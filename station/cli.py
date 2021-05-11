#!/usr/bin/env python3

import argparse
import datetime
from typing import Tuple
from dateutil import tz
import calendar
import os
from pprint import pprint
import sys
import itertools

from deepdiff import DeepHash

import planner
from orbitdb import OrbitDatabase
from utils.models import SatelliteConfiguration, get_location, get_satellite
from utils.configuration import open_config, save_config
from utils.functional import first
from utils.globalvars import APP_NAME, LOG_FILE, COMMENT_PASS_TAG, COMMENT_PLAN_TAG, COMMENT_UPDATE_TAG, CONFIG_PATH
from utils.dates import from_iso_format
from utils.cron import  get_planner_command, get_receiver_command, open_crontab
from recipes.factory import get_recipe_names
from quality_ratings import get_rate_names

def get_interval(job):
    frequency = job.frequency()
    year = datetime.datetime.utcnow().year
    days_in_year = 366 if calendar.isleap(year) else 365
    interval = int(round((days_in_year * 24 * 60 * 60 * 1.0) / frequency))
    return interval

def update_config(config, args, names):
    for name in names:
        if isinstance(name, str):
            config_name, args_name = name, name
        else:
            config_name, args_name = name

        arg = getattr(args, args_name, None)
        if arg is None:
            continue

        config[config_name] = getattr(args, args_name)

def get_hash(obj):
    return DeepHash(obj)[obj]

def hex_bytes(value):
    try:
        bytearray.fromhex(value)
    except ValueError:
        raise argparse.ArgumentTypeError("%s is invalid hex bytes value" % (value,))
    return value

def exist_directory(x: str) -> str:
    """
    'Type' for argparse - checks that directory exists but does not open.
    """
    if not os.path.exists(x):
        # Argparse uses the ArgumentTypeError to give a rejection message like:
        # error: argument input: x does not exist
        raise argparse.ArgumentTypeError("{0} does not exist".format(x))
    if not os.path.isdir(x):
        raise argparse.ArgumentTypeError("%s isn't a directory" % (x,))
    return x

def parse_receiver_job(job) -> Tuple[str, datetime.datetime, datetime.datetime]:
    '''
    Parse receiver job CRON entry.
    Returns satellite name, AOS and LOS.
    AOS is recover from job start date. Therefore it has one minute accuracy.
    '''
    parameters = job.command.replace(RECEIVER_COMMAND, "")
    sat_name, los_raw = parameters.rsplit(maxsplit=1)
    sat_name = sat_name.strip('"')
    los_raw = los_raw.strip('"')

    now = datetime.datetime.now()
    now = now.replace(tzinfo=tz.tzlocal())

    schedule = job.schedule()
    next_ = schedule.get_next()
    next_ = next_.replace(tzinfo=tz.tzlocal())
    prev = schedule.get_prev()
    prev = prev.replace(tzinfo=tz.tzlocal())

    if abs(now - next_) < abs(now - prev):
        aos = next_
    else:
        aos = prev

    los = from_iso_format(los_raw)
    los = los.replace(tzinfo=tz.tzutc())

    return sat_name, aos, los

parser = argparse.ArgumentParser(APP_NAME)
subparsers = parser.add_subparsers(help='commands', dest="command")

clear_parser = subparsers.add_parser(
    'clear', help='Clear all scheduled reception events')

log_parser = subparsers.add_parser(
    'logs', help='Show logs'
)

plan_parser = subparsers.add_parser('plan', help='Schedule planned reception events')
plan_parser.add_argument("--cron", type=str, help='Cron format required. Default "0 4 * * *" for 4:00 AM')
plan_parser.add_argument("--force", action="store_true", default=False, help="Perform planning now. (default: %(default)s)")
plan_parser.add_argument("--skip-update", action="store_true", default=False, help="Disables periodic update. (default: %(default)s)")

pass_parser = subparsers.add_parser("pass", help="Information about passes")
pass_parser.add_argument("target", type=str, help="Pass number or satellite name")
pass_parser.add_argument("--aos", help="AOS in ISO format. If not provided then display next pass", type=from_iso_format, required=False)
pass_parser.add_argument("--step", help="Time step to draw diagram [seconds] (default: 60)", type=lambda v: datetime.timedelta(seconds=int(v)), default=datetime.timedelta(minutes=1))
pass_parser.add_argument("--width", help="Plot width (default: %(default)s)", default=30, type=int)
pass_parser.add_argument("--height", help="Plot height (default: %(default)s)", default=15, type=int)
pass_parser.add_argument("--scale-polar", help="Scale width and height for polar plot (default: %(default)s)", default=0.5, type=float)
scale_elevation_pass_parser = pass_parser.add_mutually_exclusive_group()
scale_elevation_pass_parser.add_argument("--scale-elevation", action="store_true", help="Scale 4x elevation series (default: %(default)s)", dest="scale_elevation", default=True)
scale_elevation_pass_parser.add_argument("--no-scale-elevation", action="store_false", dest="scale_elevation")
utc_group_pass_parser = pass_parser.add_mutually_exclusive_group()
utc_group_pass_parser.add_argument("--utc", action="store_true", help="Print dates in UTC (default: %(default)s)", dest="print_utc", default=False)
utc_group_pass_parser.add_argument("--no-utc", action="store_false", dest="print_utc")

config_parser = subparsers.add_parser("config", help="Configuration")
replan_config_parser_group = config_parser.add_mutually_exclusive_group()
replan_config_parser_group.add_argument("-r", "--replan", action="store_true", help="Force plan now (default: %(default)s)", dest="replan")
replan_config_parser_group.add_argument("--no-replan", action="store_false", help="No force plan now", dest="replan", default=False)
config_subparsers = config_parser.add_subparsers(help="Configurations", dest="config_command")
location_config_parser = config_subparsers.add_parser("location", help="Change groundstation location")

# This section parses content of the config file (located in ~/.config/svarog/config.yml)
location_config_parser.add_argument("-lat", "--latitude", type=float, help="Latitude in degrees")
location_config_parser.add_argument("-lng", "--longitude", type=float, help="Longitude in degrees")
location_config_parser.add_argument("-ele", "--elevation", type=float, help="Elevation in meters")
global_config_parser = config_subparsers.add_parser("global", help="Change global prediction parameters")
global_config_parser.add_argument("-aos", type=int, help="Elevation (in degress) on AOS")
global_config_parser.add_argument("-me", "--max-elevation", type=int, help="Max elevation greater than")
global_config_parser.add_argument("-s", "--strategy", choices=["aos", "max-elevation"], help="Select strategy to track satellites")
submit_global_config_parser = global_config_parser.add_mutually_exclusive_group()
submit_global_config_parser.add_argument("--submit", action="store_true", help="Submit observations to content server", dest="submit", default=None)
submit_global_config_parser.add_argument("--no-submit", action="store_false", help="Don't submit observations to content server", dest="submit", default=None)
global_config_parser.add_argument("--save-to-disk", choices=("NONE", "SIGNAL", "PRODUCT", "ALL"),
    help="Choose data saved on disk (SIGNAL - WAV file, PRODUCT - exported imageries, ALL - both, NONE - nothing")
global_config_parser.add_argument("--directory", type=exist_directory, help="Directory to store observations")
satellite_config_parser = config_subparsers.add_parser("sat", help="Satellite configuration")
satellite_config_parser.add_argument("name", type=str, help="Satellite name", nargs='?')
satellite_config_parser.add_argument("-f", "--frequency", type=str, help="Frequency in Hz. Allowed scientific notation.")
satellite_config_parser.add_argument("-aos", type=int, help="Elevation (in degress) on AOS")
satellite_config_parser.add_argument("-me", "--max-elevation", type=int, help="Max elevation greater than")
satellite_config_parser.add_argument("-d", "--delete", action="store_true", default=False, help="Delete satellite")
satellite_config_parser.add_argument("--recipe", choices=get_recipe_names(), help="Recipe name to handle observation")
satellite_config_parser.add_argument("--rate", choices=get_rate_names(), help="Function to rate quality of imagery")
submit_satellite_config_parser = satellite_config_parser.add_mutually_exclusive_group()
submit_satellite_config_parser.add_argument("--submit", action="store_true", help="Submit observations to content server", dest="submit", default=None)
submit_satellite_config_parser.add_argument("--no-submit", action="store_false", help="Don't submit observations to content server", dest="submit", default=None)
disabled_satellite_config_parser = satellite_config_parser.add_mutually_exclusive_group()
disabled_satellite_config_parser.add_argument("--enabled", action="store_false", help="Enable plan observations", dest="disabled", default=None)
disabled_satellite_config_parser.add_argument("--disabled", action="store_true", help="Disable plan observations", dest="disabled", default=None)
satellite_config_parser.add_argument("--save-to-disk", choices=("SIGNAL", "PRODUCT", "ALL", "INHERIT"),
    help="Choose data saved on disk (SIGNAL - WAV file, PRODUCT - exported imageries, ALL - both, INHERIT - as in global")
norad_config_parser = config_subparsers.add_parser("norad", help="Manage sources NORAD data")
norad_config_parser.add_argument("urls", nargs="*", type=str, help="URLs of NORAD data")
norad_config_parser.add_argument("-d", "--delete", action="store_true", default=False, help="Delete NORAD")
norad_config_parser.add_argument("-r", "--refresh", action="store_true", default=False, help="Re-fetch necessary NORAD files")
server_config_parser = config_subparsers.add_parser("server", help="Manage credentials to connect to content server")
server_config_parser.add_argument("-u", "--url", type=str, help="URL of content server")
server_config_parser.add_argument("--id", type=str, help="Station ID")
server_config_parser.add_argument("-s", "--secret", type=hex_bytes, help="HMAC secret shared with content server")
logging_parser = config_subparsers.add_parser("logging", help="Station logging configuration")
logging_parser.add_argument("--level", choices=("DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"),
    help="Specify the logging level (DEBUG, INFO, WARNING, ERROR, or CRITICAL)", default="ERROR")

args = parser.parse_args()
command = args.command

RECEIVER_COMMAND = get_receiver_command()
PLANNER_COMMAND = get_planner_command()

cron = open_crontab()
planner_job = first(cron.find_comment(COMMENT_PLAN_TAG))

if command == "clear":
    cron.remove_all(comment=COMMENT_PASS_TAG)
    cron.remove_all(comment=COMMENT_PLAN_TAG)
    cron.write()
    print("Cleared all existing jobs")

elif command == "logs":
    if LOG_FILE is None:
        print("Log on console. History not available.")
    else:
        with open(LOG_FILE, "rt") as f:
            print(f.read())

elif command == "plan":
    if not args.skip_update:
        print("Trying to set up cron job for periodic updates.")
        updater_job = first(cron.find_comment(COMMENT_UPDATE_TAG))
        if updater_job is None:
            cmd = os.path.join(os.path.dirname(os.path.realpath(__file__)) , "update.sh")
            updater_job = cron.new(comment=COMMENT_UPDATE_TAG, command=cmd)
            updater_job.setall("55 3 * * *")
            cron.write()
            print("Added cronjob for update, scheduled for 3:55")
        else:
            print("Cron job for update found. Not adding.")
            # TODO: We probably want to remove it and add again, just in case there's an update somewhere.

    if planner_job is None:
        args.cron = args.cron or "0 4 * * *"
        planner_job = cron.new(comment=COMMENT_PLAN_TAG, command="placeholder")

    if args.cron is not None:
        planner_job.setall(args.cron)
        interval = get_interval(planner_job)
        planner_job.set_command(PLANNER_COMMAND + str(interval))
        cron.write()
        print("Planner job %s." % (planner_job.description(
            use_24hour_time_format=True, verbose=True)))

    if args.force:
        interval = get_interval(planner_job)
        planner.execute(interval)
        print("Planned receiver jobs successful")

    if args.cron is None:
        pass_jobs = cron.find_comment(COMMENT_PASS_TAG)
        print("%s Planner" % (planner_job.description(
            use_24hour_time_format=True, verbose=True)))

        for idx, j in enumerate(pass_jobs):
            description = j.description(use_24hour_time_format=True)
            parameters = j.command.replace(RECEIVER_COMMAND, "")

            now = datetime.datetime.now()
            now = now.replace(tzinfo=tz.tzlocal())
            _, aos, los = parse_receiver_job(j)

            if now < aos:
                status = "[ ]"
            elif now > los:
                status = "[x]"
            else:
                status = ">>>"

            print(" ".join([str(idx).rjust(2), status, description, parameters]))

elif command == "pass":
    pass_target = args.target
    if pass_target.isdecimal():
        try:
            pass_jobs = cron.find_comment(COMMENT_PASS_TAG)
            index = int(pass_target)
            job = next(itertools.islice(pass_jobs, index, None))
            sat_name, aos, los = parse_receiver_job(job)
        except StopIteration:
            raise LookupError("Job not found in CronTab.")
    else:
        sat_name = pass_target
        if args.aos is not None:
            aos: datetime.datetime = args.aos
            aos = aos.replace(tzinfo=tz.tzutc())
        else:
            aos = datetime.datetime.utcnow()
            aos = aos.replace(tzinfo=tz.tzutc())

    aos = aos.astimezone(tz.tzutc())
    db = OrbitDatabase()
    config = open_config()
    from orbit_predictor.locations import Location
    location = Location(*get_location(config))
    satellite = get_satellite(config, sat_name)
    predictor = db.get_predictor(sat_name)
    pass_ = predictor.get_next_pass(location, aos, 0, 0)

    target_tz = tz.tzutc() if args.print_utc else tz.tzlocal()

    print("Satellite:", sat_name)
    print("AOS:", str(pass_.aos.astimezone(target_tz)))
    print("LOS:", str(pass_.los.astimezone(target_tz)))
    print("Duration:", str(datetime.timedelta(seconds=pass_.duration_s)))
    print("Max elevation:", "%.2f" % (pass_.max_elevation_deg,), "deg", str(pass_.max_elevation_date.astimezone(target_tz)))
    print("Off nadir", "%.2f" % (pass_.off_nadir_deg,), "deg")

    import az_elev_chart
    az_elev_chart.plot(sat_name, pass_.aos, pass_.los, location,
        args.step, args.width, args.height, args.scale_elevation,
        axis_in_local_time=not args.print_utc, scale_polar=args.scale_polar)

elif command == "config":
    config_command = args.config_command

    print("Loading config file %s" % CONFIG_PATH)

    config = open_config()
    section = config
    init_hash = get_hash(config)

    if config_command == "location":
        section = config["location"]
        update_config(section, args, ("latitude", "longitude", "elevation"))
    elif config_command == "global":
        update_config(config, args, (
            ("aos_at", "aos"),
            ("max_elevation_greater_than", "max_elevation"),
            "strategy",
            "submit",
            "save_to_disk",
            ("directory", "obsdir")
        ))
    elif config_command == "logging":
        print(config)
        if not "logging" in config:
            # Old configs may not have the logging defined. Add the section.
            config["logging"] = { "level": "INFO" }
        section = config["logging"]
        update_config(section, args, (("loglevel", "level")) )
    elif config_command == "sat":
        section = config["satellites"]
        if args.name is not None:
            name: str = args.name
            sat = first(section, lambda item: item["name"] == name)
            if sat is None:
                if not hasattr(args, "frequency") or args.frequency is None:
                    print("Frequency is required for new satellite")
                    sys.exit(1)
                new_sat: SatelliteConfiguration = {
                    "name": name,
                    "freq": ""
                }
                section.append(new_sat)
                sat = new_sat
            if args.delete:
                section.remove(sat)
            else:
                section = sat
                update_config(sat, args, (
                    ("freq", "frequency"),
                    ("aos_at", "aos"),
                    ("max_elevation_greater_than", "max_elevation"),
                    "recipe", "rate"
                ))
                if args.submit and 'submit' in sat:
                    del sat['submit']
                elif args.submit is False:
                    sat['submit'] = args.submit

                if args.save_to_disk == "INHERIT" and 'save_to_disk' in sat:
                    del sat['save_to_disk']
                elif args.save_to_disk is not None:
                    sat["save_to_disk"] = args.save_to_disk

                if args.disabled:
                    sat["disabled"] = True
                elif "disabled" in sat:
                    del sat['disabled']

        elif args.delete:
            section.clear()
    elif config_command == "norad":
        section = config["norad"]
        if args.urls is None:
            if args.delete:
                section.clear()
            elif args.refresh:
                db = OrbitDatabase(section)
                db.refresh_satellites(s['name'] for s in config["satellites"])
        elif args.urls is not None:
            if args.delete:
                for url in args.urls:
                    section.remove(url)
            elif args.refresh:
                db = OrbitDatabase(args.urls)
                db.refresh_urls()
            else:
                for url in args.urls:
                    if any(u == url for u in section):
                        continue
                    section.append(url)
                else:
                    db = OrbitDatabase(section)
                    print(db)
    elif config_command == "server":
        section = config["server"]
        update_config(section, args, ("id", "url", "secret"))
    is_changed = get_hash(config) != init_hash
    if is_changed:
        save_config(config)
        print("Configuration changed successfully")
        if args.replan:
            planner.execute(get_interval(planner_job))
    pprint(section)

else:
    parser.print_help()
