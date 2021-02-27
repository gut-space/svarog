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
    
    fm_proc = sh.rx_fm(
        "-f", frequency,
        "-s", 48000,
        "-g", 49.6,
        "-p", 1,
        "-F", 9,
        "-A", "fast",
        "-E", "DC",
        "-",
        _timeout=duration.total_seconds(),
        _timeout_signal=signal.SIGTERM,
        _piped=True
    )

    with suppress(sh.TimeoutException):
        sh.sox(fm_proc,
            "-t", "raw",
            "-b16",
            "-es",
            "-r", 48000,
            "-c1",
            "-V1",
            "-",
            signal_path,
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
