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
    with suppress(sh.TimeoutException):
        fm_proc = sh.rtl_fm(
            # Modulation raw
            "-M", "raw",
            # Set frequency (in Hz, e.g. 137MHz)
            "-f", frequency,
            # Enable bias-T
            #"-T",
            # Specify sampling rate (e.g. 48000 Hz)
            "-s", "288k",
            # Almost maximal possible value. Probably is wrong for other SDR then rtl-sdr
            "-g", 49,
            # enable DC filter
            "-E", "dc",
            # ppm error
            "-p", 1,
            raw_path,
            _timeout=duration.total_seconds(),
            _timeout_signal=signal.SIGTERM,

            # rtl_fm and rx_fm both print messages on stderr
            _err=logfile
        )

    logfile.flush()

    logfile.write("---sox log-------\n")
    logfile.flush()

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
        "rate", "96k",

        _out=logfile
    )

    logfile.flush()

    logfile.write("---sox 2: normalize-------\n")
    logfile.flush()

    # Normalize signal
    sh.sox(
        signal_path,
        normalized_signal_path,
        # Normalize to 0dBfs
        "gain", "-n",

        _out=logfile
    )

    # Demodulating
    logfile.flush()

    logfile.write("---meteor-demod-------\n")
    logfile.flush()
    sh.meteor_demod(
        sh.yes(_piped=True),
        "-o", qpsk_path,
        "-B", normalized_signal_path,

        _out=logfile
    )

    # Keep original file timestamp
    sh.touch("-r", signal_path, qpsk_path)

    # Decode QPSK
    logfile.flush()

    logfile.write("---medet 1: decode QPSK-------\n")
    logfile.flush()
    sh.medet(
        qpsk_path,
        dump_prefix_path,
        # Make doceded dump (fastest)
        "-cd",
        _out=logfile
    )

    # Generate images
    logfile.flush()

    logfile.write("---medet 2: generate image-------\n")
    logfile.flush()
    sh.medet(dump_path, product_raw_prefix_path,
        # APID for red
        "-r", 66,
        # APID for green
        "-g", 65,
        # APID for blue
        "-b", 64,
        # Use dump
        "-d",
        _out=logfile
    )

    # Convert to PNG
    logfile.write("---medet 2: generate image-------\n")
    logfile.flush()

    sh.convert(product_raw_path, product_path, _out=logfile)

    logfile.write("Done, returning:")
    logfile.write(f"- SIGNAL:  {signal_path}")
    logfile.write(f"- PRODUCT: {product_path}")
    logfile.close()

    return [
        ("SIGNAL", signal_path),
        ("PRODUCT", product_path)
    ]
