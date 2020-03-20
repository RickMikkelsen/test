# Important: This is only a extremly limited and incomplete wrapper for the e621 API
# I will write a complete wrapper someday for the new API

import requests
import logging
import time


logger = logging.getLogger(__name__)


MIN_DELAY_TIME = 0.6
TIMEOUT = 5
RETRY_COUNT = 3


class E621():
    def __init__(self, bot_name, user_nick, api_key=None, version='0.0'):
        self.api_key = api_key
        self.name = bot_name
        self.version = version
        self.nick = user_nick

        self.access_time = time.time() - MIN_DELAY_TIME

    def _make_request(self, path, login=True, **args):
        if login and self.api_key:
            args['login'] = self.nick
            args['api_key'] = self.api_key

        logger.debug(f'Requesting "https://e621.net/{path}.json", args: "{args}", User-Agent: "{self.name}/{self.version} (by {self.nick} on e621)"')

        retry_count = 0
        while retry_count <= RETRY_COUNT:
            while (self.access_time - time.time()) + MIN_DELAY_TIME > 0:
                time.sleep(max(0, (self.access_time - time.time()) + MIN_DELAY_TIME))
            self.access_time = time.time()

            try:
                r = requests.get(f'https://e621.net/{path}.json', data=args, headers={'User-Agent': f'{self.name}/{self.version} (by {self.nick} on e621)'}, timeout=TIMEOUT)
            except Exception as e:
                retry_count += 1

                if retry_count <= RETRY_COUNT:
                    continue

                raise e

            return r.json()

    def posts(self, tags, limit=50, page=None, before=None):
        if type(tags) is list:
            ' '.join(tags)

        if before:
            page = f'b{before}'

        return self._make_request('posts', tags=tags, limit=limit, page=page)
