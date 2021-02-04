#!/bin/bash

# This script is supposed to be called periodically from a cron.

# First step is to assess the git situation. Under normal circumstances (station run by user),
# there is only 0 or 1 possible. However, in developer case, there may be local changes.
# We don't want to throw them away, but at the same time we want to get any updates that
# may be available on the server. As such, we're stashing local changes. Those can be
# reinstated (git stash pop) or discarded (git stash drop). It's possible to stash multiple
# layers, so this mechanism is safe in principle.
remote_repo_status() {
    UPSTREAM="origin/master"
    LOCAL=$(git rev-parse @)
    REMOTE=$(git rev-parse "$UPSTREAM")
    BASE=$(git merge-base @ "$UPSTREAM")

    if [ $LOCAL = $REMOTE ]; then
        # "Up-to-date"
        return 0
    elif [ $LOCAL = $BASE ]; then
        # "Need to pull"
        return 1
    elif [ $REMOTE = $BASE ]; then
        # "Need to push"
        return 2
    else
        # "Diverged"
        return 3
    fi
}

# We need to fetch first. Otherwise the remote_repo_status would be based on outdated information
# and would never pick new changes.
git fetch
remote_repo_status
repo_status=$?

if (( repo_status == 0)); then
    echo "Repository is up-to-date"
    exit 0
fi

# If there are local changes, lets stash them and try to pull the new changes anyway.
if (( repo_status > 1)); then
    echo "Repository is modified. Your local changes are stashed."
    git stash save
fi

# If we gotten so far, there's something new. Pull and rerun the setup procedure.
git pull
sudo python3 setup.py install
python3 cli.py clear
python3 cli.py plan --force

# Store current SHA in a file
git rev-parse HEAD > commit.txt
