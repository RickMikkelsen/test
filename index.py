from telegram.ext import Updater, CommandHandler, InlineQueryHandler
from telegram import ParseMode, InlineQueryResultPhoto, InlineQueryResultGif, InlineQueryResultVideo, InputTextMessageContent
from influxdb import InfluxDBClient
from datetime import datetime
from e621 import E621
import traceback
import logging
import config

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=config.loglevel)
logger = logging.getLogger(__name__)

updater = Updater(token=config.token)


def error(bot, update, error):
    if config.influx_active:
        i.write_points(
            [
                {
                    "measurement": "error",
                    "tags": {
                        "error": str(error),
                        "traceback": ("".join(traceback.format_tb(error.__traceback__))).replace("\n", "\\n"),
                    },
                    "time": datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ'),
                    "fields": {
                        "number": 0
                    }
                }
            ]
        )

    logger.warning(f'Update "{update}" caused error "{error}": \n{"".join(traceback.format_tb(error.__traceback__))}')


def start(bot, update):
    bot.send_message(chat_id=update.message.chat_id, text=config.msg['start'], parse_mode=ParseMode.MARKDOWN)


def inline_query(bot, update):
    results_raw = e.search(tags=update.inline_query.query, limit=50, before_id=update.inline_query.offset)

    results = []

    for result in results_raw:
        file_url = result['file_url']
        caption = f'https://e621.net/post/show/{result["id"]}'
        if result['file_size'] > 5000000:
            file_url = result['sample_url']
            caption = f'Image is scaled down, full size: {result["file_url"]}\nhttps://e621.net/post/show/{result["id"]}'

        if result['file_ext'] in ['jpg', 'png']:
            results.append(
                InlineQueryResultPhoto(id=result['id'],
                                       description=result['description'],
                                       photo_url=file_url,
                                       thumb_url=result['preview_url'],
                                       caption=caption)
            )
        elif result['file_ext'] == 'gif':
            results.append(
                InlineQueryResultGif(id=result['id'],
                                     description=result['description'],
                                     gif_url=result['file_url'],
                                     thumb_url=result['preview_url'],
                                     caption=caption)
            )
        elif result['file_ext'] == 'webm':
            results.append(
                InlineQueryResultVideo(id=result['id'],
                                       title=str(result['id']),
                                       description=result['description'],
                                       video_url=result['file_url'],
                                       thumb_url=result['preview_url'],
                                       mime_type='text/html',
                                       caption=f'https://e621.net/post/show/{result["id"]}',
                                       input_message_content=InputTextMessageContent(message_text=f'https://e621.net/post/show/{result["id"]}\n\n[video]({result["file_url"]})',
                                                                                     parse_mode='markdown',
                                                                                     disable_web_page_preview=False)
                                       )
            )
        else:
            logger.debug(f'Unknown file format "{result["file_ext"]}" ({result["id"]})')

    if len(results_raw) < 1:
        next_offset = None
    else:
        next_offset = results_raw[-1]['id']

    if config.influx_active:
        i.write_points(
            [
                {
                    "measurement": "query",
                    "tags": {
                        "query": update.inline_query.query,
                    },
                    "time": datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ'),
                    "fields": {
                        "number": len(results_raw),
                        "offset": len(update.inline_query.offset) > 0
                    }
                }
            ]
        )

    update.inline_query.answer(results=results, next_offset=next_offset, switch_pm_text=config.msg['switch_pm_text'], switch_pm_parameter='owo')


if __name__ == '__main__':
    e = E621(bot_name=config.e621['bot_name'], user_nick=config.e621['user_nick'], version=config.version)

    if config.influx_active:
        i = InfluxDBClient(**config.influx)

    updater.dispatcher.add_handler(CommandHandler('start', start))
    updater.dispatcher.add_handler(InlineQueryHandler(inline_query))
    updater.dispatcher.add_error_handler(error)
    
    updater.start_polling()
    
    updater.idle()
