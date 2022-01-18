import numpy as np

from analog_noise_estimator import estimate as estimate_analog_noise

def rate(img):
    '''Uses noise estimation based on Gauss distribution. Only for analog
       noise in form similar to "groats" in old TV.

       Supports both 1D (grayscale) and RGBA images.'''

    if len(img.shape) == 3:
        # Magic happens here. If the image is read as RGBA, then it's really a 3D array
        # (each pixel is an 4 element array of values for each channel).
        # Since the alpha channel is always 1.0, we need to use offset sum, which starts
        # with a value of -1.0. The values are in 0.0..1.0 range, so need to convert to
        # 0..255 range and then divide by 3, because we summed 3 channels (RGB).
        tmp = img.sum(axis=2, initial=-1.0)*255/3

        # The values are almost fine, except some sums are almost correct (e.g. 43.99995).
        # To address those, we'll be adding 0.5 to each value, which will then be trucnated.
        img = np.array(tmp+0.5, dtype=np.uint8)

    # Analog noise estimator requires image in range 0-255. If the image is loaded as
    # floating-point array (range 0.0-1.0), then the samples are scaled to 0.0-255.0 range.
    if img.max() <= 1.0 and np.issubdtype(img.dtype, np.floating):
       img = img * 255

    return 1.0 - estimate_analog_noise(img)
