from telegram.ext import Updater, CommandHandler, InlineQueryHandler
from telegram import InlineQueryResultPhoto, InlineQueryResultGif  # , InlineQueryResultVideo
from e621 import E621
import traceback
import logging
import config

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=config.loglevel)
logger = logging.getLogger(__name__)

updater = Updater(token=config.token)


def error(bot, update, error):
    logger.warning(f'Update "{update}" caused error "{error}": \n{"".join(traceback.format_tb(error.__traceback__))}')


def start(bot, update):
    bot.send_message(chat_id=update.message.chat_id, text=config.msg['start'])


def inline_query(bot, update):
    results_raw = e.search(tags=update.inline_query.query, limit=50, before_id=update.inline_query.offset)

    results = []

    for result in results_raw:
        if result['file_ext'] in ['jpg', 'png']:
            results.append(
                InlineQueryResultPhoto(id=result['id'],
                                       description=result['description'],
                                       photo_url=result['file_url'],
                                       thumb_url=result['preview_url'])
            )
        elif result['file_ext'] == 'gif':
            results.append(
                InlineQueryResultGif(id=result['id'],
                                     description=result['description'],
                                     gif_url=result['file_url'],
                                     thumb_url=result['preview_url'])
            )
        #elif result['file_ext'] == 'webm':
        #    results.append(
        #        InlineQueryResultVideo(id=result['id'],
        #                               title=result['id'],
        #                               description=result['description'],
        #                               video_url=result['file_url'],
        #                               thumb_url=result['preview_url'],
        #                               mime_type='video/webm')
        #    )

    if len(results_raw) < 1:
        next_offset = None
    else:
        next_offset = results_raw[-1]['id']

    update.inline_query.answer(results=results, next_offset=next_offset)


if __name__ == '__main__':
    e = E621(bot_name=config.e621['bot_name'], user_nick=config.e621['user_nick'], version=config.version)

    updater.dispatcher.add_handler(CommandHandler('start', start))
    updater.dispatcher.add_handler(InlineQueryHandler(inline_query))
    updater.dispatcher.add_error_handler(error)
    
    updater.start_polling()
    
    updater.idle()
