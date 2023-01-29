# This is a recipe for NOAA APT signal decoding using GNU RADIO

from contextlib import suppress
from datetime import timedelta
import os.path
from os import remove
import signal
import waterfall

import sh

from recipes.helpers import set_sh_defaults


@set_sh_defaults
def execute(working_dir: str, frequency: str, duration: timedelta, sh=sh):

    signal_path = os.path.join(working_dir, "signal.wav")
    product_path = os.path.join(working_dir, "product.png")
    log_path = os.path.join(working_dir, "session.log")
    waterfall_path = os.path.join(working_dir, "waterfall.png")

    # TODO: If enabled, bias-T should be enabled

    # Here's the command that can be used to receive the transmission.

    # ./satnogs_noaa_apt_decoder.py --soapy-rx-device="driver=airspy" --rx-freq 137.9125M --decoded-data-file-path=/home/pi/observations/satnogs/decoded.png
    #  --samp-rate-rx=3000000 --antenna RX --gain 45 --bw 41000

    # TODO: Some of those parameters should be configurable.
    soapy_rx_device = "driver=airspy,bias=1"
    sample_rate_rx = 3000000  # number of samples per second
    gain = 45  # 45 is max for airspy, rtlsdr can go up to 49.6
    bandwidth = 36000  # specify the received bandwidth in Hz

    # Let's log the operations done by the tools to a log file. We need to flush it
    # frequently, because this file stream is also used capture tools output. Without
    # flush, the logging order gets completely messed up.
    logfile = open(log_path, "w")
    logfile.write("---satnogs_noaa_apt_decoder-------\n")
    logfile.write("soapy_rx_device=%s\n" % soapy_rx_device)
    logfile.write("sample_rate_rx=%d\n" % sample_rate_rx)
    logfile.write("gain=%f\n" % gain)
    logfile.write("bandwidth=%d\n" % bandwidth)
    logfile.flush()

    waterfall_dat = waterfall_path + ".dat"

    # Run rtl_fm/rx_fm - this records the actual samples from the RTL device
    with suppress(sh.TimeoutException):
        sh.satnogs_noaa_apt_decoder(
            # specify the device used for reception (driver=rtlsdr or driver=airspy works)
            "--soapy-rx-device", soapy_rx_device,
            # the receiving frequency
            "--rx-freq", frequency,
            # specify the gain
            "--gain", gain,
            # number of samples/s
            "--samp-rate-rx", sample_rate_rx,
            # How arctan is computed. We don't test other options.
            "--bw", bandwidth,
            # now set up the files
            "--decoded-data-file-path", product_path,
            "--waterfall-file-path", waterfall_dat,
            "--file-path", signal_path,
            _timeout=duration.total_seconds(),
            _timeout_signal=signal.SIGTERM,

            # rtl_fm and rx_fm both print messages on stderr
            _err=logfile
        )
    logfile.flush()

    # The GNU Radio pipeline generated raw waterfall data, which is reasonably big (30M or so).
    # We want to convert it into easily browseable PNG file.
    logfile.write("Converting waterfall data: %s to %s" % (waterfall_dat, waterfall_path))
    w = waterfall.Waterfall(waterfall_dat)
    w.plot(waterfall_path)

    # Remove raw waterfall data, we don't need it.
    os.remove(waterfall_dat)

    logfile.close()

    return [
        ("SIGNAL", signal_path),
        ("PRODUCT", product_path),
        ("LOG", log_path),
        ("WATERFALL", waterfall_path)
    ]
