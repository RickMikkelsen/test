import logging

git_url = 'https://gitlab.com/TilCreator/e621_inline_bot'
version = '1.0'

loglevel = logging.INFO

token = '<telegram token>'

msg = {
    'switch_pm_text': 'About me',
    'switch_inline_button': 'OwOpen inline mode',
    'error_text': 'UwU 500 Internal Server Error',
    'start': ('I\'m only an inline bot, I don\'t talk.\n\n'
              # 'All querys are stored in a database, so I can generate 🆒 graphs and tables you can have a look at here: [<grafana url>](<grafana url>). '
              # 'But don\'t worry, I do not trust myself with any kind of personal information, so I can\'t see your number and will never remember your id, name or other kind of pseudonym.\n\n'
              'I\'m extremly simple, so I don\'t need to and will never save any data about you.\n\n'
              f'To take a look at my source code or clone me, visit [@TilCreator/e621_inline_bot]({git_url}).\n'
              'For questions, feedback and suggestions just contact my @TilCreator!\n\n'
              'Have fun (and much yiff)!\n[Search Cheatsheet](https://e621.net/help/cheatsheet)')
}
# msg = {
#     'switch_pm_text': 'About me',
#     'switch_inline_button': 'OwOpen inline mode',
#     'error_text': 'UwU 500 Internal Server Error',
#     'start': ('I\'m only an inline bot, I don\'t talk.\n\n'
#               # 'All querys are stored in a database, so I can generate 🆒 graphs and tables you can have a look at here: [<grafana url>](<grafana url>). '
#               # 'But don\'t worry, I do not trust myself with any kind of personal information, so I can\'t see your number and will never remember your id, name or other kind of pseudonym.\n\n'
#               'I\'m extremly simple, so I don\'t need to and will never save any data about you.\n\n'
#               f'To take a look at my source code or clone me, visit [@TilCreator/e621_inline_bot]({git_url}).\n'
#               'For questions, feedback and suggestions just contact my @TilCreator!\n\n'
#               'Have fun!\n[Search Cheatsheet](https://e926.net/help/cheatsheet)')
# }

safe_mode = True

e621 = {
    'api_key': '<e621 api token>',
    'bot_name': f'Telegram inline bot ({git_url})',
    'user_nick': 'TilCreator'
}

timeouts = {
    'return_known_results': .2,
    'accept_query': 2,
    'return_placeholder': 4,
    'result_valid': 60,
    'forget_query': 6
}

influx_active = False
influx = {
    'host': '127.0.0.1',
    'port': 8086,
    'username': '<db_user>',
    'password': '<db_user_passwd>',
    'database': '<db_name>'
}
