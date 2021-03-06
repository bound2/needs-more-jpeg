import os
import time
import mock
import copy
import unittest
import testhelper

from telepot import DelegatorBot
from telepot.delegate import per_chat_id, create_open, pave_event_space
from bot import TelegramParser


class TelegramTest(unittest.TestCase):
    def setUp(self):
        token = os.environ.get('TOKEN', '133505823:AAHZFMHno3mzVLErU5b5jJvaeG--qUyLyG0')
        bot = DelegatorBot(token, [
            pave_event_space()(
                per_chat_id(), create_open, TelegramParser, timeout=10
            ),
        ])
        self._bot = bot
        TelegramParser.CACHE.clear()

    # TODO kill bot object
    def tearDown(self):
        pass

    @mock.patch('__main__.DelegatorBot.sendPhoto', return_value=testhelper.result_send_image_from_text)
    @mock.patch('__main__.DelegatorBot.sendMessage', return_value=testhelper.result_error_quality)
    def test_needs_more_jpeg_integration(self, message_mock, photo_mock):
        # Check that posted url gets into cache
        self._bot.handle(testhelper.text_msg_url)
        time.sleep(2)
        assert len(TelegramParser.CACHE[27968550]) == 1
        assert len(TelegramParser.CACHE[21345678]) == 0

        # Check that response is called by bot
        self._bot.handle(testhelper.text_msg_command)
        time.sleep(3)
        assert photo_mock.call_count == 1

        # Test that exception will be thrown and message will be sent to client
        for i in range(0, 10):
            self._bot.handle(testhelper.text_msg_command)
        time.sleep(3)
        assert photo_mock.call_count == 11

        # Validate that message was sent as the quality can't be reduced any further
        self._bot.handle(testhelper.text_msg_command)
        time.sleep(5)
        assert photo_mock.call_count == 11
        assert message_mock.call_count == 1
        assert len(TelegramParser.CACHE[27968550]) == 0  # cache will be cleared when limit is hit

    @mock.patch('__main__.DelegatorBot.sendPhoto', return_value=testhelper.result_send_image_from_gallery)
    def test_image_from_gallery_integration(self, photo_mock):
        # Check that posted image gets into cache
        self._bot.handle(testhelper.image_msg)
        time.sleep(2)
        assert len(TelegramParser.CACHE[27968550]) == 1
        assert len(TelegramParser.CACHE[21345678]) == 0

        # Check that response is called by bot
        self._bot.handle(testhelper.text_msg_command)
        time.sleep(2)
        assert photo_mock.call_count == 1

    def test_cache_is_overriden_by_new_message(self):
        self._bot.handle(testhelper.text_msg_url)
        time.sleep(2)
        first_cache_value = TelegramParser.CACHE[27968550]

        # Override previous value by sending new image
        self._bot.handle(testhelper.image_msg)
        time.sleep(2)
        second_cache_value = TelegramParser.CACHE[27968550]

        assert len(first_cache_value) == 1
        assert len(second_cache_value) == 1
        assert next(iter(first_cache_value)) != next(iter(second_cache_value))

    @mock.patch('__main__.DelegatorBot.sendMessage', return_value=testhelper.result_error_cache_empty)
    def test_needs_more_jpeg_without_image(self, message_mock):
        # Should give feedback to the user that there are no images that need more jpeg
        self._bot.handle(testhelper.text_msg_command)
        time.sleep(2)
        assert message_mock.call_count == 1

        self._bot.handle(testhelper.text_msg_command)
        time.sleep(2)
        assert message_mock.call_count == 2

    @mock.patch('__main__.DelegatorBot.sendMessage', return_value=testhelper.result_error_cache_empty)
    def test_non_image_url(self, message_mock):
        text_msg_non_image_url = copy.deepcopy(testhelper.text_msg_url)
        text_msg_non_image_url['text'] = 'https://google.com'
        # Validate that item was added to cache due to being url
        self._bot.handle(text_msg_non_image_url)
        time.sleep(2)
        assert len(TelegramParser.CACHE[27968550]) == 1
        # Validate that error message was sent to the client and the cache is cleared
        self._bot.handle(testhelper.text_msg_command)
        time.sleep(2)
        assert message_mock.call_count == 1
        assert len(TelegramParser.CACHE[27968550]) == 0

    @mock.patch('__main__.DelegatorBot.sendPhoto', return_value=testhelper.result_send_image_from_gallery)
    @mock.patch('__main__.DelegatorBot.sendMessage', return_value=testhelper.result_error_cache_empty)
    def test_image_ttl(self, message_mock, photo_mock):
        initial_value = TelegramParser.TTL
        TelegramParser.TTL = 10
        try:
            self._bot.handle(testhelper.image_msg)
            time.sleep(11)
            self._bot.handle(testhelper.text_msg_command)
            time.sleep(11)
            assert photo_mock.call_count == 0
            assert message_mock.call_count == 1
            assert len(TelegramParser.CACHE[27968550]) == 0
        finally:
            TelegramParser.TTL = initial_value

    @mock.patch('__main__.DelegatorBot.sendPhoto', return_value=testhelper.result_send_image_from_gallery)
    def test_different_chats_caches(self, photo_mock):
        self._bot.handle(testhelper.image_msg)
        time.sleep(2)
        # Modify ids from the original test data
        different_user_image_msg = copy.deepcopy(testhelper.image_msg)
        different_user_image_msg['chat']['id'] = 27000500
        different_user_image_msg['from']['id'] = 27000500
        self._bot.handle(different_user_image_msg)
        time.sleep(2)
        # Validate cache
        first_user_cache = TelegramParser.CACHE[27968550]
        second_user_cache = TelegramParser.CACHE[27000500]
        assert len(first_user_cache) == 1
        assert len(second_user_cache) == 1
        assert len(TelegramParser.CACHE) == 2


if __name__ == '__main__':
    unittest.main()
