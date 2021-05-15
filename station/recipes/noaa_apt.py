from contextlib import suppress
from datetime import timedelta
import os.path
import signal

import sh

from recipes.helpers import set_sh_defaults


@set_sh_defaults
def execute(working_dir: str, frequency: str, duration: timedelta, sh=sh):
    raw_path = os.path.join(working_dir, "signal.raw")
    signal_path = os.path.join(working_dir, "signal.wav")
    product_path = os.path.join(working_dir, "product.png")
    log_path = os.path.join(working_dir, "session.log")

    sample_rate = 48000

    l = open(log_path, "w")
    l.write("---rtl_fm log-------\n")
    l.flush()

    # Run rtl_fm/rx_fm - this records the actual samples from the RTL device
    with suppress(sh.TimeoutException):
        sh.rtl_fm(
            # Specify frequency (in Hz, e.g. 137MHz)
            "-f", frequency,
            # Specify sampling rate (e.g. 48000 Hz)
            "-s", sample_rate,
            # Maximal possible value. Probably is wrong for other SDR then rtl-sdr
            "-g", 49.6,
            # Copy-paste from suspects www
            "-p", 1,
            # Higher quality downsampling - possible value 0 or 9. 9 is experimental.
            "-F", 9,
            # Enable bias-T
            "-T",
            # How arctan is computed. We don't test other options.
            "-A", "fast",
            # dc blocking filter (?)
            "-E", "DC",
            # Output to pipe, optional in this command
            raw_path,
            _timeout=duration.total_seconds(),
            _timeout_signal=signal.SIGTERM,

            # rtl_fm and rx_fm both print messages on stderr
            _err=l
        )
    l.flush()

    l.write("---sox log-------\n")
    l.flush()

    # Run sox - this convert raw samples into audible WAV
    sh.sox(# Type of input
        "-t", "raw",
        # Sample size in bits
        "-b16",
        # Signed integer encoding
        "-es",
        "-r", sample_rate,
        # Number of channels of audio data - 1 - mono
        "-c1",
        # Verbosity level (0 - silence, 1 - failure messages, 2 - warnings, 3 - processing phases, 4 - debug)
        "-V3",
        # Read from the raw file (instead of stdin via pipe)
        raw_path,
        # Output path
        signal_path,
        # Resampling rate
        "rate", "11025",
        _out=l
    )
    l.flush()

    l.write("---noaa-apt log-------\n")
    l.flush()

    # Run noaa_apt - this decodes APT from the audio file into PNG image.
    sh.noaa_apt(
        "-o", product_path,
        signal_path,
        _out=l
    )
    l.flush()

    try:
        os.remove(raw_path)
    except FileNotFoundError:
        l.write("noaa_apt recipe: Tried to delete %(raw_path)s, but the file was not found.\n")
        pass

    l.close()

    return [
        ("SIGNAL", signal_path),
        ("PRODUCT", product_path),
        ("LOG", log_path)
    ]
