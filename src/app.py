import logging
import sys

import bot
from watcher import Watcher

if __name__ == "__main__":
    logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.DEBUG)
    match sys.argv:
        case [_, "bot"]:
            bot.run()
        case [_, "watcher"]:
            Watcher.default().run()
        case _:
            raise ValueError(f"Run 'app.py [bot|watcher]'")
