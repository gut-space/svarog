import datetime
import os
import sys
from typing import Iterable, List, Tuple
import uuid

from utils.models import SatelliteConfiguration
from recipes import recipes

if sys.version_info[0] == 3 and sys.version_info[1] >= 8:
    from typing import Literal
else:
    from typing_extensions import Literal

'''
The different satellites require different software and configuration.
This is a recipe-based solution. "Recipe" is a script which is responsible
for the signal reception and its decoding.

Each recipe takes three parameters:

* Working directory - it is writable, clean and temporary directory.
* Frequency - transmission frequency in MHz
* Duration - after this time script should stop SDR, in seconds

As output the script returns a dictionary where key is a category
and value is a path or paths to file(s). Currently the following categories
are supported:
- "signal" for initial audio file in WAV format
- "product" or "products" for decoded image

In the future additional categories will be added. Most likely there will be:
- "waterfall" presenting the frequency spectrum changing over time
- "telemetry" for any decoded telemetry data
- "logs" for detailed decoding notes

Other categories are likely to appear.

User should have a possibility to execute recipe in stand alone mode, i.e. without
the whole station code (without any need to initialize the station).

Recipe isn't responsible for clean up. The working directory should be deleted
after file processing. If some files should be kept, then they should be moved
to a safe place.

User has a possibility to select recipe by "recipe" parameter in satellite
config. Now it is optional and script try to deduce recipe based on satellite.
(For example if recipe isn't provided and name starts with NOAA then we use
recipe for NOAA).

All recipes must be located in directory with this file ("recipes") and have
"execute" method which accept all parameters.
'''

BASE_DIR = "/tmp/observations_tmp"
os.makedirs(BASE_DIR, exist_ok=True)

def get_recipe(sat: SatelliteConfiguration):
    '''
    Returns path to recipe file assigned with the specified satellite.
    If recipe doesn't exist throw LookupError.

    Function check "recipe" field in passed configuration for recipe.
    If it is empty then check built-in list with compatible recipes.
    '''
    recipe = None
    if "recipe" in sat:
        recipe = sat["recipe"]
    if recipe is None and sat["name"].startswith("NOAA"):
        recipe = "noaa-apt"
    if recipe is None:
        raise LookupError("Unknown recipe")

    return recipes[recipe]


def execute_recipe(sat: SatelliteConfiguration, los: datetime.datetime) -> Iterable[Tuple[Literal["signal", "product"], str]]:
    '''
    Execute recipe for specified satellite and return results.

    Return collection of tuples with category and path.
    If no recipe found then throw LookupError.

    We use "signal" category for raw, unprocessed received signal file
    and "product" for finished data (e. q. imagery) extracted from signal.
    You may get multiple files with the same category.

    Caller is responsible for cleaning up the results.
    You need delete or move returned files when you don't need them.
    '''
    recipe_function = get_recipe(sat)

    uid = uuid.uuid4()
    reception_directory = os.path.join(BASE_DIR, str(uid))
    os.makedirs(reception_directory, exist_ok=True)
    now = datetime.datetime.utcnow()
    record_interval = los - now

    output = recipe_function(reception_directory, sat["freq"], record_interval)
    return output


def get_recipe_names() -> List[str]:
    '''Returns all recipe names.'''
    return list(recipes.keys())
