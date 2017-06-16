import time

from telepot import DelegatorBot
from telepot.helper import ChatHandler
from telepot.loop import MessageLoop
from telepot.delegate import per_chat_id, create_open, pave_event_space


class TelegramParser(ChatHandler):
    def __init__(self, *args, **kwargs):
        super(TelegramParser, self).__init__(*args, **kwargs)

    def on_chat_message(self, msg):
        raw_text = msg.get('text')
        #self.sender.sendMessage("")


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
