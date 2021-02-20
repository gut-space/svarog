from datetime import timedelta
import signal

import sh


def execute(prefix: str, frequency: str, duration: timedelta):
    signal_filename = prefix + "_signal.wav"
    product_filename = prefix + "_product.png"
    
    rtl_fm_proc = sh.rtl_fm(
        "-d", 0,
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

    try:
        sh.sox(rtl_fm_proc,
            "-t", "raw",
            "-b16",
            "-es",
            "-r 48000",
            "-c1",
            "-V1",
            "-",
            signal_filename,
            "rate", "11025"
        )
    except sh.TimeoutException:
        pass


    sh.noaa_apt(
        "-o", product_filename,
        signal_filename
    )

    return {
        "signal": signal_filename,
        "product": product_filename
    }


