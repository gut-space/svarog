import os
from configparser import ConfigParser
import uuid
from functools import wraps
from contextlib import contextmanager

import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

from migrate_db import migrate
from app.repository import Repository


# The relative path to the root directory.
_root_dir = os.path.dirname(os.path.realpath(__file__))
_root_dir = os.path.dirname(_root_dir)


def _read_configurations():
    '''Read the configuration file in the root directory.'''
    ini_path = os.path.join(_root_dir, 'svarog.ini')

    config = ConfigParser()
    config.optionxform = str
    config.read(ini_path)
    config = config['database']

    config = dict(**config)
    maintenance_config = config.copy()

    # The possibility to provide the separate maintenance credentials
    # if the standard user has limited privileges.
    # They are used only to create, migrate and drop database.
    # The test are running using the standard credentials.
    maintenance_mapping = {
        'maintenance_user': 'user',
        'maintenance_password': 'password',
        'maintenance_database': 'database'
    }

    for from_, to in maintenance_mapping.items():
        if from_ in maintenance_config:
            maintenance_config[to] = maintenance_config[from_]
            del maintenance_config[from_]
            del config[from_]

    # The main database from the configuration is not touched.
    # The database name is used as a prefix for the test databases.
    pattern_database_name = config.get('database', 'postgres')
    test_database_name = f'{pattern_database_name}-{uuid.uuid4()}'
    test_database_name = test_database_name.replace('-', '_')
    config['database'] = test_database_name

    return config, maintenance_config


def _standard_seed_db(config):
    '''Migrate and seed the test database.'''
    migrate(config, os.path.join(_root_dir, 'db'))

    with psycopg2.connect(**config) as conn:
        with conn.cursor() as cursor:
            with open(os.path.join(_root_dir, "tests", "db-data.psql"), "rt") as f:
                cursor.execute(f.read())
                conn.commit()


@contextmanager
def setup_database_test_case():
    '''Create the test database, migrate it to the latest version, and
    destroy after test case.'''
    user_config, maintenance_config = _read_configurations()

    maintenance_in_user_config = maintenance_config.copy()
    maintenance_in_user_config['database'] = user_config['database']

    user = user_config.get('user', 'postgres')
    database = user_config['database']

    maintenance_connection = psycopg2.connect(**maintenance_config)
    maintenance_connection.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
    maintenance_cursor = maintenance_connection.cursor()

    create_database_query = f'CREATE DATABASE {database} OWNER {user};'
    maintenance_cursor.execute(create_database_query)

    maintenance_cursor.close()
    maintenance_connection.close()

    _standard_seed_db(maintenance_in_user_config)

    try:
        yield user_config
    finally:
        maintenance_connection = psycopg2.connect(**maintenance_config)
        maintenance_connection.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        maintenance_cursor = maintenance_connection.cursor()

        drop_database_query = f'DROP DATABASE {database};'
        maintenance_cursor.execute(drop_database_query)

        maintenance_cursor.close()
        maintenance_connection.close()


def use_repository(f):
    '''The test case decorator that passes the repository object
    as the first argument. The repository uses the test database.
    The database is destroyed after the test case.'''
    @wraps(f)
    def wrapper(self, *args, **kwargs):
        with setup_database_test_case() as config:
            repository = Repository(config)
            return f(self, repository, *args, **kwargs)
    return wrapper
