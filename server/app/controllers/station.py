from app.repository import Repository
from flask import render_template, abort
from app import app, utils

@app.route('/station/<station_id>')
def station(station_id = None):

    repository = Repository()
    station = repository.read_station(station_id)
    if station is None:
        abort(404, "Station not found")
    statistics = repository.read_station_statistics(station["station_id"])

    photos = repository.read_station_photos(station_id)

    owners = repository.station_owners(station_id)

    # Now get 3 latest observations from this station
    filters = {
        "station_id": station['station_id']
    }
    latest_obs = repository.read_observations(filters=filters, limit=3, offset=0)

    # Get the 3 observations with the best rating
    best_obs = repository.read_observations(filters=filters, limit=3, offset=0, order="r.rating DESC", expr="r.rating is not NULL")

    x = {}
    x['station_id'] = station['station_id']
    x['name'] = station['name']
    x['coords'] = utils.coords(station['lon'], station['lat'])
    x['descr'] = station['descr']

    x['config'] = station['config']
    x['registered'] = station['registered']
    x['lastobs'] = statistics["last_los"]
    x['firstobs'] = statistics["first_aos"]
    x['cnt'] = statistics["observation_count"]

    files = []
    for photo in photos:
        y = {}
        y['filename'] = photo['filename']
        y['descr'] = photo['descr']
        y['sort'] = photo['sort']
        files.append(y)

    return render_template('station.html', station = x, files = files, owners = owners, latest_obs=latest_obs, best_obs=best_obs)
