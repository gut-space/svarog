from flask import abort

from app import app
from app.repository import ObservationId, Repository
from app.pagination import use_pagination

from tletools import TLE

@app.route('/obs/<obs_id>')
@use_pagination(5)
def obs(obs_id: ObservationId = None, limit_and_offset = None):
    if obs_id is None:
        abort(300, description="ID is required")
        return

    repository = Repository()
    with repository.transaction():
        observation = repository.read_observation(obs_id)

        orbit = None

        if observation is None:
            abort(404, "Observation not found")

        orbit = observation
        if observation['tle'] is not None:
            orbit = parse_tle(observation['tle'][0], observation['tle'][1])

        files = repository.read_observation_files(observation["obs_id"],
            **limit_and_offset)
        files_count = repository.count_observation_files(obs_id)
        satellite = repository.read_satellite(observation["sat_id"])

    return 'obs.html', dict(obs = observation, files=files,
        sat_name=satellite["sat_name"], item_count=files_count, orbit=orbit)

def parse_tle(tle1, tle2):
    t = TLE.from_lines(line1=tle1, line2=tle2, name="whatevah")
    return t.to_orbit()