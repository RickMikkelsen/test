import requests
import logging

logger = logging.getLogger(__name__)


class E621():
    def __init__(self, bot_name, user_nick, key='', version='0.0'):
        self.key = key
        self.name = bot_name
        self.version = version
        self.nick = user_nick

    def _make_request(self, path, **args):
        logger.debug(f'Requesting "https://e621.net/{path}.json", args: "{args}", User-Agent: "{self.name}/{self.version} (by {self.nick} on e621)"')

        r = requests.get(f'https://e621.net/{path}.json', data=args, headers={'User-Agent': f'{self.name}/{self.version} (by {self.nick} on e621)'})
        #print(r.text)
        return r.json()

    def search(self, tags, limit=320, before_id=None, all=False):
        if type(tags) is list:
            ' '.join(tags)

        if all:
            posts = []
            while True:
                tmp_posts = self._make_request('post/index', tags=tags, limit=limit)
                posts += tmp_posts

                if len(tmp_posts) < 1:
                    return posts
        else:
            return self._make_request('post/index', tags=tags, limit=limit, before_id=before_id)
