import unittest

import numpy as np

import quality_ratings


class TestQualityRatings(unittest.TestCase):
    def test_list_names(self):
        names = quality_ratings.get_rate_names()
        self.assertTrue("analog" in names)
        self.assertTrue("digital" in names)

    def test_get_rate_by_name(self):
        self.assertIsNotNone(quality_ratings.get_rate_by_name("analog"))
        self.assertIsNotNone(quality_ratings.get_rate_by_name("digital"))

    def test_analog_rating_on_gaussian_noise_small_sigma(self):
        img = np.random.normal(scale=1, size=(1000, 1000))
        rate = quality_ratings.get_rate_by_name("analog")
        rating = rate(img)
        self.assertAlmostEquals(1.0, rating, 2)

    def test_analog_rating_on_gaussian_noise_big_sigma(self):
        img = np.random.normal(scale=20, size=(1000, 1000))
        rate = quality_ratings.get_rate_by_name("analog")
        rating = rate(img)
        self.assertAlmostEquals(0.0, rating, 2)

    def test_analog_rating_on_gaussian_noise_medium_sigma(self):
        img = np.random.normal(scale=12.7, size=(1000, 1000))
        rate = quality_ratings.get_rate_by_name("analog")
        rating = rate(img)
        self.assertAlmostEquals(0.5, rating, 1)

    def test_analog_rating_on_blank(self):
        '''Image doesn't contain any noise - good quality'''
        img = np.zeros((1000, 1000))
        rate = quality_ratings.get_rate_by_name("analog")
        rating = rate(img)
        self.assertAlmostEquals(1, rating, 2)

    def test_digital_rating_on_black(self):
        '''All pixels are black - no data - bad quality'''
        img = np.zeros((1000, 1000))
        rate = quality_ratings.get_rate_by_name("digital")
        rating = rate(img)
        self.assertAlmostEquals(0, rating, 3)

    def test_digital_rating_on_white(self):
        '''All pixels aren't black - full data - goo quality'''
        img = np.ones((1000, 1000))
        rate = quality_ratings.get_rate_by_name("digital")
        rating = rate(img)
        self.assertAlmostEquals(1, rating, 3)

    def test_digital_rating_on_half_zeros(self):
        z = np.ones((1000, 500))
        o = np.zeros((1000, 500))
        img = np.hstack((z, o))
        rate = quality_ratings.get_rate_by_name("digital")
        rating = rate(img)
        self.assertAlmostEquals(0.5, rating, 3)

    def test_digital_rating_on_quater_zeros(self):
        ones = np.ones((1000, 750))
        zeros = np.zeros((1000, 250))
        img = np.hstack((zeros, ones))
        rate = quality_ratings.get_rate_by_name("digital")
        rating = rate(img)
        self.assertAlmostEquals(0.75, rating, 3)

    def test_digital_rating_on_3d_black(self):
        img = np.zeros((1000, 1000, 3))
        rate = quality_ratings.get_rate_by_name("digital")
        rating = rate(img)
        self.assertAlmostEquals(0, rating, 3)

    def test_digital_rating_on_3d_white(self):
        img = np.ones((1000, 1000, 3))
        rate = quality_ratings.get_rate_by_name("digital")
        rating = rate(img)
        self.assertAlmostEquals(1, rating, 3)

    def test_digital_rating_on_3d_quater_zeros(self):
        img = np.ones((1000, 1000, 3))
        img[:,:,2] = 0
        img[:250,:,0:2] = 0
        rate = quality_ratings.get_rate_by_name("digital")
        rating = rate(img)
        self.assertAlmostEquals(0.75, rating, 3)
