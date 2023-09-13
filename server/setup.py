#!/usr/bin/env python3
from migrate_db import migrate
import datetime
from os import getcwd, path, makedirs, environ
import shutil
import sys

from setuptools import setup, find_packages

# STEP 1: install python packages
REQUIREMENTS = [i.strip() for i in open("requirements.txt").readlines()]

setup(name='svarog-server',
      version='1.0',
      description='svarog server',
      author='SF, TM',
      packages=find_packages(),
      install_requires=REQUIREMENTS
      )

# STEP 2: ensure the config is exists
config_path = "svarog.ini"
if not path.exists(config_path):
    shutil.copyfile("svarog.ini.template", config_path)

    # The chance that the template would actually work are pathetic. Need to tell the user to
    # tweak it to his/her specific needs.
    print("NOTE: Template config file copied over to %s" % config_path)
    print("NOTE: Please edit it to match your configuration and rerun the setup script again.")
    sys.exit(-1)

# STEP 3: ensure the database is updated.


def backup_database():
    import subprocess
    try:
        from configparser import ConfigParser
    except ImportError:
        from ConfigParser import ConfigParser
    backup_dir = "backups"
    makedirs(backup_dir, exist_ok=True)
    config = ConfigParser()
    config.read(config_path)
    db = config["database"]
    now = datetime.datetime.utcnow()
    timestamp_filename = "svarog-%s.backup" % (now.isoformat())
    backup_path = path.join(backup_dir, timestamp_filename)
    env = environ.copy()
    env["PGPASSWORD"] = db["password"]
    subprocess.check_call(
        ["pg_dump",
         "--host", db["host"],
         "--port", db.get("port", "5432"),
         "--username", db["user"],
         "--dbname", db["database"],
         "--format", "c",  # Custom
         "--compress", "8",
         "--no-password",
         "--file", backup_path
         ], env=env
    )
    if not path.exists(backup_path):
        raise FileNotFoundError(backup_path)
    print("Backup created here: %s" % (backup_path,))


backup_database()
migrate()

# STEP 4: make sure the update script will be called every day
COMMENT_UPDATE_TAG = 'svarog-update'


def install_update_cronjob():
    print("Installing cronjob")
    from crontab import CronTab
    cron = CronTab(user=True)

    # remove old cronjobs (if any)
    cron.remove_all(comment=COMMENT_UPDATE_TAG)

    # This job will pull the new code at noon
    job = cron.new(command="cd " + getcwd() + " && ./update.sh", comment=COMMENT_UPDATE_TAG)
    job.setall('0 12 * * *')

    cron.write()


install_update_cronjob()

print("Installation complete.")
