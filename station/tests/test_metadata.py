
from metadata import Metadata
import pytest
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
        except:
            pass
        return super().tearDown()

    def test_open_empty(self):
        m = Metadata(TESTFILE)

        self.assertEqual(m.get('antenna'), 'unknown')
        self.assertEqual(m.get('antenna-type'), 'unknown')
        self.assertEqual(m.get('receiver'), 'RTL-SDR v3')
        self.assertEqual(m.get('lna'), 'none')
        self.assertEqual(m.get('filter'), 'none')

    def test_add_key(self):
        m = Metadata(TESTFILE)
        m.add('foo', 'bar')
        m.add('baz', 123)

        self.assertEqual(m.get('foo'), 'bar')
        self.assertEqual(m.get('baz'), 123)

    def test_del_key(self):
        m = Metadata(TESTFILE)
        m.add('foo', 'bar')
        self.assertEqual(m.get('antenna'), 'unknown') # default entry
        self.assertEqual(m.get('foo'), 'bar')  # user entry

        m.delete('foo')
        m.delete('antenna')

        self.assertEqual(m.get('foo'), '')
        self.assertEqual(m.get('antenna'), '')

    def test_file(self):
        """Tests that the file can be written with proper content."""
        try:
            os.remove(TESTFILE)
        except:
            pass
        m = Metadata(TESTFILE)
        m.writeFile()

        with open(TESTFILE, 'r') as myfile:
            data=myfile.read()

        j = json.loads(data)
        self.assertIsNotNone(j)
        self.assertIsNotNone(j['antenna'])
        self.assertIsNotNone(j['antenna-type'])
        self.assertIsNotNone(j['receiver'])
        self.assertIsNotNone(j['lna'])
        self.assertIsNotNone(j['filter'])
