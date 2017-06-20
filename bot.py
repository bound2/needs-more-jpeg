import time

from telepot import DelegatorBot
from telepot.loop import MessageLoop
from telepot.delegate import per_chat_id, create_open, pave_event_space
from ConfigParser import ConfigParser
from parser.telegramparser import TelegramParser

if __name__ == '__main__':
    config = ConfigParser()
    config.read('config.ini')
    section = config.sections().pop()
    token = config.get(section, 'token')

    bot = DelegatorBot(token, [
        pave_event_space()(
            per_chat_id(), create_open, TelegramParser, timeout=10
        ),
    ])
    MessageLoop(bot).run_as_thread()
    print('Listening ...')

    while 1:
        time.sleep(10)
