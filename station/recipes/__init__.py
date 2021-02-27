import recipes.noaa_apt
import recipes.meteor_qpsk

# Each recipe should be registered in this dictionary
recipes = {
    'noaa-apt': recipes.noaa_apt.execute,
    'meteor-qpsk': recipes.meteor_qpsk.execute
}

__all__ = ["recipes"]