'''
Module encapsulate database operations.
It is responsible for create and execute SQL queries and support transactional.
'''

from datetime import datetime
from functools import wraps
from typing import Any, List, NewType, Sequence, Union, Optional, Tuple, Dict
from enum import Enum
import sys
from collections import defaultdict

if sys.version_info >= (3, 8):
    from typing import TypedDict
else:
    from typing_extensions import TypedDict

import psycopg2
from psycopg2.extras import RealDictCursor
from app.utils import first

# Data model

ObservationId = NewType("ObservationId", int)
ObservationFileId = NewType("ObservationFileId", int)
StationId = NewType("StationId", int)
SatelliteId = NewType("SatelliteId", int)
StationPhotoId = NewType("StationPhotoId", int)


class ObservationFile(TypedDict):
    obs_file_id: ObservationFileId
    filename: str
    media_type: str
    obs_id: ObservationId
    rating: Optional[float]


class Observation(TypedDict):
    obs_id: ObservationId
    aos: datetime
    tca: datetime
    los: datetime
    sat_id: SatelliteId
    thumbnail: str
    config: Optional[Dict]
    station_id: StationId
    tle: Optional[List[str]]


class ObservationFilter(TypedDict, total=False):
    obs_id: ObservationId
    aos_before: datetime
    los_after: datetime
    sat_id: SatelliteId
    notes: str
    station_id: StationId
    has_tle: bool


class Satellite(TypedDict):
    sat_id: SatelliteId
    sat_name: str


class Station(TypedDict):
    station_id: StationId
    name: str
    lon: float
    lat: float
    descr: str
    config: str
    registered: datetime


class StationStatistics(TypedDict):
    observation_count: int
    last_los: Optional[datetime]


class StationPhoto(TypedDict):
    photo_id: StationPhotoId
    station_id: StationId
    sort: int
    filename: str
    descr: str


class UserRole(Enum):
    REGULAR = 1
    OWNER = 2
    ADMIN = 3
    BANNED = 4


class User(TypedDict):
    id: int
    username: str
    digest: str
    email: str
    role: UserRole

# Lists all stations owned by specific user


class Stations(TypedDict):
    stations: List[Tuple[str, StationId]]  # station name, station_id

# List all users that own a particular station


class StationOwners(TypedDict):
    owners: List[Tuple[str, int]]  # username, user_id

# Utils


def without_keys(d, keys: Sequence[str]):
    return {x: d[x] for x in d if x not in keys}


def exclude_from_dict(d, keys: Sequence[str]):
    excluded = [d[k] for k in keys]
    obj = without_keys(d, keys)

    return [obj,] + excluded


class DefaultDictWithAnyKey(defaultdict):
    '''
    Same as defaultdict, but always return True if you check
    key existance. Idea: if defaultdict returns value for any
    key then it should return that contains any key.
    For expected work you should pass @default_factory in
    constructor.
    '''

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def __contains__(self, item):
        return True

# Errors


class RepositoryError(Exception):
    '''Base class for Repository module errors.'''

    def __init__(self, message: str):
        super().__init__(message)


class TransactionAlreadyOpenError(RepositoryError):
    def __init__(self):
        super().__init__("Other transaction is already open on this repository. "
                         "You may to have only one transaction opened in the same time")


# Psycopg2 doesn't provide typing in current version.
Connection = Any
Cursor = RealDictCursor


class _TransactionContext(TypedDict):
    conn: Connection
    cursor: Cursor


def use_cursor(f):
    '''
    Decorator who ensures that connection is established and has created cursor.

    If no transaction is pending then it will be create before execution and commit
    (if execution not throw exceptions) and close after.

    If transaction is pending then it will be used, but not commit after execution.

    You need use this decorator before any public method (endpoint) in repository
    if it uses database connection.
    '''
    @wraps(f)
    def wrapper(*args, **kwargs):
        self_obj: Repository = args[0]

        if self_obj.is_pending_transaction:
            res = f(*args, **kwargs)
        else:
            with self_obj.transaction() as t:
                res = f(*args, **kwargs)
                t.commit()

        return res

    return wrapper


class Repository:
    '''
    Class for communication with database.

    You can use it with or without transactional.
    If you don't open transaction manually then it will
    be create, commit and close automatically.

    For transactional use .transaction method with context manager.
    '''

    def __init__(self, config=None):
        '''
        Config is dictionary of psycopg2.connect method. If you don't
        provide it then data from INI will be used.
        '''
        if config is None:
            from app import app
            config = app.config["database"]
        self._config = config
        self._transaction_context: Optional[_TransactionContext] = None  # type: ignore

    @property
    def is_pending_transaction(self):
        return self._transaction_context is not None

    @property
    def _cursor(self) -> Cursor:
        '''Return Cursor in curret transacion.'''
        context = self._transaction_context
        return context.get("cursor")

    @use_cursor
    def count_observations(self, filters: ObservationFilter = {}) -> int:
        q = ("SELECT COUNT(*) as count "
             "FROM observations "
             "WHERE (%(obs_id)s IS NULL OR obs_id = %(obs_id)s) AND "
             "(%(aos_before)s IS NULL OR aos <= %(aos_before)s) AND "
             "(%(los_after)s IS NULL OR los >= %(los_after)s) AND "
             "(%(sat_id)s IS NULL OR sat_id = %(sat_id)s) AND "
             "(%(station_id)s IS NULL OR station_id = %(station_id)s) AND "
             "(%(notes)s IS NULL OR notes ILIKE '%%' || %(notes)s || '%%') AND "
             "(%(has_tle)s IS NULL OR (tle IS NOT NULL) = %(has_tle)s);")
        cursor = self._cursor
        query_kwargs = DefaultDictWithAnyKey(lambda: None)
        query_kwargs.update(filters)
        cursor.execute(q, query_kwargs)
        return cursor.fetchone()["count"]

    @use_cursor
    def read_observations(self, filters: ObservationFilter = {}, limit: int = 100,
                          offset: int = 0, order: str = "o.aos DESC", expr: str = "TRUE") -> Sequence[Observation]:
        '''Returns observations that match specified criteria.

        Parameters
        filters - a dictionary with optional filtering parameters
        limit - max number of rows to return
        offset - if returning not the first page
        order - how to order the rows (optional)
        expr - addtional custom expression passed to WHERE clause
        '''

        # Most of the parameters are substituted by psycopg2 cursor. Those are dynamic
        # parameters, i.e. those are specified by the user (using filtering on a page).
        # The other type of parameters expr and order are strictly defined by the Svarog
        # code. And honestly, I was not able to make psycopg2 use them without adding
        # extra quotes.
        q = ("SELECT o.obs_id, o.aos, o.tca, o.los, o.sat_id, o.thumbnail, "
             "o.station_id, o.notes, o.tle, r.rating, o.config "
             "FROM observations o "
             "LEFT JOIN observation_ratings r ON o.obs_id = r.obs_id "
             "WHERE (%(obs_id)s IS NULL OR o.obs_id = %(obs_id)s) AND "
             "(%(aos_before)s IS NULL OR o.aos <= %(aos_before)s) AND "
             "(%(los_after)s IS NULL OR o.los >= %(los_after)s) AND "
             "(%(sat_id)s IS NULL OR o.sat_id = %(sat_id)s) AND "
             "(%(station_id)s IS NULL OR o.station_id = %(station_id)s) AND "
             "(%(notes)s IS NULL OR o.notes ILIKE '%%' || %(notes)s || '%%') AND "
             "(%(has_tle)s IS NULL OR (o.tle IS NOT NULL) = %(has_tle)s) "
             f"AND {expr} ORDER BY {order} "
             "LIMIT %(limit)s OFFSET %(offset)s")
        cursor = self._cursor
        query_kwargs = DefaultDictWithAnyKey(lambda: None)
        query_kwargs.update(filters)
        query_kwargs.update({'limit': limit, 'offset': offset})
        cursor.execute(q, query_kwargs)
        return cursor.fetchall()

    def read_observation(self, obs_id: ObservationId) -> Optional[Observation]:
        observations = self.read_observations({'obs_id': obs_id}, limit=1)
        if len(observations) == 0:
            return None
        return observations[0]

    @use_cursor
    def insert_observation(self, observation: Observation) -> ObservationId:
        cursor = self._cursor
        cursor.execute(
            "INSERT INTO observations "
            "(aos, tca, los, sat_id, thumbnail, config, station_id, tle) "
            "VALUES (%(aos)s, %(tca)s, %(los)s, %(sat_id)s, %(thumbnail)s, "
            "%(config)s, %(station_id)s, %(tle)s) "
            "RETURNING obs_id;",
            {
                'aos': observation["aos"].isoformat(),
                'tca': observation['tca'].isoformat(),
                'los': observation['los'].isoformat(),
                'sat_id': observation['sat_id'],
                'thumbnail': observation['thumbnail'],
                'config': observation['config'],
                'station_id': observation['station_id'],
                'tle': observation['tle']
            }
        )
        return cursor.fetchone()['obs_id']

    @use_cursor
    def delete_observation(self, obs_id: ObservationId):
        q = ("DELETE "
             "FROM observations "
             "WHERE obs_id = %s;")
        cursor = self._cursor
        cursor.execute(q, (obs_id,))

    @use_cursor
    def count_observation_files(self, obs_id: ObservationId) -> int:
        q = ("SELECT COUNT(*) as count "
             "FROM observation_files "
             "WHERE obs_id = %s")
        cursor = self._cursor
        cursor.execute(q, (obs_id,))
        return cursor.fetchone()["count"]

    @use_cursor
    def read_observation_files(self, obs_id: ObservationId,
                               limit: int = 100, offset: int = 0) -> Sequence[ObservationFile]:
        q = ("SELECT obs_file_id, filename, media_type, obs_id, rating "
             "FROM observation_files "
             "WHERE obs_id = %s "
             "ORDER BY obs_file_id "
             "LIMIT %s OFFSET %s")
        cursor = self._cursor
        cursor.execute(q, (obs_id, limit, offset))
        return cursor.fetchall()

    @use_cursor
    def insert_observation_file(self, observation_file: ObservationFile) -> ObservationFileId:
        q = ("INSERT INTO observation_files "
             "(filename, media_type, obs_id, rating) "
             "VALUES "
             "(%(filename)s, %(media)s, %(obs)s, %(rating)s) "
             "RETURNING obs_file_id;")
        cursor = self._cursor
        cursor.execute(q, {
            'filename': observation_file['filename'],
            'media': observation_file['media_type'],
            'obs': observation_file['obs_id'],
            'rating': observation_file['rating']
        })
        return cursor.fetchone()['obs_file_id']

    @use_cursor
    def read_satellites(self, limit: int = 100, offset: int = 0) -> Optional[Satellite]:
        q = ("SELECT sat_id, sat_name "
             "FROM satellites "
             "LIMIT %s OFFSET %s;")
        cursor = self._cursor
        cursor.execute(q, (limit, offset))
        return cursor.fetchall()

    @use_cursor
    def read_satellite(self, sat: Union[SatelliteId, str]) -> Optional[Satellite]:
        if isinstance(sat, str):
            q = "SELECT sat_id, sat_name FROM satellites WHERE sat_name = %s LIMIT 1;"
        else:
            q = "SELECT sat_id, sat_name FROM satellites WHERE sat_id = %s LIMIT 1;"
        cursor = self._cursor
        cursor.execute(q, (sat,))
        return cursor.fetchone()

    @use_cursor
    def count_stations(self) -> int:
        q = ("SELECT COUNT(*) as count "
             "FROM stations")
        cursor = self._cursor
        cursor.execute(q)
        return cursor.fetchone()["count"]

    @use_cursor
    def owned_stations(self, user_id: int) -> Stations:

        q = ("SELECT s.name, s.station_id "
             "FROM stations s "
             "JOIN station_owners ON s.station_id = station_owners.station_id WHERE station_owners.user_id = %s "
             "ORDER BY s.station_id desc")
        cursor = self._cursor
        cursor.execute(q, (user_id,))
        return cursor.fetchall()

    @use_cursor
    def station_owners(self, station_id: int) -> StationOwners:
        q = ("SELECT u.username, u.id FROM users u JOIN station_owners o ON u.id = o.user_id WHERE o.station_id = %s")
        cursor = self._cursor
        cursor.execute(q, (station_id,))
        return cursor.fetchall()

    @use_cursor
    def is_station_owner(self, user_id: int, station_id: StationId) -> bool:
        """Returns true if the specified user is the station owner, and false otherwise"""
        q = ("SELECT true FROM station_owners WHERE user_id = %s AND station_id = %s")
        cursor = self._cursor
        cursor.execute(q, (user_id, station_id,))
        # The query returns 0 or 1 rows.
        return bool(cursor.rowcount)

    @use_cursor
    def read_stations(self, limit=100, offset=0) -> Sequence[Station]:
        q = ("SELECT s.station_id, s.name, s.lon, s.lat, s.descr, s.config, s.registered "
             "FROM stations s "
             "ORDER BY s.station_id "
             "LIMIT %s OFFSET %s;")

        cursor = self._cursor
        cursor.execute(q, (limit, offset))
        return cursor.fetchall()

    @use_cursor
    def read_station(self, id_: StationId) -> Optional[Station]:
        q = ("SELECT s.station_id, s.name, s.lon, s.lat, s.descr, s.config, s.registered "
             "FROM stations s "
             "WHERE s.station_id = %s "
             "LIMIT 1")

        cursor = self._cursor
        cursor.execute(q, (id_,))
        return cursor.fetchone()

    @use_cursor
    def read_station_statistics(self, station_id: StationId) \
            -> Optional[StationStatistics]:
        q = ("SELECT COUNT(o) AS observation_count, MAX(o.los) AS last_los, "
             "MIN(o.aos) AS first_aos "
             "FROM stations s "
             "LEFT JOIN observations o ON s.station_id = o.station_id "
             "WHERE s.station_id = %s "
             "GROUP BY s.station_id "
             "LIMIT 1")
        cursor = self._cursor
        cursor.execute(q, (station_id,))
        return cursor.fetchone()

    @use_cursor
    def read_stations_statistics(self, limit: int = 100, offset: int = 0) \
            -> Sequence[StationStatistics]:
        q = ("SELECT COUNT(o) AS observation_count, MAX(o.los) AS last_los "
             "FROM stations s "
             "LEFT JOIN observations o ON s.station_id = o.station_id "
             "GROUP BY s.station_id "
             "ORDER BY s.station_id "
             "LIMIT %s OFFSET %s;")
        cursor = self._cursor
        cursor.execute(q, (limit, offset,))
        return cursor.fetchall()

    @use_cursor
    def read_station_photos(self, id_: StationId) -> Sequence[StationPhoto]:
        q = ("SELECT photo_id, station_id, sort, filename, descr "
             "FROM station_photos "
             "WHERE station_id = %s")

        cursor = self._cursor
        cursor.execute(q, (id_,))
        return cursor.fetchall()

    @use_cursor
    def read_station_secret(self, station_id: StationId) -> Optional[bytes]:
        query = "SELECT secret FROM stations WHERE station_id = %s"
        cursor = self._cursor
        cursor.execute(query, (station_id,))
        row = cursor.fetchone()
        # If there's no such station or the station's configuration is broken (i.e. doesn't have any secret set)
        if row is None or row["secret"] is None:
            return None

        return bytes(row["secret"])

    def user_role_to_enum(self, role: str) -> UserRole:
        """Converts string to UserRole enum"""
        u = first(lambda u: u.name == role.upper(), UserRole)
        if u is not None:
            return u

        # Rage quit if we're not able to figure the role out
        raise LookupError("can't convert %s to any known user roles." % role)

    @use_cursor
    def read_user(self, user: Union[int, str]) -> Optional[User]:
        if isinstance(user, int):
            query = "SELECT id, username, digest, email, role FROM users WHERE id = %s"
        else:
            query = "SELECT id, username, digest, email, role FROM users WHERE username = %s"
        cursor = self._cursor
        cursor.execute(query, (user,))

        row = cursor.fetchone()
        u = None
        if row:
            row['role'] = self.user_role_to_enum(row['role'])
            u = User(row)
        return u

    @use_cursor
    def get_database_version(self) -> int:
        '''
        Returns database version. Return 0 if database is empty.
        @see: https://stackoverflow.com/a/42693458
        '''
        is_database_empty_query = ("SELECT count(*) AS count "
                                   "FROM pg_class c "
                                   "JOIN pg_namespace s ON s.oid = c.relnamespace "
                                   "WHERE s.nspname NOT IN ('pg_catalog', 'information_schema') "
                                   "AND s.nspname NOT LIKE 'pg_temp%' "
                                   "AND s.nspname <> 'pg_toast'")

        cursor = self._cursor
        cursor.execute(is_database_empty_query)
        is_database_empty = cursor.fetchone()["count"] == 0

        if is_database_empty:
            return 0

        exists_query = ("SELECT EXISTS ( "
                        "SELECT FROM information_schema.tables "
                        "WHERE table_schema = 'public' "
                        "AND  table_name = 'schema' "
                        ");")
        cursor.execute(exists_query)
        res = cursor.fetchone()
        is_table_version_exists = len(res) == 1
        if not is_table_version_exists:
            return 1

        version_query = 'SELECT "version" FROM "schema" LIMIT 1'
        try:
            cursor.execute(version_query)
            row = cursor.fetchone()
            if row is None:
                raise Exception("Database version not set")
            return row["version"]
        except BaseException:
            print("Failed to select schema version, assuming 0")
            return 0

    @use_cursor
    def execute_raw_query(self, query):
        cursor = self._cursor
        cursor.execute(query)

    def transaction(self):
        '''Create new transaction.'''
        return Transaction(self)


class Transaction:
    def __init__(self, repository: Repository):
        self._repository = repository

    @property
    def _transaction_context(self) -> Optional[_TransactionContext]:
        '''Retrive context from repository'''
        repository = self._repository
        return repository._transaction_context

    @_transaction_context.setter
    def _transaction_context(self, transaction_context: Optional[_TransactionContext]):
        '''Set new context in repository'''
        self._repository._transaction_context = transaction_context

    def commit(self):
        '''Save changes permanently'''
        context = self._transaction_context
        conn = context["conn"]
        conn.commit()

    def rollback(self):
        '''Revert changes'''
        context = self._transaction_context
        conn = context["conn"]
        conn.rollback()

    def __enter__(self):
        '''Open new connection and cursor. Store them in repository.'''
        if self._transaction_context is not None:
            raise TransactionAlreadyOpenError()

        config = self._repository._config
        conn: Connection = psycopg2.connect(**config)
        cursor: Cursor = conn.cursor(cursor_factory=RealDictCursor)
        transaction_context: _TransactionContext = {
            'conn': conn,
            'cursor': cursor
        }
        self._transaction_context = transaction_context
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        '''
        Close connections. If changes aren't committed then
        they are lost. If any exception is thrown then connection
        is closed safely and exception is propagate.
        '''
        context = self._transaction_context
        context["cursor"].close()
        context["conn"].close()
        self._transaction_context = None
