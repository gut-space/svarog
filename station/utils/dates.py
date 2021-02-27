import datetime
import dateutil
import sys


def from_iso_format(raw: str) -> datetime.datetime:
    if sys.version_info <= (3, 6):
        return dateutil.parser.isoparse(raw)
    else:
        return datetime.datetime.fromisoformat(raw)


def utc_to_local(utc_dt):
    return utc_dt.replace(tzinfo=datetime.timezone.utc).astimezone(tz=None)
