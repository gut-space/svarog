
from metadata import Metadata
import unittest
import json
import os

TESTFILE = '/tmp/metadata.json'


class TestMetadata(unittest.TestCase):
    def setUp(self):
        return super().tearDown()

    def tearDown(self) -> None:
        try:
            os.remove(TESTFILE)
        except BaseException:
            pass
        return super().tearDown()

    def test_open_empty(self):
        """If the file is not there, the default values should be loaded."""
        m = Metadata(TESTFILE)

        self.assertEqual(m.get('antenna'), 'unknown')
        self.assertEqual(m.get('antenna-type'), 'unknown')
        self.assertEqual(m.get('receiver'), 'RTL-SDR v3')
        self.assertEqual(m.get('lna'), 'none')
        self.assertEqual(m.get('filter'), 'none')

    def test_add_key(self):
        """Check if it's possible to add and overwrite keys."""
        m = Metadata(TESTFILE)
        m.set('foo', 'bar')
        m.set('baz', 123)

        self.assertEqual(m.get('foo'), 'bar')
        self.assertEqual(m.get('baz'), 123)

        # Check that set overwrites, if the key already exists
        m.set('baz', 1)
        m.set('baz', None)
        m.set('baz', 123)
        self.assertEqual(m.get('baz'), 123)

    def test_del_key(self):
        """Check if deleting existing (and non-existing) keys is working ok."""
        m = Metadata(TESTFILE)
        m.set('foo', 'bar')
        self.assertEqual(m.get('antenna'), 'unknown')  # default entry
        self.assertEqual(m.get('foo'), 'bar')  # user entry

        m.delete('foo')
        m.delete('antenna')

        self.assertEqual(m.get('foo'), '')
        self.assertEqual(m.get('antenna'), '')

        # Check that deleting non-existing key is OK
        m.delete('foo')
        m.delete('foo')
        m.delete('foo')

    def test_file(self):
        """Tests that the file can be written and that the written context is correct."""
        try:
            os.remove(TESTFILE)
        except BaseException:
            pass
        m = Metadata(TESTFILE)
        m.writeFile()

        with open(TESTFILE, 'r') as myfile:
            data = myfile.read()

        j = json.loads(data)
        self.assertIsNotNone(j)
        self.assertIsNotNone(j['antenna'])
        self.assertIsNotNone(j['antenna-type'])
        self.assertIsNotNone(j['receiver'])
        self.assertIsNotNone(j['lna'])
        self.assertIsNotNone(j['filter'])

    def test_string(self):
        """Check if the returned string looks reasonable."""
        m = Metadata(TESTFILE)
        m.clear()
        m.set('foo', 'bar')
        m.set('baz', 123)

        exp_txt = """{
    "foo": "bar",
    "baz": 123
}"""

        self.assertEqual(m.getString(), exp_txt)
