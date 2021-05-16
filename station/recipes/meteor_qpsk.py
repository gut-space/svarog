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

    normalized_signal_path = os.path.join(working_dir, "normalized_signal.wav")
    qpsk_path = os.path.join(working_dir, "qpsk")
    dump_prefix_path = os.path.join(working_dir, "dump")
    dump_path = dump_prefix_path + ".dec"
    product_raw_prefix_path = os.path.join(working_dir, "product_raw")
    product_raw_path = product_raw_prefix_path + ".bmp"

    # Let's log the operations done by the tools to a log file. We need to flush it
    # frequently, because this file stream is also used capture tools output. Without
    # flush, the logging order gets completely messed up.
    logfile = open(log_path, "w")
    logfile.write("---rtl_fm log-------\n")
    logfile.flush()

    # Record signal
    fm_proc = sh.rtl_fm(
        # Modulation raw
        "-M", "raw",
        # Set frequency (in Hz, e.g. 137MHz)
        "-f", frequency,
        # Enable bias-T
        "-T",
        # Specify sampling rate (e.g. 48000 Hz)
        "-s", 48000,
        # Almost maximal possible value. Probably is wrong for other SDR then rtl-sdr
        "-g", 48,
        # Copy-paste from suspects www
        "-p", 1,
        raw_path,
        _timeout=duration.total_seconds(),
        _timeout_signal=signal.SIGTERM,

        # rtl_fm and rx_fm both print messages on stderr
        _err=logfile
    )

    logfile.flush()
    logfile.write("---sox log 1: resample-----\n")
    logfile.flush()

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
            # Read from the raw file
            raw_path,
            # Type of output
            "-t", "wav",
            signal_path,
            # Resampling rate
            "rate", "96k",
            _out=logfile
        )

    logfile.flush()
    logfile.write("---sox log 2: normalize ------\n")
    logfile.flush()

    # Normalize signal
    sh.sox(
        signal_path,
        normalized_signal_path,
        # Normalize to 0dBfs
        "gain", "-n",
        _out=logfile
    )

    logfile.flush()
    logfile.write("--- meteor-demod ------\n")
    logfile.flush()

    # Demodulating
    sh.meteor_demod(
        sh.yes(_piped=True),
        "-o", qpsk_path,
        "-B", normalized_signal_path,
        _out=logfile
    )

    # Keep original file timestamp
    sh.touch("-r", signal_path, qpsk_path)

    logfile.flush()
    logfile.write("--- medet: decode QPSK ------\n")
    logfile.flush()

    # Decode QPSK
    sh.medet(
        qpsk_path,
        dump_prefix_path,
        # -q (quiet mode, don't print progress status)
        '-q',
        # Make decoded dump (fastest)
        "-cd",
        _out = logfile
    )

    logfile.flush()
    logfile.write("--- medet: generate image ------\n")
    logfile.flush()

    # Generate images
    sh.medet(dump_path, product_raw_prefix_path,
        # APID for red
        "-r", 64,
        # APID for green
        "-g", 65,
        # APID for blue
        "-b", 66,
        # Use dump
        "-d",
        _out = logfile
    )

    logfile.flush()
    logfile.write("--- convert: convert the output image file to PNG ------\n")
    logfile.flush()

    # Convert to PNG
    sh.convert(product_raw_path, product_path)

    logfile.close()

    return [
        ("SIGNAL", signal_path),
        ("PRODUCT", product_path),
        ("LOG", log_path)
    ]
