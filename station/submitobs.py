#!/usr/bin/python
import datetime
import os
import requests
import sys
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
        Path to PNG image
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
    image_path: str
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

def submit_observation(data: SubmitRequestData):
    '''
    Submit observation to content server.
    '''
    _, filename = os.path.split(data.image_path)

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

    file_obj = open(data.image_path, 'rb') 
    body: Dict[str, Any] = {
        "file": file_obj
    }
    body.update(form_data)

    header_value = get_authorization_header_value(station_id,
        secret, body, datetime.datetime.utcnow())

    headers = {
        "Authorization": header_value
    }

    files = {
        "file": (
            filename,
            file_obj,
            "image/png",
            {}
        )
    }

    requests.post(url, form_data, headers=headers, files=files)

if __name__ == '__main__':
    if len(sys.argv) < 4:
        print("Not enough parameters. At least 3 are needed: "
            "filename.png sat_name aos")
        exit(1)

    filename=sys.argv[1]
    sat_name=sys.argv[2]
    aos=tca=los=from_iso_format(sys.argv[3])
    notes="..."

    if len(sys.argv) >= 5:
        TCA = sys.argv[4]

    if len(sys.argv) >= 6:
        LOS = sys.argv[5]

    if len(sys.argv) >= 7:
        NOTES = sys.argv[6]

    submit_observation(
        SubmitRequestData(filename, sat_name, aos, tca, los, notes, None)
    )
