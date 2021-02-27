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
    
    sample_rate = 48000

    fm_proc = sh.rx_fm(
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
        "-",
        _timeout=duration.total_seconds(),
        _timeout_signal=signal.SIGTERM,
        _piped=True
    )

    with suppress(sh.TimeoutException):
        sh.sox(fm_proc,
            # Type of input
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
            "-",
            # Output path
            signal_path,
            # Resampling rate
            "rate", "11025"
        )

    sh.noaa_apt(
        "-o", product_path,
        signal_path
    )

    return [
        ("SIGNAL", signal_path),
        ("PRODUCT", product_path)
    ]
