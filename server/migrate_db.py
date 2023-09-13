from sys import exit
import os
from typing import Tuple, List
import logging

try:
    from app.repository import Repository
except KeyError:
    exit("Unable to load svarog.ini - make sure the file is present and has all entries.")


def list_migrations(directory: str, extension=".psql", prefix="svarog-") -> List[Tuple[int, str]]:
    '''
    List all files in @directory meet the convention:
        [@prefix][XX][@extension]
    where XX is number.

    Function return list of pairs: XX number and path. List is sorted by XX number.
    '''
    filenames = os.listdir(directory)

    migrations = []

    for filename in filenames:
        if not filename.endswith(extension):
            continue
        if not filename.startswith(prefix):
            continue
        path = os.path.join(directory, filename)
        if not os.path.isfile(path):
            continue

        version_raw, _ = os.path.splitext(filename)
        version_raw = version_raw.lstrip(prefix)
        version = int(version_raw)
        migrations.append((version, path))

    migrations.sort(key=lambda p: p[0])
    return migrations


def migrate(config=None, migration_directory="db"):
    '''
    Perform migrations.

    Parameters
    ==========
    config
        Dictionary with psycopg2 "connect" method arguments.
        If None then read INI file
    migration_directory: str
        Directory with .psql files. Files must to keep naming convention:
            svarog-XX.psql
        where XX is number of database revision.

    Returns
    =======
    Function print migration status on console. Changes are save in database.

    Notes
    =====
    If any migration fail then all changes are revert.
    '''
    repository = Repository(config)

    db_version = repository.get_database_version()

    migrations = list_migrations(migration_directory)

    with repository.transaction() as transaction:
        for migration_version, migration_path in migrations:
            if migration_version <= db_version:
                logging.info("Skip migration to %d version" % (migration_version,))
                continue

            logging.info("Process migration to %d version..." % (migration_version,), end="")
            with open(migration_path) as migration_file:
                content = migration_file.read()

            repository.execute_raw_query(content)
            logging.info("OK")

        transaction.commit()

    new_db_version = repository.get_database_version()
    logging.info("Migration complete from %d to %d!" % (db_version, new_db_version))


if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG, format='%(asctime)s %(levelname)s %(message)s', datefmt='%H:%M:%S')
    migrate()
