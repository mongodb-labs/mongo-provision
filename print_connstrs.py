#!/usr/bin/env python3
import json
import sys
from typing import List, Optional, Tuple


def build_hosts(hostname: str, start_port: int, count: int) -> str:
    """
    Build host list like: hostname:start_port,hostname:start_port+1,...
    Returns just the host list (no mongodb:// prefix).
    """
    return ",".join(f"{hostname}:{start_port + i}" for i in range(count))


def is_numeric_string(s: str) -> bool:
    """
    Return True if s is a non-empty string of digits (e.g. "3", "10").
    """
    return isinstance(s, str) and s.isdigit()


def parse_sharded(sharded_field) -> Tuple[bool, Optional[List[str]], Optional[int]]:
    """
    Parse the 'sharded' field.

    Returns:
        (is_sharded, shard_names, shard_count)

        - Non-sharded (replset):
          (False, None, None)

        - Sharded, numeric-string single-element array (e.g. ["3"]):
          (True, None, 3)  # shard_count = 3

        - Sharded, named shards (e.g. ["shardA", "shardB"]):
          (True, ["shardA", "shardB"], 2)

    Raises:
        ValueError if the 'sharded' field has an invalid shape.
    """
    if sharded_field is None:
        return False, None, None

    if not isinstance(sharded_field, list):
        raise ValueError(f"Invalid 'sharded' value (not null or list): {sharded_field!r}")

    if len(sharded_field) == 0:
        raise ValueError("Invalid 'sharded' value: empty array")

    # All members must be strings
    if not all(isinstance(x, str) for x in sharded_field):
        raise ValueError(
            "Invalid 'sharded' value: list must contain only strings "
            f"(got: {sharded_field!r})"
        )

    # Case 1: single numeric-string element → shard count
    if len(sharded_field) == 1 and is_numeric_string(sharded_field[0]):
        shard_count = int(sharded_field[0])
        if shard_count <= 0:
            raise ValueError(f"Invalid shard count in 'sharded': {sharded_field[0]!r}")
        return True, None, shard_count

    # Case 2: array of shard names (strings)
    shard_names = sharded_field
    shard_count = len(shard_names)
    return True, shard_names, shard_count


def main():
    data = json.load(sys.stdin)
    parsed_args = data.get("parsed_args", {})

    hostname = parsed_args.get("hostname", "localhost")
    base_port = int(parsed_args.get("port", 27017))
    nodes = int(parsed_args.get("nodes", 1))
    sharded_field = parsed_args.get("sharded")
    mongos_count = int(parsed_args.get("mongos", 0))

    try:
        is_sharded, shard_names, shard_count = parse_sharded(sharded_field)
    except ValueError as e:
        print(f"Error parsing 'sharded': {e}", file=sys.stderr)
        sys.exit(1)

    # Non-sharded: replica set
    if not is_sharded:
        hosts = build_hosts(hostname, base_port, nodes)
        conn_str = f"mongodb://{hosts}"
        print("Connection string:")
        print(conn_str)
        return

    # Sharded deployment

    # 1. Mongos connection string
    mongos_hosts = build_hosts(hostname, base_port, mongos_count)
    mongos_conn_str = f"mongodb://{mongos_hosts}"
    print("Main connection string:")
    print(f"{mongos_conn_str}")

    print()

    # 2. Shards
    # Shard ports start immediately after the last mongos port.
    shard_base_port = base_port + mongos_count

    # If shard_names is None, then shard_count came from numeric string like ["3"]
    if shard_names is None:
        width = max(2, len(str(shard_count)))
        shard_names = [f"shard{(i + 1):0{width}d}" for i in range(shard_count)]

    # Sanity: shard_count should match len(shard_names)
    if shard_count is None:
        shard_count = len(shard_names)

    print("Per-shard connection strings:")
    for i, shard_name in enumerate(shard_names):
        first_node_port = shard_base_port + i * nodes
        shard_hosts = build_hosts(hostname, first_node_port, nodes)
        shard_conn_str = f"mongodb://{shard_hosts}"
        print(f"{shard_name}: {shard_conn_str}")


if __name__ == "__main__":
    main()
