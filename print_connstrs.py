#!/usr/bin/env python3
import json
import sys
from typing import List, Optional, Tuple, Dict, Any


def build_hosts(hostname: str, start_port: int, count: int) -> str:
    """
    Build host list like: hostname:start_port,hostname:start_port+1,...
    """
    return ",".join(f"{hostname}:{start_port + i}" for i in range(count))


def is_numeric_string(s: str) -> bool:
    """
    Return True if s is a non-empty string of digits.
    """
    return isinstance(s, str) and s.isdigit()


def parse_sharded(sharded_field) -> Tuple[bool, Optional[List[str]], Optional[int]]:
    """
    Parse the 'sharded' field. Returns (is_sharded, shard_names, shard_count).
    """
    if sharded_field is None:
        return False, None, None

    if not isinstance(sharded_field, list):
        raise ValueError(f"Invalid 'sharded' value (not null or list): {sharded_field!r}")

    if len(sharded_field) == 0:
        raise ValueError("Invalid 'sharded' value: empty array")

    if not all(isinstance(x, str) for x in sharded_field):
        raise ValueError("Invalid 'sharded' value: list must contain only strings")

    if len(sharded_field) == 1 and is_numeric_string(sharded_field[0]):
        shard_count = int(sharded_field[0])
        if shard_count <= 0:
            raise ValueError(f"Invalid shard count: {sharded_field[0]!r}")
        return True, None, shard_count

    shard_names = sharded_field
    shard_count = len(shard_names)
    return True, shard_names, shard_count


def main():
    # Check for --json flag
    use_json = "--json" in sys.argv

    try:
        data = json.load(sys.stdin)
    except json.JSONDecodeError:
        print("Error: Input is not valid JSON", file=sys.stderr)
        sys.exit(1)

    parsed_args = data.get("parsed_args", {})
    hostname = parsed_args.get("hostname", "localhost")
    base_port = int(parsed_args.get("port", 27017))
    sharded_field = parsed_args.get("sharded")
    mongos_count = int(parsed_args.get("mongos", 0))

    if bool(parsed_args.get("single")):
        nodes = 1
    else:
        nodes = int(parsed_args.get("nodes", 1))

    try:
        is_sharded, shard_names, shard_count = parse_sharded(sharded_field)
    except ValueError as e:
        print(f"Error parsing 'sharded': {e}", file=sys.stderr)
        sys.exit(1)

    result: Dict[str, Any] = {}

    # Logic for Replica Set (Non-sharded)
    if not is_sharded:
        hosts = build_hosts(hostname, base_port, nodes)
        conn_str = f"mongodb://{hosts}"
        if use_json:
            print(json.dumps({"connection_string": conn_str}, indent=2))
        else:
            print(f"Connection string:\n{conn_str}")
        return

    # Logic for Sharded Deployment
    mongos_hosts = build_hosts(hostname, base_port, mongos_count)
    mongos_conn_str = f"mongodb://{mongos_hosts}"

    result["connection_string"] = mongos_conn_str
    result["shards"] = {}

    shard_base_port = base_port + mongos_count
    if shard_names is None:
        width = max(2, len(str(shard_count)))
        shard_names = [f"shard{(i + 1):0{width}d}" for i in range(shard_count or 0)]

    for i, shard_name in enumerate(shard_names):
        first_node_port = shard_base_port + i * nodes
        shard_hosts = build_hosts(hostname, first_node_port, nodes)
        result["shards"][shard_name] = f"mongodb://{shard_hosts}"

    # Output handling
    if use_json:
        print(json.dumps(result, indent=2))
    else:
        print(f"Main connection string:\n{result['main_connection_string']}\n")
        print("Per-shard connection strings:")
        for name, conn in result["shards"].items():
            print(f"{name}: {conn}")


if __name__ == "__main__":
    main()
