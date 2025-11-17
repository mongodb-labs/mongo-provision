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

# Hang forever:
tail -f /dev/null
