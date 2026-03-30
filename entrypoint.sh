#!/bin/bash

set -o errexit
set -o pipefail

db_version="${1:?}"

check_version() {
    local binary="$1"
    local installed
    installed=$("$binary" --version 2>&1 | head -1)
    if ! echo "$installed" | grep -qF "version v${db_version}."; then
        echo "Error: $binary exists but version does not match $db_version (found: $installed)" >&2
        exit 1
    fi
}

if [ -e /data/bin/mongos ] && [ ! -e /data/bin/mongod ]; then
    echo "Error: /data/bin/mongos exists without /data/bin/mongod" >&2
    exit 1
elif [ -e /data/bin/mongod ]; then
    check_version /data/bin/mongod
    if [ -e /data/bin/mongos ]; then
        mongod_ver=$(mongod --version 2>&1 | head -1 | grep -oE 'v[0-9][^ ]*')
        mongos_ver=$(mongos --version 2>&1 | head -1 | grep -oE 'v[0-9][^ ]*')
        if [ "$mongod_ver" != "$mongos_ver" ]; then
            echo "Error: mongod ($mongod_ver) and mongos ($mongos_ver) version mismatch" >&2
            exit 1
        fi
    fi
    echo "MongoDB $db_version already installed. Skipping download."
else
    echo "Downloading MongoDB $db_version …"
    echo y | ./m.sh "${db_version}"
fi

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
