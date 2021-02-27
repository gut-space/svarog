import os
import shutil

import yaml

from utils.models import Configuration
from utils.globalvars import CONFIG_PATH


def open_config() -> Configuration:
    config_path = CONFIG_PATH
    config_exists = os.path.exists(config_path)
    if not config_exists:
        directory = os.path.dirname(config_path)
        os.makedirs(directory, exist_ok=True)

        template_dir = os.getcwd()
        shutil.copyfile(os.path.join(template_dir, 'config.yml.template'), config_path)
        print("WARNING: config file (%s) was missing, generated using template." % config_path)

    with open(config_path) as f:
        return yaml.safe_load(f) # type: ignore


def save_config(config: Configuration):
    with open(CONFIG_PATH, "w") as f:
        return yaml.safe_dump(config, f)
