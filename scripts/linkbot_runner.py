"""
Lazy man's runner for starting linkbots.
"""
import os
import configparser
from linkbot import Linkbot

if __name__ == "__main__":
    config = configparser.ConfigParser()
    config.read(os.path.join(os.path.dirname(__file__), "..", "dullu", "linkbot.conf"))
    lb = Linkbot(broker_address=config[Linkbot.CONFIG_FILE__BROKER_HOST],
                 notification_server_host=config[Linkbot.CONFIG_FILE__BOT_REFERENCE],
                 bot_reference=config[Linkbot.CONFIG_FILE__BOT_REFERENCE])
    lb.run()
