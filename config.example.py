import logging

version = '0.0'

loglevel = logging.INFO

token = '<telegram_bot_token>'

msg = {
    'switch_pm_text': 'About me',
    'start': ('I\'m only an inline bot, I don\'t talk.\n\n'
              'All querys are stored in a database, so I can generate :cool: graphs and tables you can have a look at here: [<grafana url>](<grafana url>). '
              'But don\'t worry, I do not trust myself with any kind of personal information, so I can\'t see your number and will never remember your id, name or other kind of pseudonym.\n\n'
              'To take a look at my source code or clone me, visit [@TilCreator/e621_inline_bot](https://gitlab.com/TilCreator/e621_inline_bot).\n'
              'For questions, feedback and suggestions just contact my @TilCreator!\n\n'
              'Have fun (and yiff)!\n[Search Cheatsheet](https://e621.net/help/show/cheatsheet)')
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
