#!/usr/bin/env python3
import os
from setuptools import setup, find_packages
import argparse
import shutil
import stat
import sys

EXTERNAL_DEPENDENCIES = ["noaa-apt", "rtl_fm", "sox", "meteor-demod", "medet", "convert"]
RECIPE_DIR = "recipes"


def get_requirements_and_links():
    """Returns required packages list, parsed from requirements.txt. The tricky part is to
       handle custom packages (-e git+https://...#egg=package-name). This is currently used
       for installing angalog-signal-estimator"""
    REQUIREMENTS = []
    DEP_LINKS = []

    for i in open("requirements.txt").readlines():
        i = i.strip()

        # skip empty and commented lines
        if not len(i) or (len(i) and i[0] == '#'):
            continue

        # Handle custom download URLs
        if i.find("://") != -1:
            name = i[i.find('egg=') + 4:]
            url = i[i.find('git+'):]
            print("Found custom package: name=[%s] url=[%s]" % (name, url))
            REQUIREMENTS.append(name)
            DEP_LINKS.append(url)
            continue

        # If this is an option, ignore it. pip 20.x started adding some extra options
        # in the requirements.txt file.
        if i[0] == '-':
            print("Ignoring unknown option: %s" % i)
            continue

        # Ok, this looks like a regular dependency.
        REQUIREMENTS.append(i)

    return REQUIREMENTS, DEP_LINKS


REQUIREMENTS, DEP_LINKS = get_requirements_and_links()


def setup_aliases():

    # First, we need to find the cli.py file. It's not as trivial, as typically the code
    # can be invoked as python3 setup.py install from the station/ dir, but could also be
    # station/setup.py install from a directory above it. But we don't want to spend too
    # much wrestling with iths.
    alias = 'alias station="python3 ' + os.getcwd() + '/cli.py"'

    # Now find the true location of ~/.bash_aliases and check if there's an alias
    # for station. Note we don't care if it ours or not. We wouldn't dare to overwrite
    # user's preferences. User knows best *cough*.
    ALIAS_FILE = os.path.join(os.getenv('HOME'), ".bash_aliases")
    try:
        for line in open(ALIAS_FILE).readlines():
            if line.find("alias station") != -1:
                print("alias station already set up: %s, skipping alias setup." % line)
                return
    except Exception:
        print(ALIAS_FILE + " not found")

    if os.getenv('USER') == 'root':
        print("We're NOT going to set any aliases for root. Please manually edit your")
        print(".bash_aliases file and add this line:")
        print("")
        print(alias)
        print("")
        return

    # Ok, we're ready to rock! Add the alias.
    f = open(ALIAS_FILE, "a")
    f.write(alias + os.linesep)
    f.close()
    print("Alias %s written to %s file." % (alias, ALIAS_FILE))


def check_deps():
    """Check if required tools are available.

    :return: True if all is ok, False otherwise"""
    missing = False
    for dep in EXTERNAL_DEPENDENCIES:
        print('Checking if "%s" is installed...' % (dep,), end="")
        if shutil.which(dep) is None:
            print("MISSING")
            missing = True
        else:
            print("OK")

    return not missing


def setup_recipes():
    """Sets the recipes' exec flag"""
    for recipe_candidate_name in os.listdir(RECIPE_DIR):
        if not recipe_candidate_name.endswith(".sh"):
            continue
        recipe_path = os.path.join(RECIPE_DIR, recipe_candidate_name)
        st = os.stat(recipe_path)
        os.chmod(recipe_path, st.st_mode | stat.S_IXUSR)


parser = argparse.ArgumentParser(description='Set up the Svarog station environment.')
parser.add_argument('--skip-python', dest='skip_python', action='store_const',
                    const=True, default=False,
                    help='skips Python package installation')
parser.add_argument('--ignore-missing-deps', dest='ignore_missing_deps', action='store_const',
                    const=True, default=False,
                    help='continue even if tool dependencies (noaa-apt, medet, ...) are missing.')

args, _ = parser.parse_known_args()

if not check_deps():
    if not args.ignore_missing_deps:
        print('Please install missing dependencies.')
        sys.exit(1)
    else:
        print("WARNING: Some dependencies are missing. That may be OK if you install them later")
        print("WARNING: or are not interested in receiving specific satellites. You can always")
        print("WARNING: rerun the setup to check if they all were detected.")

if not args.skip_python:
    setup(name='svarog-station',
          version='1.0',
          description='Svarog ground station management tool',
          author='SF, TM',
          packages=find_packages(),
          install_requires=REQUIREMENTS,
          dependency_links=DEP_LINKS
          )
else:
    print("WARNING: Python installation skipped. Make sure to install them manually using this command:")
    print("WARNING: ")
    print("WARNING: $ pip3 install -r requirements.txt")
    print("WARNING: ")

setup_recipes()
setup_aliases()

print("svarog-station installation complete. Log out, log in, and then:")
print("$ station config")
print("$ station plan")
