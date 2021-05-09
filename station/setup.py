#!/usr/bin/env python
import os
from setuptools import setup, find_packages
import shutil
import stat
import sys


def get_requirements_and_links():
    """Returns required packages list, parsed from requirements.txt. The tricky part is to
       handle custom packages (-e http://"""
    REQUIREMENTS = []
    DEP_LINKS = []

    for i in open("requirements.txt").readlines():
        i = i.strip()

        # skip empty and commented lines
        if not len(i) or (len(i) and i[0] == '#'):
            continue

        # Handle custom download URLs
        if i.find("://") != -1:
            name=i[i.find('egg=') + 4:]
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

EXTERNAL_DEPENDENCIES = ["noaa-apt", "rx_fm", "sox", "meteor-demod", "medet", "convert"]

RECIPE_DIR = "recipes"

# Check if required tools are available.
missing = False
for dep in EXTERNAL_DEPENDENCIES:
    print('Checking if "%s" is installed...' % (dep,), end="")
    if shutil.which(dep) is None:
        print("MISSING")
        missing = True
    else:
        print("OK")

if missing:
    print('Please install missing dependencies.')
    sys.exit(1)

for recipe_candidate_name in os.listdir(RECIPE_DIR):
    if not recipe_candidate_name.endswith(".sh"):
        continue
    recipe_path = os.path.join(RECIPE_DIR, recipe_candidate_name)
    st = os.stat(recipe_path)
    os.chmod(recipe_path, st.st_mode | stat.S_IXUSR)

setup(name='svarog-station',
      version='1.0',
      description='Svarog ground station management tool',
      author='SF, TM',
      packages=find_packages(),
      install_requires=REQUIREMENTS,
      dependency_links=DEP_LINKS
)
