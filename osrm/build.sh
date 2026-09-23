#!/usr/bin/env bash
# Builds the walking graph `docker compose --profile routing up -d osrm` serves.
# Once per map refresh: ~150 MB of New York from BBBike, a few minutes to build.
set -euo pipefail
cd "$(dirname "$0")"

IMAGE=ghcr.io/project-osrm/osrm-backend:v5.27.1
[ -f nyc.osm.pbf ] || curl -fL -o nyc.osm.pbf https://download.bbbike.org/osm/bbbike/NewYork/NewYork.osm.pbf

run() { docker run --rm -t -v "$PWD:/data" "$IMAGE" "$@"; }
run osrm-extract -p /opt/foot.lua /data/nyc.osm.pbf
run osrm-partition /data/nyc.osrm
run osrm-customize /data/nyc.osrm
