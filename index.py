from telegram.ext import Updater, CommandHandler, InlineQueryHandler
from telegram import ParseMode, InlineQueryResultPhoto, InlineQueryResultGif, InlineKeyboardMarkup, InlineKeyboardButton, InlineQueryResultVideo, InputTextMessageContent
from datetime import datetime
from e621 import E621
import traceback
import logging
from collections import OrderedDict
import time
import threading
import signal
import re

import config

if config.influx_active:
    from influxdb import InfluxDBClient


logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=config.loglevel)
logger = logging.getLogger(__name__)


# query = ('<query>', '<before_id>')
inline_queries = {}  # {'<userid>': {'update': <update>, 'query': <query>, 'time': <time of query>}, ...}
query_queue = OrderedDict()  # OrderedDict(<query>: {'user_ids': [<user_id>, ...]}, ...)
results_cache = {}  # {<query>: {'time': <time of query>, 'posts': [...]}, ...}


def results_to_inline(results_raw, query):
    results = []

    for result in results_raw[:50]:
        file_url = result['file']['url']
        caption = f'https://e621.net/posts/{result["id"]}'
        if result['file']['size'] > 5000000:
            file_url = result['sample']['url']
            caption = f'Image is scaled down, full size: {result["file"]["url"]}\nhttps://e621.net/posts/{result["id"]}'

        offset = str(int(result['id']) + 1)

        reply_markup = InlineKeyboardMarkup([[InlineKeyboardButton(config.msg['switch_inline_button_query'], switch_inline_query_current_chat=query[0]),
                                              InlineKeyboardButton(config.msg['switch_inline_button_before'], switch_inline_query_current_chat=f'{query[0]} offset:{offset}')]])

        if result['file']['ext'] in ['jpg', 'png']:
            results.append(
                InlineQueryResultPhoto(id=result['id'],
                                       description=result['description'],
                                       photo_url=file_url,
                                       thumb_url=result['preview']['url'],
                                       caption=caption,
                                       reply_markup=reply_markup)
            )
        elif result['file']['ext'] == 'gif':
            results.append(
                InlineQueryResultGif(id=result['id'],
                                     description=result['description'],
                                     gif_url=file_url,
                                     thumb_url=result['preview']['url'],
                                     caption=caption,
                                     reply_markup=reply_markup)
            )
        elif result['file']['ext'] == 'webm':
            results.append(
                InlineQueryResultVideo(id=result['id'],
                                       title=result['id'],
                                       description=result['description'],
                                       video_url=file_url,
                                       thumb_url=result['preview']['url'],
                                       mime_type="video/mp4",
                                       caption=caption,
                                       input_message_content=InputTextMessageContent(f'https://e621.net/posts/{result["id"]}'),
                                       reply_markup=reply_markup)
            )
    if len(results_raw) < 1:
        next_offset = None
    else:
        next_offset = results_raw[-1]['id']

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


def inline_query(update, context):
    if config.safe_mode:
        update.inline_query.query += ' rating:s'

    if 'offset:' in update.inline_query.query
        if not update.inline_query.offset:
            update.inline_query.offset = re.findall(r'offset:([0-9]*)', update.inline_query.query)[0]
        update.inline_query.query = re.sub(r'offset:([0-9]*)', '', update.inline_query.query)

    inline_queries[update.inline_query.from_user.id] = {'update': update, 'query': (update.inline_query.query, update.inline_query.offset.strip('t')), 'query_time': time.time()}


def _debounce_thread():
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
            no_wait = bool(update.inline_query.offset)
            in_queue = query in query_queue.keys()
            user_in_queue = False if not in_queue else user_id in query_queue[query]['user_ids']
            in_results = query in results_cache.keys()

            # logger.debug({'wait_time': wait_time, 'update': update.to_dict(), 'query': query, 'no_wait': no_wait, 'in_queue': in_queue, 'user_in_queue': user_in_queue, 'in_results': in_results})

            if wait_time > config.timeouts['forget_query']:
                del inline_queries[user_id]

                continue

            try:
                if wait_time > config.timeouts['return_known_results'] or no_wait:
                    if in_results:
                        transpiled_posts = results_to_inline(results_cache[query]['posts'], query)

                        update.inline_query.answer(switch_pm_text=config.msg['switch_pm_text'], switch_pm_parameter='owo', results=transpiled_posts['results'],
                                                   next_offset=transpiled_posts['next_offset'], cache_time=config.timeouts['result_valid'])

                        del inline_queries[user_id]
                    elif wait_time > config.timeouts['return_placeholder']:
                        update.inline_query.answer(results=[InlineQueryResultPhoto(id='-1', photo_url='https://upload.wikimedia.org/wikipedia/commons/c/ca/1x1.png',
                                                                                   thumb_url='https://upload.wikimedia.org/wikipedia/commons/c/ca/1x1.png',
                                                                                   input_message_content=InputTextMessageContent(config.msg['error_text']))],
                                                   next_offset=update.inline_query.offset + 't', switch_pm_text=config.msg['switch_pm_text'], switch_pm_parameter='owo', cache_time=0)

                        del inline_queries[user_id]
                    elif (wait_time > config.timeouts['accept_query'] or no_wait) and (not in_queue or not user_in_queue):
                        if not in_queue:
                            query_queue[query] = {'user_ids': [user_id]}
                        elif not user_in_queue:
                            query_queue[query]['user_ids'].append(user_id)
            except Exception as exce:
                error(update, error=exce)

        if config.loglevel == logging.DEBUG:
            print(f'active_users: {len(inline_queries)}, query_queue: {len(query_queue)}, results_cache: {len(results_cache)}', end='\r')

        time.sleep(0.01)


def _query_thread():
    while bot_active:
        while len(query_queue) > 0:
            query = list(query_queue.keys())[0]

            logger.debug(f'Starting query: "{query}"')

            try:
                results_cache[query] = {'time': time.time(),
                                        'posts': e.posts(tags=query[0], limit=50, before=query[1])['posts']}
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

    if config.influx_active:
        i = InfluxDBClient(**config.influx)

    updater = Updater(config.token, use_context=True)

    updater.dispatcher.add_handler(CommandHandler('start', start))
    updater.dispatcher.add_handler(InlineQueryHandler(inline_query))
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
