import datetime
import os
import os.path
import shutil
import unittest
import logging
import json
from logging import FileHandler
from pprint import pprint

import testing.postgresql

from app import app
from app.hmac_token import get_authorization_header_value
from app.repository import Repository
from tests.utils import standard_seed_db, check_output

Postgresql: testing.postgresql.PostgresqlFactory

def setUpModule():
    global Postgresql
    Postgresql = testing.postgresql.PostgresqlFactory(cache_initialized_db=True,
                                                on_initialized=standard_seed_db)

def tearDownModule():
    # clear cached database at end of tests
    Postgresql.clear_cache()

IMAGE_ROOT = "tests/images"
LOG_FILE = "test.log"

# Setting the secret is necessary for storing login details is a session.
app.config["SECRET_KEY"] = "test secret"

class CzmlTests(unittest.TestCase):

    def setUp(self):

        self.postgres = Postgresql()
        app.config['TESTING'] = True
        app.config['WTF_CSRF_ENABLED'] = False
        app.config['DEBUG'] = False
        app.config["database"] = self.postgres.dsn()
        app.config["storage"] = {}
        app.config["storage"]["image_root"] = IMAGE_ROOT
        os.makedirs(os.path.join(IMAGE_ROOT, "thumbs"), exist_ok=True)
        os.makedirs(os.path.join(IMAGE_ROOT, "charts"), exist_ok=True)

        app.config["view"] = {}
        app.config["view"]["items_per_page"] = 100

        self.app = app.test_client()

        # This is a test. Log EVERYTHING.
        logHandler = FileHandler(LOG_FILE)
        logHandler.setLevel(logging.DEBUG)
        app.logger.setLevel(logging.DEBUG)
        app.logger.addHandler(logHandler)

    def tearDown(self):
        self.postgres.stop()
        shutil.rmtree(IMAGE_ROOT, ignore_errors=True)
        os.remove(LOG_FILE)

    def test_czml_valid(self):
        """This tests a valid observation. Checks if observation 1276 can be returned as CZML
           and if its content looks reasonable."""

        response = self.app.get('/czml/1276', follow_redirects=True)

        # Check if it looks ok and has JSON format
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content_type, 'application/json')
        czml = json.loads(response.data)

        # Now perform some basic CZML tests. Make sure it consists of at least 4 packets.
        self.assertGreaterEqual(len(czml), 4)

        doc_pkt = czml[0] # document-packet (this describes basic things, such as time boundaries and time zoom)
        prop_pkt = czml[1] # custom properties (this defines Earth, not sure why it's needed, but it's there)
        sat_pkt = czml[2] # the satellite data
        gs_pkt = czml[3] # ground station

        # Checks for document packet. Not much there to check.
        self.assertEqual(doc_pkt['id'], "document")
        self.assertEqual(doc_pkt['name'], "document_packet")

        # Checks for custom properties.
        self.assertEqual(prop_pkt['id'], "custom_properties")

        # Checks for the satellite packet.
        self.assertEqual(sat_pkt['id'], 0)
        self.assertEqual(sat_pkt['name'], "NOAA 18 (norad id 28654)")
        # TODO: we could check tons of extra data here, but for now let's hope the values returnes are correct.

        # Check for the ground station packet. GS0 is a serial number that poliastro assigns to specific ground
        # stations. We also want to make sure that the description contains some reference to the station name (TKiS-1)
        self.assertTrue(gs_pkt['id'] == "GS0")
        self.assertTrue(gs_pkt['description'].find("TKiS-1") != -1)

    def test_czml_invalid_obs(self):
        """This tests error handling:
           - invalid observation number
           - missing observation number"""

        # There's no observation 12345.
        response = self.app.get('/czml/12345', follow_redirects=True)
        self.check_error_response(response, 'Unable to find observation 12345')

        # This observation number is clearly invalid.
        response = self.app.get('/czml/1111one', follow_redirects=True)
        self.check_error_response(response, 'Invalid observation \'1111one\', expected number')

    def check_error_response(self, resp, exp_error):
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.content_type, 'application/json')
        czml = json.loads(resp.data)
        self.assertTrue(czml['error'])
        self.assertEqual(czml['error'], exp_error)


if __name__ == "__main__":
    unittest.main()
