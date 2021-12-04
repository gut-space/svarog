import os
import logging
import yaml


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
METADATA_FILE = os.path.join(CONFIG_DIRECTORY, "metadata.json")

if not os.path.exists(CONFIG_DIRECTORY):
    os.makedirs(CONFIG_DIRECTORY, exist_ok=True)


# Loglevel is a bit complicated. By default, it's ERROR, unless it's set in the config file,
# unless it's a dev environment which is always DEBUG.
loglevel = logging.ERROR

try:
    with open(CONFIG_PATH) as f:
        config = yaml.safe_load(f) # type: ignore
        lv = config["logging"]["level"]
        loglevel = logging._nameToLevel[lv]
except:
    pass

if DEV_ENVIRONMENT:
    loglevel = logging.DEBUG


logging.basicConfig(level = loglevel,
                    format='%(asctime)s %(levelname)s %(filename)s:%(lineno)d: %(message)s',
                    filename=LOG_FILE)
