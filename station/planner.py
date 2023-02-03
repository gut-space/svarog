"""
Code related to getting upcoming sat passes and planning observations.
"""

import datetime
import sys
from typing import Sequence
from colored import fg

from orbit_predictor.locations import Location
from datetimerange import DateTimeRange
from dateutil import tz

from selectstrategy import strategy_factory, Observation
from utils.globalvars import COMMENT_PASS_TAG
from utils.models import set_satellite_defaults, get_location, Configuration
from utils.cron import get_receiver_command, open_crontab
from utils.configuration import open_config
from utils.dates import utc_to_local
from orbitdb import OrbitDatabase

RECEIVER_COMMAND = get_receiver_command()

prediction_config = open_config()


def get_command(name: str, range_: DateTimeRange):
    return RECEIVER_COMMAND + '"%s" "%s"' % (name, range_.end_datetime.isoformat())


def get_passes(config: Configuration, from_: datetime.datetime, to: datetime.datetime):
    location = Location(*get_location(config))
    satellites = filter(lambda s: not s.get("disabled", False), config["satellites"])
    strategy_name: str = config.get("strategy", "max-elevation")  # type: ignore

    orbit_db = OrbitDatabase(config["norad"])
    strategy = strategy_factory(strategy_name)

    init = []
    for sat in satellites:
        set_satellite_defaults(config, sat)
        aos_at = sat["aos_at"]
        max_elevation_greater_than = sat["max_elevation_greater_than"]
        predictor = orbit_db.get_predictor(sat["name"])

        passes = predictor.passes_over(location, from_, to, max_elevation_greater_than, aos_at_dg=aos_at)

        # orbit predictor is using naive dates (no timezone info)
        # We could force the tzinfo to be utc here like this:
        #
        # p.aos = p.aos.replace(tzinfo=datetime.timezone.utc)
        # p.los = p.los.replace(tzinfo=datetime.timezone.utc)
        #
        # but then many places in the code would have to be updated to
        # also deal with timezones. Let's play along and keep it naive.
        init += [(sat["name"], p) for p in passes]

        for p in passes:
            init.append((sat["name"], p))

    selected = strategy(init)
    return selected


def get_timestamp_str(timestamp: datetime, timezone: tz.tz) -> str:
    # orbital predictor returns timestamps in naive format (no timezones).
    # To do any timezone conversions, we need to first force it to UTC
    # if no timezone was specified.
    if timestamp.tzinfo is None:
        timestamp = timestamp.replace(tzinfo=datetime.timezone.utc)
    return f"{timestamp.astimezone(timezone).strftime('%Y-%m-%d %H:%M:%S')} {timestamp.astimezone(timezone).tzname()}"


def plan_passes(selected: Sequence[Observation], cron):
    selected = sorted(selected, key=lambda o: o.pass_.aos)
    for entry in selected:
        cmd = get_command(entry.data, entry.range)
        job = cron.new(cmd, COMMENT_PASS_TAG)
        start_datetime = utc_to_local(entry.range.start_datetime)
        job.setall(start_datetime)
    cron.write()


def print_passes(passes, config: Configuration):
    """Pretty prints the passes."""

    orbit_db = OrbitDatabase(config["norad"])

    name_width = 12  # width of the sat names
    passes = sorted(passes, key=lambda x: x[1].aos)
    n = fg(15)  # normal text

    print(" Satellite   | Norad | AOS                      | LOS                      | Max alt. (deg)")
    print("-------------+-------+--------------------------+--------------------------+----------------")

    for p in passes:
        max_alt = p[1].max_elevation_deg
        if max_alt > 60:
            c = fg(10)  # green
        elif max_alt > 20:
            c = fg(11)  # yellow
        else:
            c = fg(9)  # red

        timezone = datetime.timezone.utc if not True else tz.tzlocal()
        norad = orbit_db.get_norad(p[0])

        aos_txt = get_timestamp_str(p[1].aos, timezone)
        los_txt = get_timestamp_str(p[1].los, timezone)

        print(f"{p[0]:{name_width}} | {norad:3.0f} | {c}{aos_txt:<24}{n} | {c}{los_txt:<24}{n} | {c}{p[1].max_elevation_deg:4.1f}{n}")


def clear(cron):
    cron.remove_all(comment=COMMENT_PASS_TAG)
    cron.write()


def execute(interval: int, cron=None, dry_run: bool = False):
    """_summary_

    :param interval: interval, expressed in seconds
    :param cron: _description_, defaults to None
    :param dry_run: _description_, defaults to False
    :return: List of passes
    """
    if cron is None:
        cron = open_crontab()
    start = datetime.datetime.utcnow()
    delta = datetime.timedelta(seconds=interval)
    end = start + delta

    passes = get_passes(prediction_config, start, end)

    if dry_run:
        print_passes(passes, prediction_config)
    else:
        clear(cron)
        plan_passes(passes, cron)

    return passes


if __name__ == '__main__':
    interval = int(sys.argv[1]) if len(sys.argv) > 1 else 24 * 60 * 60
    execute(interval)
