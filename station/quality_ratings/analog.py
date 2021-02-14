from analog_noise_estimator import estimate as estimate_analog_noise


def rate(img):
    '''Uses noise estimation based on Gauss distribution. Only for analog
       noise in form similar to "groats" in old TV. Supports only 1D (grayscale)
       images.'''
    return 1.0 - estimate_analog_noise(img)
