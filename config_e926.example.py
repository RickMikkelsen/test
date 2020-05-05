import logging

git_url = 'https://gitlab.com/TilCreator/e621_inline_bot'
version = '1.0'

loglevel = logging.INFO
debug_status_line = False

db_url = 'sqlite:///data_e926.db'

token = '<telegram token>'

safe_mode = True

blacklist = {'default': ('gore\n'  # default e621 blacklist
                         'scat\n'
                         'watersports\n'
                         'young -rating:s\n'
                         'loli\n'
                         'shota'),
             'limit': {'lines': 200,
                       'chars_per_line': 1000}}

e621 = {
    'api_key': '<e621 api key>',
    'bot_name': f'Telegram inline bot ({git_url})',
    'user_nick': '<e621 user nick>',
    'posts_per_query': 300  # preferably a multiple of 50
}

timeouts = {
    'return_known_results': 0.2,
    'accept_query': 1.2,
    'return_placeholder': 4,
    'result_valid': 60,
    'forget_query': 6,
    'chat_state': 48 * 60 * 60
}

influx_active = False
influx = {
    'host': '127.0.0.1',
    'port': 8086,
    'username': '<db_user>',
    'password': '<db_user_passwd>',
    'database': '<db_name>'
}

max_buttons_per_row = 5

msg = {
    'switch_pm_text': 'About me',
    'switch_inline_button_empty': 'OwOpen inline mode',
    'switch_inline_button_query': 'open search',
    'switch_inline_button_before': 'search with offset',
    'switch_inline_button_query_retry': 'retry query',
    'error_text': 'UwU 500 Internal Server Error',
    'start': ('I\'m only an inline bot, I don\'t talk.\n\n'
              # 'All querys are stored in a database, so I can generate 🆒 graphs and tables you can have a look at here: [<grafana url>](<grafana url>). '
              # 'But don\'t worry, I do not trust myself with any kind of personal information, so I can\'t see your number and will never remember your id, name or other kind of pseudonym.\n\n'
              'Hewwo, I\'m a e926 inline search bot.\n\n'
              'On default I will not save any data about you, only if you want to use the blacklist function, I will have to ask you to allow me to save data about you.\n\n'
              f'To take a look at my source code or clone me, visit [@TilCreator/e621_inline_bot]({git_url}).\n'
              'For questions, feedback and suggestions just contact my @TilCreator! (or write an issue on Gitlab)\n\n'
              '[Search Cheatsheet](https://e926.net/help/cheatsheet)\n'
              'To use the blacklist: /blacklist\n\n'
              'Have fun!'),
    'blacklist': 'Blacklist:\n```\n{blacklist}\n```\nUse the buttons to change the blacklist\nE926 blacklist help page: https://e926.net/help/blacklist\n(Uploader blacklisting currently unsupported)',
    'blacklist_button_add': 'Add',
    'blacklist_button_clear': 'Clear',
    'blacklist_button_remove': 'Remove line',
    'blacklist_nodata': 'Blacklist:\n```\n{blacklist}\n```\nTo change the blacklist you have to accept first that I\'m allowed to save data about you.\nClick this to confirm /itrustyou',
    'blacklist_clear': 'Your blacklist is now empty',
    'blacklist_add': 'Write me what you would like to add to your blacklist now. You can also use multiple lines in one message to add multiple lines to your blacklist',
    'blacklist_add_button_cancel': 'Cancel',
    'blacklist_add_done': 'Adding done, blacklist is now:\n```\n{blacklist}\n```',
    'blacklist_add_error_chars_per_line': f"""You got the longest lines I have ever see!\nSry, but I won\'t take lines longer than {blacklist['limit']['chars_per_line']} chars""",
    'blacklist_add_error_lines': f"""You got the longest blacklist I have ever see!\nSry, but I won\'t take blacklists longer than {blacklist['limit']['lines']} lines""",
    'blacklist_remove': 'Blacklist:\n```\n{blacklist_numbered}\n```\nPress one of the corosponding line buttons to remove the line',
    'blacklist_remove_done': 'Line removed\n\nBlacklist:\n```\n{blacklist_numbered}\n```\nPress one of the corosponding line buttons to remove the line',
    'blacklist_remove_button_done': 'Done',
    'blacklist_remove_done_nochange': 'Blacklist:\n```\n{blacklist}\n```',
    'blacklist_remove_error_hash': 'Blacklist changed in other ways, no changes written! Plz try again\n\nBlacklist:\n```\n{blacklist_numbered}\n```\nPress one of the corosponding line buttons to remove the line',
    'itrustyou': 'This will allow me to save data about you. This currently includes: Your user id and your blacklist.\nYou can always delete your data with /forgetme',
    'itrustyou_button': 'I really trust you',
    'ireallytrustyou': 'You can now use the /blacklist.\nRemember that you can delete your data with /forgetme',
    'itrustyou_fail': 'You already trust me.\nIf you want me to forget you enter /forgetme',
    'ireallytrustyou_fail': 'You already trust me.\nIf you want me to forget you enter /forgetme',
    'forgetme': 'You really want me to forget you?',
    'forgetme_button': 'Really forget me',
    'reallyforgetme': 'Goodbye\n\n\\[Memory wipe complete]',
    'forgetme_fail': 'I don\'t even know you, how should I forget you then?',
    'reallyforegetme_fail': 'I don\'t even know you, how should I forget you then?',
    'nodata_fail': 'To use this function you have to allow me to save data about you.\nClick this to confirm /itrustyou'
}
