import os
import time
import mock
import unittest
import testhelper

from telepot import DelegatorBot
from telepot.delegate import per_chat_id, create_open, pave_event_space
from main import TelegramParser


class TelegramTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # TODO should it be created before every tests? seems like otherwise it's conflicting
        token = os.environ.get('TOKEN', '133505823:AAHZFMHno3mzVLErU5b5jJvaeG--qUyLyG0')
        bot = DelegatorBot(token, [
            pave_event_space()(
                per_chat_id(), create_open, TelegramParser, timeout=10
            ),
        ])
        cls._bot = bot

    @mock.patch('__main__.DelegatorBot.sendPhoto', return_value=testhelper.result_send_image_from_text)
    @mock.patch('__main__.DelegatorBot.sendMessage', return_value=testhelper.result_quality_error)
    def test_parsed_url_added_to_cache(self, message_mock, photo_mock):
        TelegramParser.CACHE.clear()
        # Check that posted url gets into cache
        self._bot.handle(testhelper.text_msg_url)
        time.sleep(1)
        assert len(TelegramParser.CACHE[27968550]) == 1
        assert len(TelegramParser.CACHE[21345678]) == 0

        # Check that response is called by bot
        self._bot.handle(testhelper.text_msg_command)
        time.sleep(1)
        assert photo_mock.call_count == 1

        # Test that exception will be thrown and message will be sent to client
        for i in range(0, 12):
            self._bot.handle(testhelper.text_msg_command)
        time.sleep(3)
        assert photo_mock.call_count == 13

        # Validate that message was sent as the quality can't be reduced any further
        self._bot.handle(testhelper.text_msg_command)
        time.sleep(1)
        assert photo_mock.call_count == 13
        assert message_mock.call_count == 1
        assert len(TelegramParser.CACHE[27968550]) == 0  # cache will be cleared when limit is hit


if __name__ == '__main__':
    unittest.main()
