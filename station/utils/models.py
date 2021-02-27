import sys
from typing import List, Optional, Tuple

from utils.functional import first

if sys.version_info >= (3, 8):
    from typing import TypedDict, Literal
else:
    from typing_extensions import TypedDict, Literal


SATELLITE_SAVE_MODE = Literal["SIGNAL", "PRODUCT", "ALL", "INHERIT", "NONE"]
GLOBAL_SAVE_MODE = Literal["SIGNAL", "PRODUCT", "ALL", "NONE"]
STRATEGY = Literal["max-elevation", "aos"]


class LocationConfiguration(TypedDict):
    elevation: float
    latitude: float
    longitude: float
    name: str


class SatelliteConfiguration(TypedDict, total=False):
    freq: str
    name: str
    submit: Optional[bool]
    save_to_disk: Optional[SATELLITE_SAVE_MODE]
    aos_at: Optional[int]
    max_elevation_greater_than: Optional[int]
    disabled: Optional[bool]
    recipe: Optional[str]
    rate: Optional[str]


class ServerConfiguration(TypedDict):
    id: str
    secret: str
    url: str


class Configuration(TypedDict):
    aos_at: int
    location: LocationConfiguration
    max_elevation_greater_than: int
    norad: List[str]
    satellites: List[SatelliteConfiguration]
    save_to_disk: Optional[GLOBAL_SAVE_MODE]
    server: ServerConfiguration
    strategy: Optional[STRATEGY]
    submit: Optional[bool]
    obsdir: Optional[str]


def get_location(config: Configuration) -> Tuple[str, float, float, float]:
    location = (config["location"]["name"],
            config["location"]["latitude"], config["location"]["longitude"],
            config["location"]["elevation"])
    return location


def set_satellite_defaults(config: Configuration, satellite: SatelliteConfiguration):
    '''
    If satellite structure doesn't contains optional values
    then they will be set using inherited, global configuration.
    '''
    if 'submit' not in satellite:
        global_submit = config.get('submit', None)
        if global_submit is None:
            global_submit = True
        satellite['submit'] = global_submit
    if 'save_to_disk' not in satellite or satellite['save_to_disk'] == 'INHERIT':
        global_ = config.get('save_to_disk')
        if global_ is None:
            global_ = "NONE"
        satellite["save_to_disk"] = global_
    if 'aos_at' not in satellite:
        global_ = config.get('aos_at')
        if global_ is None:
            global_ = 0
        satellite['aos_at'] = global_
    if 'max_elevation_greater_than' not in satellite:
        global_ = config.get('max_elevation_greater_than')
        if global_ is None:
            global_ = 0
        satellite['max_elevation_greater_than'] = global_
    if 'disabled' not in satellite:
        satellite['disabled'] = False


def get_satellite(config: Configuration, sat: str) -> SatelliteConfiguration:
    '''
    Search for satellite configuration. Throw LookupError if not found.
    If found then omitted optional fields will be set using inherited, global
    configuration.
    '''
    satellites = config['satellites']
    satellite = first(satellites, lambda s: s['name'] == sat)
    if satellite is None:
        raise LookupError("Satellite %s not found" % (sat,))
    set_satellite_defaults(config, satellite)
    return satellite
