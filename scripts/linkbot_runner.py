"""
Lazy man's runner for starting linkbots.
"""
import os
import configparser
from linkbot import Linkbot

if __name__ == "__main__":
    config = configparser.ConfigParser()
    config.read(os.path.join(os.path.dirname(__file__), "..", "dullu", "linkbot.conf"))
    settings = config[Linkbot.CONFIG_FILE__SECTION_SETTINGS]
    lb = Linkbot(broker_address=settings[Linkbot.CONFIG_FILE__BROKER_HOST],
                 bot_reference=settings[Linkbot.CONFIG_FILE__BOT_REFERENCE],
                 notification_server_host=settings[Linkbot.CONFIG_FILE__NOTIFICATION_SERVER_HOST],
                 notification_server_username=settings[Linkbot.CONFIG_FILE__NOTIFICATION_SERVER_USERNAME],
                 notification_server_password=settings[Linkbot.CONFIG_FILE__NOTIFICATION_SERVER_PASSWORD])
    lb.run()
