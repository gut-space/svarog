from analog_noise_estimator import estimate as estimate_analog_noise


def rate(img):
    return 1.0 - estimate_analog_noise(img)
