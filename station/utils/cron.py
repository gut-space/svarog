import sys
import os.path
from typing import Optional

from crontab import CronTab

from utils.globalvars import DEV_ENVIRONMENT, CONFIG_DIRECTORY


def _get_command(directory: Optional[str], filename: str):
    """Returns an absolute path to the file in directory."""
    if directory is None:
        directory = sys.argv[0]
    if not os.path.isdir(directory):
        directory = os.path.dirname(directory)
    path = os.path.join(directory, filename)
    path = os.path.abspath(path)
    return path


def get_planner_command(directory=None):
    """Returns a shell command to be executed to start a planner."""
    return "python3 %s " % _get_command(directory, "planner.py")


def get_receiver_command(directory=None):
    """Returns a shell command to be executed to receive transmission."""
    return "python3 %s " % _get_command(directory, "receiver.py")


def get_updater_command(directory=None):
    """Returns an absolute path to the update.sh script, to be used by cron job."""
    return _get_command(directory, "update.sh")


def open_crontab() -> CronTab:
    if DEV_ENVIRONMENT:
        path = os.path.join(CONFIG_DIRECTORY, "crontab")
        if not os.path.exists(path):
            with open(path, "x") as _:
                pass
        return CronTab(tabfile=path)
    else:
        return CronTab(user=True)
