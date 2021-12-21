#!/bin/bash

# For some strange reason, git branch --show-current doesn't work on Debian 10,
# even though the git version is 2.20 there.
BRANCH=$(git rev-parse --abbrev-ref HEAD)

if test "$BRANCH" != "master"; then
    echo "The current branch ($BRANCH) is not master, skipping update."
    exit 1
fi

# Get rid of any mess that could be in progress
git merge --abort
git cherry-pick --abort

# Discard any local changes and switch to master
git reset --hard

# Disabled for testing. The problem with testing is that if this
# checks out master, then there's no way to test this change on
# a branch. As such, this should be uncommented only AFTER this
# update procedure is merged to master.

#git checkout master

# This will wipe all non-tracked files. It's a bit much.
#git clean -fxd

# Get the new version
git pull

# Store current SHA in a file
git rev-parse HEAD > commit.txt

# Run the installation script
VENV=$PWD/venv/bin/activate
echo "Enabling venv at $VENV"

# We don't care that venv activation scritp will not be checked.
# shellcheck disable=SC1090
. "$VENV"
python setup.py install

# Restart web server (make sure this corresponds to the actual server you're running)
#sudo systemctl restart apache2
sudo systemctl restart unit
sudo systemctl restart nginx
