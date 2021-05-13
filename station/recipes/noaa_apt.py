from contextlib import suppress
from datetime import timedelta
import os.path
import signal

import sh

from recipes.helpers import set_sh_defaults


@set_sh_defaults
def execute(working_dir: str, frequency: str, duration: timedelta, sh=sh):
    signal_path = os.path.join(working_dir, "signal.wav")
    product_path = os.path.join(working_dir, "product.png")
    log_path = os.path.join(working_dir, "session.log")

    sample_rate = 48000

    l = open(log_path, "w")
    l.write("---rx_fm log-------")

    with suppress(sh.TimeoutException):
        sh.rtl_fm(
            "-f", frequency,
            "-s", sample_rate,
            # Maximal possible value. Probably is wrong for other SDR then rtl-sdr
            "-g", 49.6,
            # Copy-paste from suspects www
            "-p", 1,
            # Higher quality downsampling - possible value 0 or 9. 9 is experimental.
            "-F", 9,
            # How arctan is computed. We don't test other options.
            "-A", "fast",
            # dc blocking filter (?)
            "-E", "DC",
            # Output to pipe, optional in this command
            "signal.raw",
            _timeout=duration.total_seconds(),
            _timeout_signal=signal.SIGTERM,
            _out=l
        )
    l.close()

    l = open(log_path, "a")

    l.write("---sox log-------")

    sh.sox(# Type of input
        "-t", "raw",
        # Sample size in bits
        "-b16",
        # Signed integer encoding
        "-es",
        "-r", sample_rate,
        # Number of channels of audio data - 1 - mono
        "-c1",
        # Verbosity level - 1 - failure messages
        "-V1",
        # Read from stdin (from pipe)
        "signal.raw",
        # Output path
        signal_path,
        # Resampling rate
        "rate", "11025",
        _out=l
    )
    l.close()
    l = open(log_path, "a")

    l.write("---noaa-apt log-------")

    sh.noaa_apt(
        "-o", product_path,
        signal_path,
        _out=l
    )

    os.remove("signal.raw")

    return [
        ("SIGNAL", signal_path),
        ("PRODUCT", product_path),
        ("LOG", log_path)
    ]
