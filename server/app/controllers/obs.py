from flask import abort, render_template

from app import app
from app.repository import ObservationId, Repository, Observation
from app.pagination import use_pagination
from math import floor
from app.utils import strfdelta
from flask_login import current_user

from tletools import TLE
from astropy import units as u
import os


@app.route('/obs/<obs_id>')
@use_pagination(5)
def obs(obs_id: ObservationId = None, limit_and_offset=None):
    if obs_id is None:
        abort(300, description="ID is required")
        return

    repository = Repository()
    with repository.transaction():
        observation = repository.read_observation(obs_id)

        orbit = None

        if observation is None:
            abort(404, "Observation not found")

        files = repository.read_observation_files(observation["obs_id"],
                                                  **limit_and_offset)
        files_count = repository.count_observation_files(obs_id)
        satellite = repository.read_satellite(observation["sat_id"])

        orbit = observation
        if observation['tle'] is not None:
            # observation['tle'] is always an array of exactly 2 strings.
            orbit = parse_tle(*observation['tle'], satellite["sat_name"])

        station = repository.read_station(observation["station_id"])

    # Now tweak some observation parameters to make them more human readable
    observation = human_readable_obs(observation)

    # Now determine if there is a logged user and if there is, if this user is the owner of this
    # station. If he is, we should show the admin panel.
    user_id = 0
    owner = False
    if current_user.is_authenticated:
        user_id = current_user.get_id()

        # Check if the current user is the owner of the station.
        station_id = station['station_id']

        owner = repository.is_station_owner(user_id, station_id)

    return 'obs.html', dict(obs=observation, files=files,
                            sat_name=satellite["sat_name"], item_count=files_count, orbit=orbit, station=station, is_owner=owner)


def parse_tle(tle1: str, tle2: str, name: str) -> dict:
    """ Parses orbital data in TLE format and returns a dictionary with printable orbital elements
        and other parameters."""

    # First, parse the TLE lines. We don't care about the name.
    t = TLE.from_lines(line1=tle1, line2=tle2, name=name)

    # Now convert it to poliastro orbit. All the data is there, but we want to
    # make it easier to read, format it nicely and do some basic calculations.
    # Hence the orb dictionary.
    o = t.to_orbit()

    RE = o.attractor.R  # Earth radius
    r_a = o.r_a - RE  # Calculate apogee and perigee as altitude above Earth surface,
    r_p = o.r_p - RE  # rather than as distance from barycenter.

    m = floor(o.period.to(u.s).value / 60)
    s = (o.period.to(u.s) - m * 60 * u.s).value

    # Now make the parameters easier to read (cut unnecessary digits after comma, show altitude, etc)
    orb = {}
    orb["overview"] = repr(o)
    orb["inc"] = "%4.1f %s" % (o.inc.value, o.inc.unit)
    orb["a"] = o.a
    orb["ecc"] = o.ecc
    orb["r_a"] = "%4.1f %s (%4.1f %s above surface)" % (o.r_a.value, o.r_a.unit, r_a.value, r_a.unit)
    orb["r_p"] = "%4.1f %s (%4.1f %s above surface)" % (o.r_p.value, o.r_p.unit, r_p.value, r_p.unit)
    orb["raan"] = "%4.1f %s" % (o.raan.value, o.raan.unit)
    orb["period"] = "%4.0f %s (%dm %ds)" % (o.period.value, o.period.unit, m, s)

    # Let's convert epoch to something more pleasantly readable.
    orb["epoch"] = o.epoch.strftime("%Y-%m-%d %H:%M:%S") + " UTC"

    return orb


def human_readable_obs(obs: Observation) -> Observation:
    """Gets an observation and formats some of its parameters to make it more human readable.
       Returns an observation."""

    aos_los_duration = obs["los"] - obs["aos"]
    tca_correction = ""

    if obs["aos"] == obs["tca"]:
        obs["tca"] = obs["aos"] + aos_los_duration / 2
        tca_correction = " (corrected, the original observation record incorrectly says TCA = AOS)"

    aos_tca_duration = obs["tca"] - obs["aos"]

    obs.aos = obs["aos"].strftime("%Y-%m-%d %H:%M:%S")
    obs.tca = obs["tca"].strftime("%Y-%m-%d %H:%M:%S") + ", " + strfdelta(aos_tca_duration, fmt="{M:02}m {S:02}s since AOS") + tca_correction
    obs.los = obs["los"].strftime("%Y-%m-%d %H:%M:%S") + ", " + strfdelta(aos_los_duration, fmt="{M:02}m {S:02}s since AOS")
    return obs


@app.route('/obs/delete/<obs_id>', methods=["GET", "POST"])
def obs_delete(obs_id: ObservationId = None):

    # First check if such an observation even exists.
    repository = Repository()
    observation = repository.read_observation(obs_id)
    if observation is None:
        return render_template('obs_delete.html', status=["There is no observation %s" % obs_id], obs_id=obs_id)

    # Second, check if the guy is logged in.
    if not current_user.is_authenticated:
        return render_template('obs_delete.html', status=["You are not logged in, you can't delete anything."], obs_id=obs_id)

    # Ok, at least this guy is logged in. Let's check who he is.
    user_id = current_user.get_id()

    # Check if the current user is the owner of the station.
    station = repository.read_station(observation["station_id"])
    station_id = station['station_id']

    owner = repository.is_station_owner(user_id, station_id)

    if not owner:
        return render_template('obs_delete.html', status=["You are not the owner of station %s, you can't delete observation %s."
                                                          % (station.name, obs_id)], obs_id=obs_id)

    # If you got that far, this means the guy is logged in, he's the owner and is deleting his own observation.

    status = obs_delete_db_and_disk(repository, obs_id)
    return render_template('obs_delete.html', status=status, obs_id=obs_id)


def obs_delete_db_and_disk(repository: Repository, obs_id: ObservationId):

    app.logger.info("About to delete observation %s and all its files" % obs_id)

    # Step 1: Create a list of files to be deleted. There may be several products.
    products = repository.read_observation_files(obs_id)
    obs = repository.read_observation(obs_id)
    files = [[f['filename'], "product"] for f in products]

    # Step 2: thumbnail is stored with the observation. There's at most one thumbnail.
    files.append([os.path.join("thumbs", obs['thumbnail']), "thumbnail"])

    # Step 3: And there are two charts: alt-az pass chart and polar pass chart.
    files.append([os.path.join("charts", "by_time-%s.png" % obs_id), "pass chart"])
    files.append([os.path.join("charts", "polar-%s.png" % obs_id), "polar pass chart"])

    # All those files are stored in this dir
    root = app.config["storage"]['image_root']

    status = []
    for f in files:
        path = os.path.join(root, f[0])
        app.logger.info("Trying to delete [%s]" % path)
        try:
            os.remove(path)
            status.append("Deleted %s file %s." % (f[1], f[0]))
        except Exception as ex:
            status.append("Failed to delete %s file: %s, reason: %s" % (f[1], path, repr(ex)))

    # Step 4: delete entries in the db
    repository.delete_observation(obs_id)
    status.append("DB removal complete.")

    return status
