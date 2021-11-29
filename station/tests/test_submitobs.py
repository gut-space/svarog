import unittest

from submitobs import get_mime_type

class TestSubmitObs(unittest.TestCase):

    def test_mime_types(self):
        cases = [
            [ "file.png", "image/png"],
            [ "FILE.PNG", "image/png"],
            [ "too.many.dots.PnG", "image/png"],
            [ "failure.log", "text/plain"],
            [ "success.txt", "text/plain"],
            [ "wojak.jpg", "image/jpeg"],
            [ "doge.JPEG", "image/jpeg"],
            [ "extensionless", "application/octet-stream"],
            [ "unknownext.tkis", "application/octet-stream"]
        ]

        for case in cases:
            self.assertEqual(get_mime_type(case[0]), case[1])
