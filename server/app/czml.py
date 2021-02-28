
from poliastro.czml.extract_czml import CZMLExtractor
from app.repository import ObservationId, Repository, Observation
from tletools import TLE
from astropy.time import Time
from astropy import units as u
from pprint import pprint

def get_czml(id):

    # First we need to get the observation and sat data from a database.
    repository = Repository()

    obs = repository.read_observation(id)
    if obs is None:
        return '{ "error": "Unable to find observation %s" }' % id

    sat = repository.read_satellite(obs['sat_id'])
    if sat is None:
        return '{ "error": "Unable to details for sat with norad id %s" }' % obs['sat_id']

    station = repository.read_station(obs['station_id'])

    print("#### OBS")
    pprint(obs)
    print("#### SAT")
    pprint(sat)
    print("#### station")
    pprint(station)

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
    extractor.add_orbit(orb, id_name=name, path_width=2, label_text=str(id), label_fill_color=[125, 80, 120, 255])

    if station is not None:
        extractor.add_ground_station([ station['lon'] * u.degree, station['lat'] * u.degree ],
            label_text = station['name'],
            id_description= station['descr'])

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
