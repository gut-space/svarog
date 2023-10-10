import datetime
import logging
import os
import shutil
import sys
import typing
import json

from matplotlib.pyplot import imread

from utils.functional import first
from utils.models import get_satellite
from utils.dates import from_iso_format
from utils.configuration import open_config
from submitobs import submit_observation, SubmitRequestData
from recipes import factory
from quality_ratings import get_rate_by_name
from sh import CommandNotFound
from metadata import Metadata


def move_to_satellite_directory(root: str, sat_name: str, path: str):
    now = datetime.datetime.utcnow()
    timestamp_dir = now.strftime(r"%Y-%m-%d")
    base = os.path.basename(path)
    new_dir = os.path.join(root, sat_name, timestamp_dir)
    new_path = os.path.join(new_dir, base)

    os.makedirs(new_dir, exist_ok=True)
    shutil.move(path, new_path)


config = open_config()


def get_rating_for_product(product_path: str, rate_name: typing.Optional[str]) \
        -> typing.Optional[float]:
    if rate_name is None:
        return None

    try:
        rate = get_rate_by_name(rate_name)
        img = imread(product_path)
        return rate(img)
    except Exception:
        logging.error("Error during rating the product", exc_info=True)
        return None


def cmd():
    if len(sys.argv) < 3:
        print("Usage: receiver.py <name> <los> [opts]")
        print("name - name of the receiver")
        print("los - loss of signal time (UTC)")
        return

    _, name, los, *opts = sys.argv

    logging.info("Starting receiver job: name=%s los=%s, PATH=%s" % (name, los, os.getenv('PATH')))

    satellite = get_satellite(config, name)

    aos_datetime = datetime.datetime.utcnow()
    los_datetime = from_iso_format(los)

    # TODO: calculate TCA properly. There may be cases when an observation is interrupted by another,
    # better pass. Also, part of the pass could be obscured by buildings.
    tca_datetime = aos_datetime + (los_datetime - aos_datetime) / 2

    dir = factory.get_dir(satellite, los_datetime)

    # Early metadata write to local file. We do this before the recipe is executed, because the recipe
    # may file. If the recipe returns without any major issues, we will write it again with possibly
    # extra metadata returned by the recipe.
    m = Metadata()
    m.set("satellite", satellite["name"])
    m.set("aos", aos_datetime.isoformat())
    m.set("los", los_datetime.isoformat())
    m.set("tca", tca_datetime.isoformat())
    # Write metadata to local file
    metadata_file = os.path.join(dir, "metadata.json")
    m.writeFile(metadata_file)
    logging.info(f"INFO: metadata written to {metadata_file}.")

    try:
        results, dir, metadata = factory.execute_recipe(satellite, los_datetime)
    except:
        logging.error("ERROR: Recipe execution failed, exception:", exc_info=True)
        return

    # We're entirely sure the recipe is honest and reported only files that were actually created *cough*.
    # However, if things go south and for some reason the recipe is mistaken (e.g. the noaa-apt fails to
    # create a .png file, because the input WAV file was junk), then we should filter out the files
    # that do not exist.
    files_txt = ""
    valid_results = []
    for a, b in results:
        if not os.path.exists(b):
            logging.warning("Recipe claims to provide %s file %s, but this file doesn't exist. Skipping." % (a, b))
            continue
        files_txt += a + ":" + b + " "
        valid_results.append((a, b))
    results = valid_results

    logging.info("Recipe execution complete, generated %d result[s] (%s), stored in %s directory." % (len(results), files_txt, dir))

    # Post-processing
    save_mode = satellite["save_to_disk"]
    should_submit = satellite["submit"]

    signal = first(results, lambda r: r[0] == "SIGNAL")
    products = filter(lambda r: r[0] == "PRODUCT", results)

    # Use the metadata stored in file, but supplement it with details returned by the recipe
    m = Metadata()
    for x in metadata:
        m.set(x, metadata[x])
    m.set("satellite", satellite["name"])
    m.set("aos", aos_datetime.isoformat())
    m.set("los", los_datetime.isoformat())
    m.set("tca", tca_datetime.isoformat())
    # Write metadata to local file
    metadata_file = os.path.join(dir, "metadata.json")
    m.writeFile(metadata_file)
    logging.info(f"INFO: Updated metadata written to {metadata_file}.")

    if should_submit:
        logging.info("Submitting results")
        product = first(products, lambda _: True)
        if product is not None:
            logging.info("Getting rating for product %s (rating algorithm is %s)" % (product[1], satellite.get("rate")))
            rating = get_rating_for_product(product[1], satellite.get("rate"))
            logging.info("Product %s got rating %s" % (product[1], rating))
            # TODO: Submit ALL products and logs
            logging.warning("TODO: signal submission not implemented yet (%s)" % signal)
            files = [product[1]]
            submit_observation(
                SubmitRequestData(
                    files, name, aos_datetime, tca_datetime,
                    los_datetime, m.getString(), rating
                )
            )

    # Now, delete files we don't want to save
    for type, f in products:
        if type == save_mode or type == "ALL":
            # don't delete this file
            continue
        logging.info("Deleting file %s (type %s), because save_mode is %s" % (f, type, save_mode))
        os.remove(f)


if __name__ == '__main__':
    try:
        cmd()
    except CommandNotFound as e:
        _, name, los, *opts = sys.argv
        logging.error("Command not found: %s when executing receiver %s (LOS: %s)" % (e, name, los), exc_info=True)
        logging.error("Make sure you have PATH set up correctly in your crontab. See https://stackoverflow.com/questions/10129381/crontab-path-and-user")
    except Exception:
        _, name, los, *opts = sys.argv
        logging.error("Failed receiver %s (LOS: %s)" % (name, los), exc_info=True)
