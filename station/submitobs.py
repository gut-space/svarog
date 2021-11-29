#!/usr/bin/python
import datetime
import os
import requests
import sys
import logging

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
    notes: str
        Any text note
    rating: float?
        Rating of image
    """
    image_path: List[str]
    sat_name: str
    aos: datetime.datetime
    tca: datetime.datetime
    los: datetime.datetime
    notes: str
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
    known_types = {
        "csv": "text/plain",
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
        "notes": data.notes,
        "rating": data.rating
    }

    tle = get_tle(data.sat_name, data.aos)
    if tle is not None:
        form_data["tle"] = tle

    # Now process the files
    files = []
    for f in data.image_path:
        _, filename = os.path.split(data.image_path)

        file_obj = open(data.image_path, 'rb')
        body: Dict[str, Any] = {
            "file": file_obj
        }
        body.update(form_data)

    files = {
        "file": (
            filename,
            file_obj,
            "image/png",
            {}
        )
    }

    header_value = get_authorization_header_value(station_id,
        secret, body, datetime.datetime.utcnow())

    headers = {
        "Authorization": header_value
    }

    # Check if notes are a valid JSON
    logging.debug(f"Notes = {data.notes}")

    logging.info("Submitting observation, url=%s file=%s" % (url, filename))

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
        logging.debug("Response details: %s" % repr(resp))
        return f"Upload failed, status code {resp.status_code}"
    else:
        logging.info("Upload successful.")

    # All seems to be OK
    return None

if __name__ == '__main__':
    if len(sys.argv) < 4:
        print("Not enough parameters. At least 3 are needed: "
            "filename.png sat_name aos [tca] [los] [notes] [rating]")
        exit(1)

    filename=sys.argv[1]
    sat_name=sys.argv[2]
    aos=tca=los=from_iso_format(sys.argv[3])
    notes = ""
    rating = None

    if len(sys.argv) >= 5:
        tca = from_iso_format(sys.argv[4])

    if len(sys.argv) >= 6:
        los = from_iso_format(sys.argv[5])

    if len(sys.argv) >= 7:
        notes = sys.argv[6]

    if len(sys.argv) >= 8:
        rating = float(sys.argv[7])

    result = submit_observation(
        SubmitRequestData(filename, sat_name, aos, tca, los, notes, rating)
    )

    if result:
        logging.error(f"Upload result: {result}")

    # Empty string means success, everything else is a failure
    sys.exit(result is not None)
