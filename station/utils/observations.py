
from pathlib import Path
import re
import json
from enum import Enum


class ObservationStatus(Enum):
    UNKOWN = 0  # Unable to determine status
    USELESS = 1  # Observation is useless (no useful data, just log)
    SUCCESS = 2  # Observation is successful, but was not uploaded
    UPLOADED = 3  # Was able to confirm that the observation was uploaded properly.
    UPLOAD_FAILED = 4  # An attempt to upload was attempted, but it failed.


def obs_del(obsdir: str, obsname: str):
    """ This physically deletes the observation from the local disk."""
    print(f"Deleting observation {obsname}...")
    obsdir = Path(obsdir)
    obsname = Path(obsname)
    fullpath = obsdir / obsname
    if not obsdir.is_dir():
        print(f"Observation directory {obsdir} does not exist!")
        return
    if not fullpath.is_dir():
        print(f"Observation {fullpath} does not exist!")
        return
    obsdir = obsdir / obsname
    for f in obsdir.glob('*'):
        f.unlink()
    obsdir.rmdir()


def obs_clean(obsdir: str, obsname: str):
    """Removes obsolete files from good, successfull operation."""
    obsdir = Path(obsdir + "/" + obsname)
    files = obsdir.glob('*.png')

    if list(files):
        # Ok, there are PNG files, we can get rid of the .raw and .wav files.
        wav_files = obsdir.glob('*.wav')
        for file in wav_files:
            print(f"PNG exists in this {str(obsdir)}, deleting {str(file)}")
            file.unlink()
        raw_files = obsdir.glob('*.raw')
        for file in raw_files:
            print(f"RAW exists in this {str(obsdir)}, deleting {str(file)}")
            file.unlink()


def obs_list(obsdir: str, clean: bool = False, del_uploaded: bool = False):
    """ Lists observations in the specified directory. If clean is True, it will also delete useless observations."""
    obs_stats(obsdir)

    dirs = sorted(d for d in Path(obsdir).glob('*') if d.is_dir())
    useless_cnt = 0
    uploaded_cnt = 0
    upload_failed_cnt = 0
    success_cnt = 0
    total_cnt = 0
    unknown_cnt = 0
    for d in dirs:
        status = obs_determine_status(obsdir, d.name)
        total_cnt += 1
        if status == ObservationStatus.USELESS:
            useless_cnt += 1
        elif status == ObservationStatus.UNKOWN:
            unknown_cnt += 1
        elif status == ObservationStatus.UPLOADED:
            uploaded_cnt += 1
        elif status == ObservationStatus.UPLOAD_FAILED:
            upload_failed_cnt += 1
        elif status == ObservationStatus.SUCCESS:
            success_cnt += 1
        obs_print_info(obsdir, d.name)
        if clean and status == ObservationStatus.USELESS:
            print(f"obsdir={obsdir} Deleting useless observation {d.name}...")
            obs_del(obsdir, d.name)
        if clean and status == ObservationStatus.SUCCESS:
            print(f"obsdir={obsdir} Cleaning useless files from observation {d.name}...")
            obs_clean(obsdir, d.name)
        if del_uploaded and status == ObservationStatus.UPLOADED:
            print(f"obsdir={obsdir} Deleting uploaded observation {d.name}...")
            obs_del(obsdir, d.name)

    print(f"SUMMARY: {total_cnt} observations, {uploaded_cnt} uploaded, {upload_failed_cnt} uploads failed, {success_cnt} successful, "
          f"{useless_cnt} useless, {unknown_cnt} unknown.")


def obs_print_info(obsdir: str, obsname: str):
    """ Prints information about observation in the specified directory."""
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

    files = [f for f in Path(obsdir + "/" + obsname).glob('*') if f.is_file()]

    # Test 1: If there's a upload status file, it's either failed or successful upload.
    for file in files:
        if file.name == "uploaded.json":
            with open(file) as json_data:
                content = json.load(json_data)
                if "status-code" in content and "response-text" in content:
                    if content["status-code"] in [200, 201, 202, 203, 204, 205]:
                        return ObservationStatus.UPLOADED
                    else:
                        return ObservationStatus.UPLOAD_FAILED
                else:
                    return ObservationStatus.UNKNOWN

    # Test 2: check if there is only a session.log file. If there is, there's no data, so it's a failed observation.
    # If there's only one file and it's just a log, it's a failed observation.
    if len(files) == 1 and files[0].name == "session.log":
        return ObservationStatus.USELESS

    # Test 3: Check if there's a signal.wav file that's too small. If there is, it's a failed observation.
    for file in files:
        if file.name == "signal.wav" and file.stat().st_size < 1024:
            return ObservationStatus.USELESS

    # Test 4: Check if there's a large png file. If there is, it's a successful observation.
    found = False
    for file in files:
        if str(file.name).endswith('png'):
            found = True
            break

    if found and file is not None:
        if file.stat().st_size < 1024:
            # Found a small png file {file}, assuming this is a failed observation.
            return ObservationStatus.USELESS
        else:
            # Found a large png file {file}, assuming this is a successful observation.
            return ObservationStatus.SUCCESS

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
