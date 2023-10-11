from contextlib import suppress
from datetime import timedelta, datetime
import os.path
import signal
import sh
from recipes.helpers import set_sh_defaults


@set_sh_defaults
def execute(working_dir: str, frequency: str, duration: timedelta, sh=sh):
    signal_path = os.path.join(working_dir, "signal.wav")
    product_path = os.path.join(working_dir, "product.png")
    raw_path = os.path.join(working_dir, "signal.raw")
    log_path = os.path.join(working_dir, "session.log")

    print(f"Writing log to {log_path}")
    logfile = open(log_path, "w")
    logfile.write(f"meteor-qpsk recipe, writing to {working_dir}, capturing freq {frequency}, duration {duration}\n")
    logfile.flush()

    normalized_signal_path = os.path.join(working_dir, "normalized_signal.wav")
    qpsk_path = os.path.join(working_dir, "qpsk")
    dump_prefix_path = os.path.join(working_dir, "dump")
    dump_path = dump_prefix_path + ".dec"
    product_raw_prefix_path = os.path.join(working_dir, "product_raw")
    product_raw_path = product_raw_prefix_path + ".bmp"

    # Record signal

    logfile.write(f"{str(datetime.now())} --- rtl_fm log ---\n")
    logfile.flush()
    with suppress(sh.TimeoutException):
        fm_proc = sh.rtl_fm(
            # Modulation raw
            "-M", "raw",
            # Set frequency (in Hz, e.g. 137MHz)
            "-f", frequency,
            # Enable bias-T (disabled)
            # "-T",
            # Specify sampling rate (e.g. 48000 Hz)
            "-s", 48000,
            # Almost maximal possible value. Probably is wrong for other SDR then rtl-sdr
            "-g", 48,
            # Copy-paste from suspicious www
            "-p", 1,
            raw_path,
            _timeout=duration.total_seconds(),
            _timeout_signal=signal.SIGKILL,
            _err=logfile,
            _bg_exc=False
            )
        logfile.write(f"rtl_fm started, pid is {fm_proc.pid}\n")

    logfile.write(f"{str(datetime.now())} --- sox (step 1, convert) log ---\n")
    logfile.flush()
    sh.sox(
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
        raw_path,
        # Type of output
        "-t", "wav",
        signal_path,
        # Resampling rate
        "rate", "96k",
        _out=logfile
        )

    # Normalize signal
    logfile.write(f"{str(datetime.now())} --- sox (step 2, normalize signal) log ---\n")
    logfile.flush()
    sh.sox(
        signal_path,
        normalized_signal_path,
        # Normalize to 0dBfs
        "gain", "-n",
        _out=logfile
    )

    # Demodulating
    logfile.write(f"{str(datetime.now())} --- meteor_demod log ---\n")
    logfile.flush()
    sh.meteor_demod(
        "-o", qpsk_path,
        "-B", normalized_signal_path,
        _out=logfile
    )

    # Keep original file timestamp
    sh.touch("-r", signal_path, qpsk_path)

    # Decode QPSK
    logfile.write(f"{str(datetime.now())} --- medet (decode QPSK) log ---\n")
    logfile.flush()
    sh.medet(
        qpsk_path,
        dump_prefix_path,
        # Make doceded dump (fastest)
        "-cd",
        _out=logfile
    )

    # Generate images
    logfile.write(f"{str(datetime.now())} --- medet (generate images) log ---\n")
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
    logfile.write(f"{str(datetime.now())} --- convert product log ---\n")
    logfile.flush()
    sh.convert(product_raw_path, product_path, _out=logfile)

    logfile.write(f"{str(datetime.now())} meteor_qpsk recipe complete.\n")
    logfile.flush()

    return [
        ("SIGNAL", signal_path),
        ("PRODUCT", product_path),
        ("LOG", log_path),
        ("RAW", raw_path)
    ]
