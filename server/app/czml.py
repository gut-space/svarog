
from poliastro.czml.extract_czml import CZMLExtractor
from poliastro.twobody import Orbit
from app.repository import ObservationId, Repository, Observation, Satellite, Station
from tletools import TLE
from astropy.time import Time
from astropy import units as u
from pprint import pprint
from app.utils import coords

def get_obs_czml(id):
    """Generates CZML file that describe the observation, specified by id. ID must be an integer.
       This returns a CZML file that contains at least 4 CZML packets: document description,
       custom parameters describing Earth spheroid, satellite pass, ground station."""

    try:
        id = int(id)
    except:
        return '{ "error": "Invalid observation \'%s\', expected number" }' % id

    # First we need to get the observation and sat data from a database.
    repository = Repository()

    obs = repository.read_observation(id)
    if obs is None:
        return '{ "error": "Unable to find observation %s" }' % id

    sat = repository.read_satellite(obs['sat_id'])
    if sat is None:
        return '{ "error": "Unable to details for sat with norad id %s" }' % obs['sat_id']

    station = repository.read_station(obs['station_id'])

    # Now make sure the observation has its TLE data recorded.
    if obs['tle'] is None:
        # We don't have TLE data. Oh well. We'll bail out for now. We can't simply get the
        # current TLE data, as TLE can only be used to propagate after its epoch.
        return '{ "error": "TLE data missing for observation %s" }' % obs['obs_id']

    # ok, all is good. Let's generate poliastro orbit based on TLE
    name = "%s (norad id %d)" % (sat['sat_name'], obs['sat_id'])
    tle = TLE.from_lines(line1=obs['tle'][0], line2=obs['tle'][1], name=name)
    orb = tle.to_orbit()

    # Now convert start and end epoch (timestamp, effectively) to astropy.Time, which is used
    # by poliastro.
    start_epoch = Time(obs['aos'])
    end_epoch = Time(obs['los'])

    # Ok, we got all the data. It's now time to generate CZML file.
    num_samples = 80
    extractor = CZMLExtractor(start_epoch, end_epoch,num_samples)

    descr = get_obs_descr(start_epoch, end_epoch, orb, obs, sat)

    extractor.add_orbit(orb, id_name=name, id_description=descr, path_width=2, label_text=str(id), label_fill_color=[125, 80, 120, 255])

    if station is not None:
        extractor.add_ground_station([ station['lat'] * u.degree, station['lon'] * u.degree ],
            label_text = station['name'],
            id_description= get_station_descr(station))

    # I'm sure there's much easier way to do the conversion, but all the examples
    # for czml3 only show how to convert a single packet. For pass visualization, we will
    # have several packets. First setting the timeframe, second will be the sat, third
    # will be the ground track. There may be more. Anyway, this code is basic, but seems
    # to be working well.
    txt = "[\n"
    first = True
    for pkt in extractor.packets:
        if not first:
            txt += ",\n"
        txt += str(pkt)
        first = False


    return txt + "]\n"

def get_obs_descr(start_epoch: Time, end_epoch: Time, orb: Orbit, obs: Observation, sat: Satellite) -> str:
    """Generates satellite pass textual description."""

    name = sat['sat_name']
    norad_id = sat['sat_id']
    tle = obs['tle']

    RE = orb.attractor.R

    descr = "<p>NORAD ID = <b>%d</b></p>\n" % norad_id
    descr += "<p>Transmission parameters<br/>\n"
    descr += "Observation number = %s<br/>" % obs['obs_id']
    descr += "AOS (Acquisition of signal) = %s<br/>\n" % start_epoch
    descr += "LOS (Loss of signal) = %s</p>\n" % end_epoch


    descr = descr + "<p>Orbit parameters<br/>\n{r_p:.1f} x {r_a:.1f} ({per_abs:.1f} x {apo_abs:.1f}) <br/>\n".format(r_p = orb.r_p, r_a=orb.r_a, per_abs=orb.r_p - RE, apo_abs=orb.r_a - RE)
    descr = descr + "Perigee = <b>{per:.1f}</b> (altitude {alt:.1f})<br/>".format(per = orb.r_p, alt = orb.r_p - RE)
    descr = descr + "Apogee = <b>{apo:.1f}</b> (altitude {alt:.1f})<br/>".format(apo = orb.r_a, alt = orb.r_a - RE)
    descr = descr + "Major semi-axis <i>a</i> = <b>%4.2f %s</b><br/>" % (orb.a.value, orb.a.unit)
    descr = descr + "Eccentricity <i>e</i> = <b>%s</b><br/>" % orb.ecc
    descr = descr + "Inclination <i>i</i> = <b>%4.2f %s</b><br/>" % (orb.inc.value, orb.inc.unit)
    descr = descr + "Right Ascension of the Ascending Node <i>raan</i> = <b>%4.2f %s</b><br/>" % (orb.raan.value, orb.raan.unit)
    descr = descr + "Argument of perigee <i>argp</i> = <b>%4.2f %s</b><br/>" % (orb.argp.value, orb.argp.unit)
    descr = descr + "Period = <b>{period:.1f}</b><br/>".format(period = orb.period)
    descr = descr + "Epoch = %s<br/></p>" % str(orb.epoch)[:16]

    return descr

def get_station_descr(station: Station) -> str:
    """Generates a description of the ground station"""
    descr = "<p><b>Description:</b><br/>" + station['descr'] + "</p>\n"

    descr += "<p><b>Coordinates</b>: " + coords(station['lon'], station['lat']) + "</p>\n"
    descr += "<p><b>Configuration</b>:<br/>" + station['config'] + "</p>"

    return descr