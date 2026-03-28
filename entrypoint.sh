#!/bin/bash

set -o errexit
set -o pipefail

db_version="${1:?}"

echo "Downloading MongoDB $db_version …"
echo y | ./m.sh "${1:?}"

# Discard the first argument.
shift

echo "Starting MongoDB cluster …"
mlaunch "$@" --bind_ip_all

echo
./print_connstrs.py < data/.mlaunch_startup

./print_connstrs.py --json > .ready < data/.mlaunch_startup

mv .ready ready

# Hang forever:
tail -f /dev/null
