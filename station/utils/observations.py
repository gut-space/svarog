
from shutil import disk_usage
from pathlib import Path
import re
from enum import Enum

class ObservationStatus(Enum):
    USELESS = 0 # Observation is useless (no useful data, just log)
    UNKOWN = 1 # Unable to determine status
    SUCCESS = 2 # Observation is successful, but was not uploaded
    SUBMITTED = 3 # Was able to confirm that the observation was uploaded properly.

def obs_list(obsdir: str):
    obs_stats(obsdir)

    dirs = sorted([d for d in Path(obsdir).glob('*') if d.is_dir()])
    useless_cnt = 0
    total_cnt = 0
    unknown_cnt = 0
    for d in dirs:
        status = obs_determine_status(obsdir, d.name)
        total_cnt += 1
        if status == ObservationStatus.USELESS:
            useless_cnt += 1
        elif status == ObservationStatus.UNKOWN:
            unknown_cnt += 1
        obs_print_info(obsdir, d.name)

    print(f"SUMMARY: {total_cnt} observations, {useless_cnt} useless, {unknown_cnt} unknown, {total_cnt - useless_cnt - unknown_cnt} useful.")

def obs_print_info(obsdir: str, obsname: str):
    du = sum(file.stat().st_size for file in Path(obsdir + "/" + obsname).rglob('*'))

    regex = re.compile(r"([0-9]{4}-[0-9]{2}-[0-9]{2}-[0-9]{4})-([a-zA-Z-0-9_]+)")
    match = regex.match(obsname)
    date = ""
    satname = ""
    if match:
        date = match.group(1)
        satname = match.group(2)

    status = obs_determine_status(obsdir, obsname)
    print(f"Observation {obsname} (date: {date}, sat: {satname}) uses {sizeof_fmt(du)} of disk space, status: {status}.")

def obs_determine_status(obsdir: str, obsname: str) -> ObservationStatus:

    # Test 1: check if there is only a session.log file. If there is, there's no data, so it's a failed observation.
    files = [f for f in Path(obsdir + "/" + obsname).glob('*') if f.is_file()]
    if len(files) == 1 and files[0].name == "session.log":
        return ObservationStatus.USELESS
    if len(files) == 1 and files[0].name == "signal.wav" and files[0].stat().st_size < 1024:
        return ObservationStatus.USELESS

    return ObservationStatus.UNKOWN

def sizeof_fmt(num, suffix="B"):
    for unit in ("", "K", "M", "G", "Ti", "Pi", "Ei", "Zi"):
        if abs(num) < 1000.0:
            return f"{num:3.1f}{unit}{suffix}"
        num /= 1000.0
    return f"{num:.1f}Yi{suffix}"

def obs_stats(obsdir: str):
    du = sum(file.stat().st_size for file in Path(obsdir).rglob('*'))
    print(f"Observation directory: {obsdir} uses {sizeof_fmt(du)} of disk space.")