#!/usr/bin/python
import datetime
import os
import requests
import sys
import logging
import json

# This is awfully early. However, some of the later imports seem to define the basic config on its own.
if __name__ == '__main__':
    logging.basicConfig(stream=sys.stdout, format="%(levelname)s %(asctime)s - %(message)s", level=logging.DEBUG)

from typing import Any, Dict, List, Optional
from dataclasses import dataclass

from utils.configuration import open_config
from utils.dates import from_iso_format
from hmac_token import get_authorization_header_value
from orbitdb import OrbitDatabase

config = open_config()
section = config["server"]
station_id = str(section["id"])
secret = bytearray.fromhex(section["secret"])
url = section["url"]

@dataclass
class SubmitRequestData:
    """
    Request data for send to server.

    Parameters
    ==========
    image_path: str
        List of files to upload
    sat_name: str
        Satellite name compatible with NORAD format
    aos: datetime.datetime
        Acquisition of Signal (or Satellite)
    tca: datetime.datetime
        Time of Closest Approach
    los: datetime.datetime
        Loss of Signal (or Satellite)
    config: dict
        meta-data information in JSON format
    rating: float?
        Rating of image
    """
    image_path: List[str]
    sat_name: str
    aos: datetime.datetime
    tca: datetime.datetime
    los: datetime.datetime
    config: Optional[str]
    rating: Optional[float]


def get_tle(sat_name: str, date: datetime.datetime) -> Optional[List[str]]:
    try:
        db = OrbitDatabase()
        return db.get_tle(sat_name, date)
    except:
        return None

def get_mime_type(filename: str) -> str:
    """
    Returns the MIME type for known and unknown file formats.

    Parameters
    ==========
    filename: str
        name of the file to be sent
    return:
        MIME type as str
    """

    # This is a list of file types that possibly could make sense in the Svarog project.
    # When adding new types, don't forget to update ALLOWED_FILE_TYPES in
    # server/app/controllers/receive.py
    known_types = {
        "csv": "text/plain",
        "gif": "image/gif",
        "jpeg": "image/jpeg",
        "jpg": "image/jpeg",
        "json": "application/json",
        "log": "text/plain",
        "png": "image/png",
        "svg": "image/svg+xml",
        "txt": "text/plain",
        "wav": "audio/wav"
    }

    txt = filename.lower()
    offset = txt.rfind('.')
    ext = txt[offset+1:] if offset != -1 else ""
    return known_types[ext] if ext in known_types else "application/octet-stream"

def submit_observation(data: SubmitRequestData):
    '''
    Attempts to submit the observation to the content server.

    Parameters
    ==========
    data: SubmitRequestData
        Observation to be sent (image, sat_name, etc.)
    return:
        None if successful or description of what went wrong
    '''
    form_data = {
        "aos": data.aos.isoformat(),
        "tca": data.tca.isoformat(),
        "los": data.los.isoformat(),
        "sat": data.sat_name,
        "rating": data.rating,
        "config": data.config
    }

    tle = get_tle(data.sat_name, data.aos)
    if tle is not None:
        form_data["tle"] = tle

    # Now process the files
    files = {}
    cnt = 0
    body: Dict[str, Any] = {
    }
    for f in data.image_path:
        _, filename = os.path.split(f)

        # If there's only one file, it will use "file" key. The second file will be "file1",
        # third "file2" etc.
        file_key = "file" if cnt==0 else f"file{cnt}"

        file_obj = open(f, 'rb')
        body[file_key] = file_obj

        files[file_key] = (filename, file_obj, get_mime_type(filename), {})
        cnt = cnt + 1

    body.update(form_data)

    header_value = get_authorization_header_value(station_id,
        secret, body, datetime.datetime.utcnow())

    headers = {
        "Authorization": header_value
    }

    # Check if notes are a valid JSON
    logging.debug(f"Meta-data = {data.config}")

    logging.info(f"Submitting observation, url={url}, file(s)={data.image_path}")

    try:
        resp = requests.post(url, form_data, headers=headers, files=files)
    except requests.exceptions.ConnectionError:
        return f"Unable to connect to {url}, connection refused"
    if (resp.status_code >= 400):
        logging.warning("Response status: %d" % resp.status_code)
    else:
        logging.info("Response status: %d" % resp.status_code)

    # Logging extra details in case of failed submission.
    if (resp.status_code != 204):
        # On info, just log the field names in what we sent. On debug, log also the content and the whole response.
        logging.info("Submission details: headers: %s, form: %s" % (",".join(headers.keys()), ",".join(form_data.keys())) )
        logging.debug("headers=%s" % headers)
        logging.debug("form=%s" % form_data)
        logging.debug("Response details: %s" % resp.text)
        return f"Upload failed, status code {resp.status_code}"
    else:
        logging.info("Upload successful.")

    # All seems to be OK
    return None

if __name__ == '__main__':
    if len(sys.argv) < 4:
        print("Not enough parameters. At least 3 are needed: "
            "filename sat_name aos [tca] [los] [notes] [rating]")
        print("filename can be a single file or coma separated list (no spaces)")
        exit(1)

    filename=sys.argv[1]
    sat_name=sys.argv[2]
    aos=tca=los=from_iso_format(sys.argv[3])
    cfg = "{}"
    rating = None

    if len(sys.argv) >= 5:
        tca = from_iso_format(sys.argv[4])

    if len(sys.argv) >= 6:
        los = from_iso_format(sys.argv[5])

    if len(sys.argv) >= 7:
        try:
            # Just check if ths input is a valid JSON (but use it as text anyway)
            json.loads(sys.argv[6])
            cfg = sys.argv[6]
        except:
            logging.error(f"ERROR: The meta-data (config) was specified: {sys.argv[6]}, but it's not a valid JSON")

    if len(sys.argv) >= 8:
        rating = float(sys.argv[7])

    # Files can be coma separated (or it could be just a single file)
    filename=filename.split(",")

    result = submit_observation(
        SubmitRequestData(filename, sat_name, aos, tca, los, cfg, rating)
    )

    if result:
        logging.error(f"Upload result: {result}")

    # Empty string means success, everything else is a failure
    sys.exit(result is not None)
