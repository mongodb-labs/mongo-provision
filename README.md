# Mongo Provision

This tool provisions a MongoDB cluster for testing. All nodes of the cluster
run in a single container.

## Example Usage
```
# Build the container:
docker build . -t mongo-provision

# Start a 3-node replica set:
docker run -it --rm -p27017-27019:27017-27019 mongo-provision 8.0 --replicaset --nodes 3

# … or, for a sharded cluster:
docker run -it --rm -p27017:27017 mongo-provision 8.0 --replicaset --sharded 3 --nodes 3
```
The above will hang indefinitely until you kill it, e.g., via CTRL-C.

Then, in another terminal, run:
```
# for the replset:
mongosh mongodb://localhost:27017,localhost:27018,localhost:27019

# … or, for sharded:
mongosh mongodb://localhost:27017
```
… and you’re in!

## Syntax
The arguments to the container are:
- a version number, e.g., `8.0`
- args such as you’d give to [mtools](https://github.com/rueckstiess/mtools)’s
`init` subcommand.

## Caveats
- You **MUST** anticipate the bound ports and export them.
- The container’s platform will dictate server version availability. For example,
  you can’t create pre-v5 clusters on Linux/ARM64 because no official builds were
  made for that version/platform combination.

## Acknowledgements

Besides [mtools](https://github.com/rueckstiess/mtools), this uses
[m](https://github.com/aheckmann/m) to download MongoDB releases.
