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
from collections import defaultdict


class ImageData:
    def __init__(self, url, timestamp, file_path=None, quality=50):
        self.url = url
        self.timestamp = timestamp
        self.file_path = file_path
        self.quality = quality

    def __eq__(self, other):
        if isinstance(other, self.__class__):
            return self.url == other.url
        return NotImplemented

    def __ne__(self, other):
        if isinstance(other, self.__class__):
            return not self.__eq__(other)
        return NotImplemented

    # TODO url hash comparison is bad due to it not existing in image messages
    def __hash__(self):
        return hash(self.url)


class TelegramParser(ChatHandler):
    TTL = 2 * 60 * 1000
    CACHE = defaultdict(frozenset)
    CACHED_DIR = 'cache'
    DOWNLOAD_DIR = 'downloads'
    URL_REGEX = r'^(?:(?:https?|ftp)://)(?:\S+(?::\S*)?@)?(?:(?:[1-9]\d?|1\d\d|2[01]\d|22[0-3])' \
                r'(?:\.(?:1?\d{1,2}|2[0-4]\d|25[0-5])){2}(?:\.(?:[1-9]\d?|1\d\d|2[0-4]\d|25[0-4]))|' \
                r'(?:(?:[a-z\u00a1-\uffff0-9]+-?)*[a-z\u00a1-\uffff0-9]+)' \
                r'(?:\.(?:[a-z\u00a1-\uffff0-9]+-?)*[a-z\u00a1-\uffff0-9]+)*' \
                r'(?:\.(?:[a-z\u00a1-\uffff]{2,})))(?::\d{2,5})?(?:/[^\s]*)?$'

    def __init__(self, *args, **kwargs):
        super(TelegramParser, self).__init__(*args, **kwargs)

    def on_chat_message(self, msg):
        raw_text = msg.get('text')
        raw_photos = msg.get('photo')
        current_timestamp = int(time.time())

        if raw_photos is not None:
            self.process_image_message(photos=raw_photos, timestamp=current_timestamp)
        elif raw_text is not None:
            self.process_text_message(text=raw_text, timestamp=current_timestamp)

    def process_text_message(self, text, timestamp):
        if 'needs more jpeg' in text:
            try:
                for image in TelegramParser.CACHE[self.chat_id]:
                    if image.timestamp + TelegramParser.TTL > timestamp:
                        new_quality = self.determine_new_quality(image.quality)
                        file_path = self.process_image(image.url, image.file_path, new_quality)
                        if file_path is not None:
                            image.file_path = file_path
                            image.timestamp = timestamp
                            image.quality = new_quality
                            self.sender.sendPhoto(photo=open(file_path, 'rb'))
            except ValueError as e:
                self._clear_cache(self.chat_id)
                self.sender.sendMessage(e.message)
        else:
            urls = re.findall(TelegramParser.URL_REGEX, text)
            if len(urls) > 0:
                self._clear_cache(self.chat_id)

            for url in urls:
                image_data = ImageData(url, timestamp)
                self._add_to_cache(self.chat_id, image_data)

    # TODO check multiple image upload
    def process_image_message(self, photos, timestamp):
        best_resolution_photo = photos[-1]
        for photo in photos:
            if photo.get('width') > best_resolution_photo.get('width') \
                    or photo.get('height') > best_resolution_photo.get('height'):
                best_resolution_photo = photo

        file_id = best_resolution_photo.get('file_id')
        new_file_path = TelegramParser.cache_file_path()
        self.bot.download_file(file_id=file_id, dest=new_file_path)

        self._clear_cache(self.chat_id)
        image_data = ImageData(url=None, timestamp=timestamp, file_path=new_file_path)
        self._add_to_cache(self.chat_id, image_data)

    @staticmethod
    def _add_to_cache(chat_id, image_data):
        cached_images = set(TelegramParser.CACHE[chat_id])
        cached_images.add(image_data)
        TelegramParser.CACHE[chat_id] = frozenset(cached_images)

    @staticmethod
    def _clear_cache(chat_id):
        TelegramParser.CACHE[chat_id] = frozenset()

    @staticmethod
    def determine_new_quality(quality):
        if quality <= 1:
            raise ValueError('Quality can not be reduced any more!!!')
        if quality <= 10:
            return quality - 1
        else:
            return quality - 10

    @staticmethod
    def process_image(url, file_path, quality):
        new_file_path = None
        if file_path is None:
            file_path = wget.download(url, out=TelegramParser.DOWNLOAD_DIR)

        try:
            if file_path.endswith(('.png', '.jpg')):
                new_file_path = TelegramParser.cache_file_path()
                image = Image.open(file_path)
                image.save(new_file_path, 'JPEG', quality=quality, optimize=False, progressive=False)
        finally:
            os.remove(file_path)

        return new_file_path

    @staticmethod
    def cache_file_path():
        return os.getcwd() + '/' + TelegramParser.CACHED_DIR + '/' + uuid.uuid4().hex + '.jpg'


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
