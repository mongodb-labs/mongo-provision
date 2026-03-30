#!/usr/bin/env python3
import atexit
import json
import os
import subprocess
import sys
import time

TOPOLOGIES = {
    "single":      ["--single"],
    "replset-3":   ["--replicaset", "--nodes", "3", "--hostname", "localhost"],
    "sharded-2x3": ["--replicaset", "--sharded", "2", "--nodes", "3"],
}

CONTAINER = "mongo-provision-test"
READY_TIMEOUT = 5 * 60  # seconds


def run(*args, **kwargs):
    return subprocess.run(args, **kwargs)


def main():
    if len(sys.argv) != 3:
        sys.exit(f"Usage: {sys.argv[0]} <version> <topology>")

    version, topology = sys.argv[1], sys.argv[2]

    if topology not in TOPOLOGIES:
        known = ", ".join(TOPOLOGIES.keys())
        sys.exit(f"Unknown topology: {topology!r} (expected one of: {known})")

    atexit.register(lambda: run("docker", "rm", "-f", CONTAINER, capture_output=True))

    run(
        "docker", "run", "-d", "--name", CONTAINER,
        "-p", "27017-27099:27017-27099",
        "mongo-provision", version, *TOPOLOGIES[topology],
        check=True,
    )

    print("Awaiting cluster readiness …")
    deadline = time.monotonic() + READY_TIMEOUT
    while True:
        if time.monotonic() > deadline:
            sys.exit("Timed out waiting for cluster to be ready")

        ps = run(
            "docker", "ps", "-q",
            "--filter", f"name={CONTAINER}",
            "--filter", "status=running",
            capture_output=True, text=True,
        )
        if not ps.stdout.strip():
            print("Container has exited:", file=sys.stderr)
            run("docker", "logs", CONTAINER)
            sys.exit(1)

        if run("docker", "exec", CONTAINER, "test", "-e", "ready", capture_output=True).returncode == 0:
            break

        time.sleep(2)

    run("docker", "logs", CONTAINER, check=True)

    ready_json = run(
        "docker", "exec", CONTAINER, "cat", "ready",
        capture_output=True, text=True, check=True,
    ).stdout
    conn = json.loads(ready_json)["connection_string"]
    print(f"Server is ready. Connection string: {conn}")

    env = {**os.environ, "EXPECTED_VERSION": version}

    if topology == "single":
        mongosh(conn, env, """
            const expected = process.env.EXPECTED_VERSION;
            const im = db.adminCommand({ isMaster: 1 });
            const ver = db.version();
            assert(ver.startsWith(expected),
              "Version mismatch: expected " + expected + ".x, got " + ver);
            assert(!im.setName,
              "Expected standalone, got setName=" + im.setName);
            print("PASS: version=" + ver + ", standalone");
        """)

    elif topology == "replset-3":
        mongosh("mongodb://localhost:27017", env, """
            const expected = process.env.EXPECTED_VERSION;
            const im = db.adminCommand({ isMaster: 1 });
            const ver = db.version();
            assert(ver.startsWith(expected),
              "Version mismatch: expected " + expected + ".x, got " + ver);
            assert(im.setName, "Expected a replica set, got standalone");
            const status = db.adminCommand({ replSetGetStatus: 1 });
            assert(status.members.length === 3,
              "Expected 3 nodes, got " + status.members.length);
            print("PASS: version=" + ver +
              ", replica set \\"" + im.setName + "\\"" +
              ", " + status.members.length + " nodes");
        """)

    elif topology == "sharded-2x3":
        mongosh(conn, env, """
            const expected = process.env.EXPECTED_VERSION;
            const im = db.adminCommand({ isMaster: 1 });
            const ver = db.version();
            assert(ver.startsWith(expected),
              "Version mismatch: expected " + expected + ".x, got " + ver);
            assert(im.msg === "isdbgrid",
              "Expected mongos (isdbgrid), got: " + JSON.stringify(im));
            const listShards = db.adminCommand({ listShards: 1 });
            assert(listShards.shards.length === 2,
              "Expected 2 shards, got " + listShards.shards.length);
            const firstShardHost = listShards.shards[0].host;
            const hostsStr = firstShardHost.includes("/")
              ? firstShardHost.split("/")[1]
              : firstShardHost;
            const nodeCount = hostsStr.split(",").length;
            assert(nodeCount === 3,
              "Expected 3 nodes/shard, got " + nodeCount +
              " (host: " + firstShardHost + ")");
            print("PASS: version=" + ver +
              ", " + listShards.shards.length + " shards" +
              ", " + nodeCount + " nodes/shard");
        """)


def mongosh(conn, env, js):
    run("mongosh", conn, "--eval", js, env=env, check=True)


if __name__ == "__main__":
    main()
