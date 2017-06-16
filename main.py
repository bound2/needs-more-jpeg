import time
import re
import os
import wget
import uuid

from telepot import DelegatorBot
from telepot.helper import ChatHandler
from telepot.loop import MessageLoop
from telepot.delegate import per_chat_id, create_open, pave_event_space
from PIL import Image


class ImageData:
    def __init__(self, url, timestamp):
        self.url = url
        self.timestamp = timestamp
        self.file_path = None

    def __eq__(self, other):
        if isinstance(other, self.__class__):
            return self.url == other.url
        return NotImplemented

    def __ne__(self, other):
        if isinstance(other, self.__class__):
            return not self.__eq__(other)
        return NotImplemented

    def __hash__(self):
        return hash(self.url)


class TelegramParser(ChatHandler):
    TTL = 2 * 60 * 1000
    CACHED_DIR = 'cache'
    DOWNLOAD_DIR = 'downloads'
    URL_REGEX = r'^(?:(?:https?|ftp)://)(?:\S+(?::\S*)?@)?(?:(?:[1-9]\d?|1\d\d|2[01]\d|22[0-3])' \
                r'(?:\.(?:1?\d{1,2}|2[0-4]\d|25[0-5])){2}(?:\.(?:[1-9]\d?|1\d\d|2[0-4]\d|25[0-4]))|' \
                r'(?:(?:[a-z\u00a1-\uffff0-9]+-?)*[a-z\u00a1-\uffff0-9]+)' \
                r'(?:\.(?:[a-z\u00a1-\uffff0-9]+-?)*[a-z\u00a1-\uffff0-9]+)*' \
                r'(?:\.(?:[a-z\u00a1-\uffff]{2,})))(?::\d{2,5})?(?:/[^\s]*)?$'

    def __init__(self, *args, **kwargs):
        super(TelegramParser, self).__init__(*args, **kwargs)
        # TODO CHAT ID as dict key, set as value
        self.url_cache = set()

    def on_chat_message(self, msg):
        raw_text = msg.get('text')
        print raw_text
        current_timestamp = int(time.time())

        if 'needs more jpeg' in raw_text:
            for image in self.url_cache:
                if image.timestamp + TelegramParser.TTL > current_timestamp:
                    file_path = self.process_image(image.url, image.file_path)
                    if file_path is not None:
                        image.file_path = file_path
                        image.timestamp = current_timestamp
                        self.sender.sendPhoto(photo=open(file_path, 'rb'))
        else:
            urls = re.findall(TelegramParser.URL_REGEX, raw_text)
            if len(urls) > 0:
                self.url_cache.clear()

            for url in urls:
                image_data = ImageData(url, current_timestamp)
                self.url_cache.add(image_data)

    @staticmethod
    def process_image(url, file_path):
        new_file_path = None
        if file_path is None:
            file_path = wget.download(url, out=TelegramParser.DOWNLOAD_DIR)

        try:
            if file_path.endswith(('.png', '.jpg')):
                new_file_path = os.getcwd() + '/' + TelegramParser.CACHED_DIR + '/' + uuid.uuid4().hex + '.jpg'
                image = Image.open(file_path)
                # TODO check that it doesn't try to upscale the quality
                image.save(new_file_path, "JPEG", quality=75, optimize=True, progressive=True)
        finally:
            os.remove(file_path)

        return new_file_path


if __name__ == '__main__':
    TOKEN = ''

    bot = DelegatorBot(TOKEN, [
        pave_event_space()(
            per_chat_id(), create_open, TelegramParser, timeout=10
        ),
    ])
    MessageLoop(bot).run_as_thread()
    print('Listening ...')

    while 1:
        time.sleep(10)
