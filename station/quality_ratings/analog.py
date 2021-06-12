import numpy as np

from analog_noise_estimator import estimate as estimate_analog_noise


def rate(img):
    '''Uses noise estimation based on Gauss distribution. Only for analog
       noise in form similar to "groats" in old TV. Supports only 1D (grayscale)
       images.'''
    # Analog noise estimator requires image in range 0-255. If image is loading as
    # floating-point array (range 0-1) then it scales the values.
    if img.max() <= 1.0 and np.issubdtype(img.dtype, np.floating):
       img = img * 255 
    return 1.0 - estimate_analog_noise(img)
