from contextlib import suppress
from datetime import timedelta
import os.path
import signal

import sh

from helpers import set_sh_defaults


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
    rtl_fm_proc = sh.rtl_fm(
        "-M", "raw",
        "-f", frequency,
        "-s", 48000,
        "-g", 48,
        "-p", 1,
        _timeout=duration.total_seconds(),
        _timeout_signal=signal.SIGTERM,
        _piped=True
    )

    with suppress(sh.TimeoutException):
        sh.sox(rtl_fm_proc,
            "-t", "raw",
            "-r", "288k",
            "-c", 2,
            "-b", 16,
            "-e", "s",
            "-",
            "-t", "wav",
            signal_path,
            "rate", "96k"
        )

    # Normalize signal
    sh.sox(signal_path, normalized_signal_path, "gain", "-n")

    # Demodulating
    sh.meteor_demod(
        sh.yes(_piped=True),
        "-o", qpsk_path,
        "-B", normalized_signal_path
    )

    # Keep original file timestamp
    sh.touch("-r", signal_path, qpsk_path)

    # Decode QPSK
    sh.medet(qpsk_path, dump_prefix_path, "-cd")

    # Generate images
    sh.medet(dump_path, product_raw_prefix_path,
        "-r", 66,
        "-g", 65,
        "-b", 64,
        "-d"
    )

    # Convert to PNG
    sh.convert(product_raw_path, product_path)

    return {
        "signal": signal_path,
        "product": product_path
    }
