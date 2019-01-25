import logging

version = '0.0'

loglevel = logging.INFO

token = '<telegram_bot_token>'

msg = {
    'start': 'I\'m only an inline bot, I don\'t talk. Have fun!\n[Cheatsheet](https://e621.net/help/show/cheatsheet)'
}

e621 = {
    'bot_name': 'Telegram inline bot',
    'user_nick': '<user_nick>'
}

influx_active = False
influx = {
    'host': '127.0.0.1',
    'port': 8086,
    'username': '<db_user>',
    'password': '<db_user_passwd>',
    'database': '<db_name>'
}
