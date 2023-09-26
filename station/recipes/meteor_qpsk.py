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

    normalized_signal_path = os.path.join(working_dir, "normalized_signal.wav")
    qpsk_path = os.path.join(working_dir, "qpsk")
    dump_prefix_path = os.path.join(working_dir, "dump")
    dump_path = dump_prefix_path + ".dec"
    product_raw_prefix_path = os.path.join(working_dir, "product_raw")
    product_raw_path = product_raw_prefix_path + ".bmp"

    # Record signal
    fm_proc = sh.rtl_fm(
        # Modulation raw
        "-M", "raw",
        # Set frequency (in Hz, e.g. 137MHz)
        "-f", frequency,
        # Enable bias-T
        #"-T",
        # Specify sampling rate (e.g. 48000 Hz)
        "-s", 48000,
        # Almost maximal possible value. Probably is wrong for other SDR then rtl-sdr
        "-g", 48,
        # Copy-paste from suspects www
        "-p", 1,
        _timeout=duration.total_seconds(),
        _timeout_signal=signal.SIGTERM,
        _piped=True
    )

    with suppress(sh.TimeoutException):
        sh.sox(fm_proc,
               # Type of input
               "-t", "raw",
               "-r", "288k",
               # Channels - 2 - stereo
               "-c", 2,
               # Sample size
               "-b", 16,
               # Signed integer encoding
               "-e", "s",
               # Verbosity level (0 - silence, 1 - failure messages, 2 - warnings, 3 - processing phases, 4 - debug)
               "-V3",
               # Read from stdin (from pipe)
               "-",
               # Type of output
               "-t", "wav",
               signal_path,
               # Resampling rate
               "rate", "96k"
               )

    # Normalize signal
    sh.sox(
        signal_path,
        normalized_signal_path,
        # Normalize to 0dBfs
        "gain", "-n"
    )

    # Demodulating
    sh.meteor_demod(
        sh.yes(_piped=True),
        "-o", qpsk_path,
        "-B", normalized_signal_path
    )

    # Keep original file timestamp
    sh.touch("-r", signal_path, qpsk_path)

    # Decode QPSK
    sh.medet(
        qpsk_path,
        dump_prefix_path,
        # Make doceded dump (fastest)
        "-cd"
    )

    # Generate images
    sh.medet(dump_path, product_raw_prefix_path,
             # APID for red
             "-r", 66,
             # APID for green
             "-g", 65,
             # APID for blue
             "-b", 64,
             # Use dump
             "-d"
             )

    # Convert to PNG
    sh.convert(product_raw_path, product_path)

    return [
        ("SIGNAL", signal_path),
        ("PRODUCT", product_path)
    ]
