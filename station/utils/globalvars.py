import os
import logging


DEV_ENVIRONMENT =  os.environ.get("DEV_ENVIRONMENT") == '1'
APP_NAME = "svarog"
COMMENT_PASS_TAG = APP_NAME + "-pass"
COMMENT_PLAN_TAG = APP_NAME + "-plan"
COMMENT_UPDATE_TAG = APP_NAME + "-update"

CONFIG_DIRECTORY: str = os.environ.get("SVAROG_CONFIG_DIR") # type: ignore
if CONFIG_DIRECTORY is None:
    if DEV_ENVIRONMENT:
        CONFIG_DIRECTORY = os.path.abspath("./config")
    else:
        CONFIG_DIRECTORY = os.path.expanduser("~/.config/%s" % (APP_NAME,))

CONFIG_PATH = os.path.join(CONFIG_DIRECTORY, "config.yml")
LOG_FILE = os.path.join(CONFIG_DIRECTORY, "log") if not DEV_ENVIRONMENT else None

if not os.path.exists(CONFIG_DIRECTORY):
    os.makedirs(CONFIG_DIRECTORY, exist_ok=True)

logging.basicConfig(level=logging.DEBUG if DEV_ENVIRONMENT else logging.ERROR,
                    format='%(asctime)s %(levelname)s %(filename)s:%(lineno)d: %(message)s',
                    filename=LOG_FILE)
