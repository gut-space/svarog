import unittest
import os.path

import receiver


class TestReceiverRatings(unittest.TestCase):
    def setUp(self):
        data_directory = os.path.join(os.path.dirname(__file__), "data")
        self.rgb_path = os.path.join(data_directory, "rgb-image.png")
        self.gray_path = os.path.join(data_directory, "gray-image.png")

    def test_rating_for_single_layer_product(self):
        rating = receiver.get_rating_for_product(self.gray_path, "analog")
        self.assertIsNotNone(rating)
        self.assertIsInstance(rating, float)

    def test_rating_for_multi_layer_product(self):
        rating = receiver.get_rating_for_product(self.rgb_path, "digital")
        self.assertIsNotNone(rating)
        self.assertIsInstance(rating, float)

    def test_rating_for_non_exists_product(self):
        rating = receiver.get_rating_for_product("<>?\\//", "digital")
        self.assertIsNone(rating)

    def test_rating_for_non_exists_rate(self):
        rating = receiver.get_rating_for_product(self.rgb_path, "<>//\\")
        self.assertIsNone(rating)

    def test_rating_for_none_rate(self):
        rating = receiver.get_rating_for_product(self.rgb_path, None)
        self.assertIsNone(rating)

    def test_rating_for_none_arguments(self):
        rating = receiver.get_rating_for_product(None, None)  # type: ignore
        self.assertIsNone(rating)

    def test_single_layer_rating_called_with_multi_layer_product(self):
        rating = receiver.get_rating_for_product(self.rgb_path, "analog")
        # with the recent updates, the rating now works for RGB images
        self.assertIsNotNone(rating)

    def test_multi_layer_rating_called_with_single_layer_product(self):
        rating = receiver.get_rating_for_product(self.gray_path, "digital")
        self.assertIsNotNone(rating)
        self.assertIsInstance(rating, float)
