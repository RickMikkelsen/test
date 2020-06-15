from datetime import datetime
import traceback
import logging
from collections import OrderedDict
import time
import threading
import signal
import re
import dataset
import sys
from more_itertools import unique_everseen
from e621 import E621
from telegram.ext import Updater, CommandHandler, InlineQueryHandler, CallbackQueryHandler, MessageHandler, Filters
from telegram import ParseMode, InlineQueryResultPhoto, InlineQueryResultGif, InlineKeyboardMarkup, InlineKeyboardButton, InlineQueryResultVideo, InputTextMessageContent

config_name = 'config'
if len(sys.argv) >= 2:
    config_name += '_' + sys.argv[1]

config = __import__(config_name)

if config.influx_active:
    from influxdb import InfluxDBClient


logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=config.loglevel)
logger = logging.getLogger(__name__)


# query = ('<query>', '<before_id>')
inline_queries = {}  # {'<userid>': {'update': <update>, 'query': <query>, 'time': <time of query>}, ...}
query_queue = OrderedDict()  # OrderedDict(<query>: {'user_ids': [<user_id>, ...]}, ...)
results_cache = {}  # {<query>: {'time': <time of query>, 'posts': [...]}, ...}


def results_to_inline(results_raw, query, blacklist):
    results = []

    for result in results_raw:
        ratings = {"s": "safe", "q": "questionable", "e": "explicit"}

        tags = sorted({x for v in result['tags'].values() for x in v}) + [f'rating:{result["rating"]}',
                                                                          f'rating:{ratings[result["rating"]]}',
                                                                          f'id:{result["id"]}',
                                                                          f'type:{result["file"]["ext"]}']

        blacklisted = False
        if not re.match(r'.*(?:^|\s+)id:([0-9]+)(?:$|\s+).*', query[0]):  # If 'id:*' not in query, ignore blacklist
            for line in blacklist.split('\n'):
                if len(line) < 1:
                    continue

                in_blacklist = []
                for tag in line.split():
                    if tag.startswith('-'):
                        in_blacklist.append(tag[1:] not in tags)
                    else:
                        in_blacklist.append(tag in tags)

                if False not in in_blacklist:
                    blacklisted = True

        if blacklisted:
            continue

        file_url = result['file']['url']
        caption = f'https://e621.net/posts/{result["id"]}'
        if result['file']['size'] > 500000:
            file_url = result['sample']['url']
            caption = f'Image is scaled down, full size: {result["file"]["url"]}\nhttps://e621.net/posts/{result["id"]}'

        description = result['description']
        if len(description) > 500:
            description = description[:500] + '...'

        offset = str(int(result['id']) + 1)

        reply_markup = InlineKeyboardMarkup([[InlineKeyboardButton(config.msg['switch_inline_button_query'], switch_inline_query_current_chat=query[0]),
                                              InlineKeyboardButton(config.msg['switch_inline_button_before'], switch_inline_query_current_chat=f'{query[0]} offset:{offset}')]])

        if result['file']['ext'] in ['jpg', 'png']:
            results.append(
                InlineQueryResultPhoto(id=result['id'],
                                       description=description,
                                       photo_url=file_url,
                                       thumb_url=result['preview']['url'],
                                       caption=caption,
                                       reply_markup=reply_markup)
            )
        elif result['file']['ext'] == 'gif':
            results.append(
                InlineQueryResultGif(id=result['id'],
                                     description=description,
                                     gif_url=file_url,
                                     thumb_url=result['preview']['url'],
                                     caption=caption,
                                     reply_markup=reply_markup)
            )
        elif result['file']['ext'] == 'webm':
            results.append(
                InlineQueryResultVideo(id=result['id'],
                                       title=result['id'],
                                       description=description,
                                       video_url=file_url,
                                       thumb_url=result['preview']['url'],
                                       mime_type="video/mp4",
                                       caption=caption,
                                       input_message_content=InputTextMessageContent(f'https://e621.net/posts/{result["id"]}'),
                                       reply_markup=reply_markup)
            )

        if len(results) >= 50:
            break

    if len(results) < 1:
        next_offset = None
    else:
        next_offset = results[-1]['id']

    return {'results': results, 'next_offset': next_offset}


def error(update, context=None, error=None):
    if error is None:
        error = context.error

    if config.influx_active:
        i.write_points(
            [
                {
                    "measurement": "error",
                    "tags": {
                        "error": str(error),
                        "traceback": "".join(traceback.format_tb(error.__traceback__)).replace('\n', '<br>'),
                    },
                    "time": datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ'),
                    "fields": {
                        'number': 0
                    }
                }
            ]
        )

    logger.warning(f'Update "{update}" caused error "{error}": \n{"".join(traceback.format_tb(error.__traceback__))}')


def start(update, context):
    update.message.reply_text(text=config.msg['start'], parse_mode=ParseMode.MARKDOWN,
                              reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(config.msg['switch_inline_button_empty'], switch_inline_query='')]]))


def blacklist(update, context):
    blacklist = config.blacklist['default']
    user_data = None

    user_data = users.find_one(user_id=update.message.from_user.id)

    if user_data:
        blacklist = user_data['blacklist']

        update.message.reply_text(text=config.msg['blacklist'].format(blacklist=blacklist), parse_mode=ParseMode.MARKDOWN,
                                  reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(config.msg['blacklist_button_add'], callback_data='blacklist_add'),
                                                                      InlineKeyboardButton(config.msg['blacklist_button_clear'], callback_data='blacklist_clear')],
                                                                     [InlineKeyboardButton(config.msg['blacklist_button_remove'], callback_data='blacklist_remove')]]))
    else:
        update.message.reply_text(text=config.msg['blacklist_nodata'].format(blacklist=blacklist), parse_mode=ParseMode.MARKDOWN)


def blacklist_clear(update, context):
    if not users.find_one(user_id=update.message.from_user.id):
        update.message.reply_text(text=config.msg['nodata_fail'], parse_mode=ParseMode.MARKDOWN)
        return

    users.update({'user_id': update.message.from_user.id, 'blacklist': ''}, ['user_id'])

    update.message.reply_text(text=config.msg['blacklist_clear'], parse_mode=ParseMode.MARKDOWN)


def blacklist_add(update, context):
    if not users.find_one(user_id=update.message.from_user.id):
        update.message.reply_text(text=config.msg['nodata_fail'], parse_mode=ParseMode.MARKDOWN)
        return

    context.user_data['chat_state'] = {'state': 'blacklist_add', 'time': time.time()}

    update.message.reply_text(text=config.msg['blacklist_add'],
                              reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(config.msg['blacklist_add_button_cancel'], callback_data='blacklist_add_cancel')]]))


def blacklist_remove(update, context, callback=None):
    if not users.find_one(user_id=update.message.from_user.id):
        update.message.reply_text(text=config.msg['nodata_fail'], parse_mode=ParseMode.MARKDOWN)
        return

    blacklist = users.find_one(user_id=update.message.from_user.id)['blacklist'].split('\n')
    if blacklist == ['']:
        blacklist = []

    blacklist_hash = hash('\n'.join(blacklist))

    text = config.msg['blacklist_remove']

    if callback:
        if callback == 'blacklist_remove_done':
            update.message.reply_text(text=config.msg['blacklist_remove_done_nochange'].format(blacklist='\n'.join(blacklist)), parse_mode=ParseMode.MARKDOWN)
            return

        _, _, callback_blacklist_hash, callback_blacklist_i = callback.split('_')
        callback_blacklist_hash, callback_blacklist_i = int(callback_blacklist_hash), int(callback_blacklist_i)

        if blacklist_hash != int(callback_blacklist_hash):
            text = config.msg['blacklist_remove_error_hash']
        else:
            if callback_blacklist_i not in range(len(blacklist)):
                text = config.msg['blacklist_remove_error_hash']
            else:
                text = config.msg['blacklist_remove_done']

                blacklist = [line for i, line in enumerate(blacklist) if i != callback_blacklist_i]

                users.update({'user_id': update.message.from_user.id, 'blacklist': '\n'.join(blacklist)}, ['user_id'])

    blacklist_hash = hash('\n'.join(blacklist))

    blacklist_numbered = ''
    for i, line in enumerate(blacklist):
        blacklist_numbered += f'{i} - {line}\n'

    buttons = []
    for i in range(len(blacklist)):
        if len(buttons) <= 0 or len(buttons[-1]) >= config.max_buttons_per_row:
            buttons.append([])
        buttons[-1].append(InlineKeyboardButton(str(i), callback_data=f'blacklist_remove_{blacklist_hash}_{i}'))
    
    buttons.append([InlineKeyboardButton(config.msg['blacklist_remove_button_done'], callback_data='blacklist_remove_done')])

    update.message.reply_text(text=text.format(blacklist_numbered=blacklist_numbered), parse_mode=ParseMode.MARKDOWN,
                              reply_markup=InlineKeyboardMarkup(buttons))


def itrustyou(update, context):
    if users.find_one(user_id=update.message.from_user.id):
        update.message.reply_text(text=config.msg['itrustyou_fail'], parse_mode=ParseMode.MARKDOWN)

        return

    update.message.reply_text(text=config.msg['itrustyou'], parse_mode=ParseMode.MARKDOWN,
                              reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(config.msg['itrustyou_button'], callback_data='ireallytrustyou')]]))


def ireallytrustyou(update, context):
    if users.find_one(user_id=update.message.from_user.id):
        update.message.reply_text(text=config.msg['ireallytrustyou_fail'], parse_mode=ParseMode.MARKDOWN)

        return

    users.insert_ignore({'user_id': update.message.from_user.id, 'blacklist': config.blacklist['default']}, ['user_id'])

    update.message.reply_text(text=config.msg['ireallytrustyou'], parse_mode=ParseMode.MARKDOWN)


def forgetme(update, context):
    if not users.find_one(user_id=update.message.from_user.id):
        update.message.reply_text(text=config.msg['forgetme_fail'], parse_mode=ParseMode.MARKDOWN)

        return

    update.message.reply_text(text=config.msg['forgetme'], parse_mode=ParseMode.MARKDOWN,
                              reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(config.msg['forgetme_button'], callback_data='reallyforgetme')]]))


def reallyforgetme(update, context):
    if not users.find_one(user_id=update.message.from_user.id):
        update.message.reply_text(text=config.msg['forgetme_fail'], parse_mode=ParseMode.MARKDOWN)

        return

    if 'chat_state' in context.user_data:
        del context.user_data['chat_state']

    users.delete(user_id=update.message.from_user.id)

    update.message.reply_text(text=config.msg['reallyforgetme'], parse_mode=ParseMode.MARKDOWN)


def chat_query(update, context):
    if 'chat_state' in context.user_data.keys() and context.user_data['chat_state']['state'] == 'blacklist_add':
        if context.user_data['chat_state']['time'] + config.timeouts['chat_state'] < time.time():
            del context.user_data['chat_state']

            return

        lines_new = []

        for line in update.message.text.split('\n'):
            line = ' '.join(line.strip(' ').split())  # remove leading, trailing and double spaces

            if len(line) < 1:
                continue

            if len(line) > config.blacklist['limit']['chars_per_line']:
                update.message.reply_text(text=config.msg['blacklist_add_error_chars_per_line'], parse_mode=ParseMode.MARKDOWN)
                return

            lines_new.append(line)

        lines_old = users.find_one(user_id=update.message.from_user.id)['blacklist'].split('\n')
        if lines_old[0] == '':
            lines_old = []

        lines_final = list(unique_everseen(lines_old + lines_new))

        if len(lines_final) > config.blacklist['limit']['lines']:
            update.message.reply_text(text=config.msg['blacklist_add_error_lines'], parse_mode=ParseMode.MARKDOWN)
            return

        blacklist = '\n'.join(lines_final)

        users.update({'user_id': update.message.from_user.id, 'blacklist': blacklist}, ['user_id'])

        del context.user_data['chat_state']

        update.message.reply_text(text=config.msg['blacklist_add_done'].format(blacklist=blacklist), parse_mode=ParseMode.MARKDOWN)


def callback_query(update, context):
    update.message = update.callback_query.message
    update.message.from_user = update.callback_query.from_user

    if update.callback_query.data == 'ireallytrustyou':
        ireallytrustyou(update, context)
    elif update.callback_query.data == 'reallyforgetme':
        reallyforgetme(update, context)
    elif update.callback_query.data == 'blacklist_clear':
        blacklist_clear(update, context)
    elif update.callback_query.data == 'blacklist_add':
        blacklist_add(update, context)
    elif update.callback_query.data == 'blacklist_add_cancel':
        if 'chat_state' in context.user_data.keys() and context.user_data['chat_state']['state'] == 'blacklist_add':
            del context.user_data['chat_state']
    elif update.callback_query.data == 'blacklist_remove':
        blacklist_remove(update, context)
    elif re.match(r'blacklist_remove_(?:-)?[0-9]+_[0-9]+', update.callback_query.data):
        blacklist_remove(update, context, callback=update.callback_query.data)

        # updater.bot.delete_message(update.callback_query.message.chat_id, update.callback_query.inline_message_id)
        # return
    elif update.callback_query.data == 'blacklist_remove_done':
        blacklist_remove(update, context, callback=update.callback_query.data)

    update.callback_query.edit_message_reply_markup(InlineKeyboardMarkup([[]]))


def inline_query(update, context):
    if config.safe_mode:
        update.inline_query.query += ' rating:s'

    re_offset = r'(?:^|\s+)offset:([0-9]*)(?:$|\s+)'
    if re.match(rf'.*{re_offset}.*', update.inline_query.query):
        if not update.inline_query.offset:
            update.inline_query.offset = re.findall(re_offset, update.inline_query.query)[0]
        update.inline_query.query = re.sub(re_offset, ' ', update.inline_query.query)

    # Replace e621/e926 url with id:<id>
    update.inline_query.query = re.sub(r'(?:^|\s+)(?:http(?:s)?\:\/\/)?e(?:621|926)\.net\/post(?:s|\/show)\/([0-9]+)(?:\?\S*)?(?:$|\s+)', r'id:\g<1>', update.inline_query.query)

    update.inline_query.query = ' '.join(update.inline_query.query.split())

    inline_queries[update.inline_query.from_user.id] = {'update': update, 'query': (update.inline_query.query, update.inline_query.offset.strip('t')), 'query_time': time.time()}


def _debounce_thread():
    if config.periodic_logging['enabled']:
        logging_data = {'new_queries': 0,
                        'query_queue': 0,
                        'results_cache': 0,
                        'successful_queries': 0,
                        'failed_queries': 0,
                        'successfuly_cached': 0}
        last_logged = time.time() - config.periodic_logging['interval']

        print(','.join(logging_data.keys()), file=open(config.periodic_logging['file'], 'w'))

    while bot_active:
        for query in list(results_cache.keys()):
            if time.time() - results_cache[query]['time'] > config.timeouts['result_valid']:
                del results_cache[query]

        for query in list(query_queue.keys()):
            user_ids = query_queue[query]['user_ids']
            for i in range(len(user_ids)):
                if user_ids[i] not in inline_queries.keys() or query != inline_queries[user_ids[i]]['query']:
                    del user_ids[i]
            if len(user_ids) <= 0:
                del query_queue[query]

        for user_id in list(inline_queries.keys()):
            inline_query = inline_queries[user_id]
            wait_time = time.time() - inline_query['query_time']
            update = inline_query['update']
            query = inline_query['query']
            no_wait = bool(query[1])
            in_queue = query in query_queue.keys()
            user_in_queue = False if not in_queue else user_id in query_queue[query]['user_ids']
            in_results = query in results_cache.keys()

            in_results_other_offset = {'key': None, 'offset_i': 0, 'length': 0}
            if not in_results and query[1]:
                for key in list(results_cache.keys()):  # results_cache could change during iteration
                    if not key in results_cache or key[0] != query[0]:
                        continue
                    results = results_cache[key]

                    for i, result in enumerate(results['posts']):
                        length = len(results['posts']) - i

                        if result['id'] == int(query[1]) - 1 and length > in_results_other_offset['length']:
                            in_results_other_offset = {'key': key[1],
                                                       'offset_i': i,
                                                       'length': length}

                            break

            # logger.debug({'wait_time': wait_time, 'update': update.to_dict(), 'query': query, 'no_wait': no_wait, 'in_queue': in_queue, 'user_in_queue': user_in_queue, 'in_results': in_results})

            if wait_time > config.timeouts['forget_query']:
                del inline_queries[user_id]

                continue

            try:
                if wait_time > config.timeouts['return_known_results'] or no_wait:
                    if in_results or in_results_other_offset['key'] is not None:
                        if in_results:
                            posts = results_cache[query]['posts']
                        else:
                            posts = results_cache[(query[0], in_results_other_offset['key'])]['posts'][in_results_other_offset['offset_i']:]

                            if config.periodic_logging['enabled']: logging_data['successfuly_cached'] += 1

                        blacklist = config.blacklist['default']
                        user = users.find_one(user_id=user_id)
                        if user:
                            blacklist = user['blacklist']

                        is_personal = blacklist != config.blacklist['default']

                        transpiled_posts = results_to_inline(posts, query, blacklist=blacklist)

                        update.inline_query.answer(switch_pm_text=config.msg['switch_pm_text'], switch_pm_parameter='owo', results=transpiled_posts['results'],
                                                   next_offset=transpiled_posts['next_offset'], cache_time=config.timeouts['result_valid'], is_personal=is_personal)

                        del inline_queries[user_id]

                        if config.periodic_logging['enabled']: logging_data['successful_queries'] += 1
                    elif wait_time > config.timeouts['return_placeholder']:
                        update.inline_query.answer(results=[InlineQueryResultPhoto(id='-1', photo_url='https://upload.wikimedia.org/wikipedia/commons/c/ca/1x1.png',
                                                                                   thumb_url='https://upload.wikimedia.org/wikipedia/commons/c/ca/1x1.png',
                                                                                   input_message_content=InputTextMessageContent(config.msg['error_text']),
                                                                                   reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(config.msg['switch_inline_button_query_retry'],
                                                                                                                       switch_inline_query_current_chat=query[0])]]))],
                                                   next_offset=query[1] + 't', switch_pm_text=config.msg['switch_pm_text'], switch_pm_parameter='owo', cache_time=0)

                        del inline_queries[user_id]

                        if config.periodic_logging['enabled']: logging_data['failed_queries'] += 1
                    elif (wait_time > config.timeouts['accept_query'] or no_wait) and (not in_queue or not user_in_queue):
                        if not in_queue:
                            query_queue[query] = {'user_ids': [user_id]}
                        elif not user_in_queue:
                            query_queue[query]['user_ids'].append(user_id)
            except Exception as exce:
                error(update, error=exce)

        if config.loglevel == logging.DEBUG and config.debug_status_line:
            print(f'active_users: {len(inline_queries)}, query_queue: {len(query_queue)}, results_cache: {len(results_cache)}', end='\r')

        if config.periodic_logging['enabled'] and time.time() - last_logged > config.periodic_logging['interval']:
            print(','.join([str(val) for val in logging_data.values()]), file=open(config.periodic_logging['file'], 'a'))

            logging_data = {'new_queries': len(inline_queries),
                            'query_queue': len(query_queue),
                            'results_cache': len(results_cache),
                            'successful_queries': 0,
                            'failed_queries': 0,
                            'successfuly_cached': 0}

            last_logged = time.time()

        time.sleep(0.01)


def _query_thread():
    while bot_active:
        while len(query_queue) > 0:
            query = list(query_queue.keys())[0]

            logger.debug(f'Starting query: "{query}"')

            try:
                results_cache[query] = {'time': time.time(),
                                        'posts': e.posts(tags=query[0], limit=config.e621['posts_per_query'], before=query[1])['posts']}
            except Exception as exce:
                error({}, error=exce)
            else:
                if query in query_queue.keys():
                    del query_queue[query]

                logger.debug(f'Finished query: "{query}", results: {len(results_cache[query]["posts"])}')

        time.sleep(0.01)


def kill_threads():
    global bot_active
    bot_active = False

    query_thread.join()
    debounce_thread.join()


if __name__ == '__main__':
    e = E621(bot_name=config.e621['bot_name'], user_nick=config.e621['user_nick'], api_key=config.e621['api_key'], version=config.version)

    db = dataset.connect(config.db_url)

    users = db.create_table('users', primary_id='user_id')

    if config.influx_active:
        i = InfluxDBClient(**config.influx)

    updater = Updater(config.token, use_context=True)

    updater.dispatcher.add_handler(CommandHandler('start', start))
    updater.dispatcher.add_handler(CommandHandler('blacklist', blacklist))
    updater.dispatcher.add_handler(CommandHandler('itrustyou', itrustyou))
    # updater.dispatcher.add_handler(CommandHandler('ireallytrustyou', ireallytrustyou))
    updater.dispatcher.add_handler(CommandHandler('forgetme', forgetme))
    # updater.dispatcher.add_handler(CommandHandler('reallyforgetme', reallyforgetme))
    updater.dispatcher.add_handler(CallbackQueryHandler(callback_query))
    updater.dispatcher.add_handler(InlineQueryHandler(inline_query))
    updater.dispatcher.add_handler(MessageHandler(Filters.text, chat_query))

    updater.dispatcher.add_error_handler(error)

    updater.start_polling()

    bot_active = True

    debounce_thread = threading.Thread(target=_debounce_thread)
    debounce_thread.daemon = True
    debounce_thread.start()

    query_thread = threading.Thread(target=_query_thread)
    query_thread.daemon = True
    query_thread.start()

    signal.signal(signal.SIGINT, kill_threads)

    try:
        updater.idle()
    except KeyboardInterrupt:
        kill_threads()
