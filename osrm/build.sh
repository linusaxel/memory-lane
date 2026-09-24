#!/usr/bin/env bash
# Builds the walking graph `docker compose --profile routing up -d osrm` serves.
# Once per map refresh: New York (~150 MB) and Copenhagen (~50 MB) from BBBike,
# merged into one graph because osrm-routed serves one. A few minutes to build.
set -euo pipefail
cd "$(dirname "$0")"

IMAGE=ghcr.io/project-osrm/osrm-backend:v5.27.1
[ -f nyc.osm.pbf ] || curl -fL -o nyc.osm.pbf https://download.bbbike.org/osm/bbbike/NewYork/NewYork.osm.pbf
[ -f cph.osm.pbf ] || curl -fL -o cph.osm.pbf https://download.bbbike.org/osm/bbbike/Copenhagen/Copenhagen.osm.pbf

docker run --rm -v "$PWD:/data" debian:bookworm-slim sh -c \
  "apt-get update -qq && apt-get install -y -qq osmium-tool >/dev/null \
   && osmium merge --overwrite -o /data/streets.osm.pbf /data/nyc.osm.pbf /data/cph.osm.pbf"

run() { docker run --rm -t -v "$PWD:/data" "$IMAGE" "$@"; }
run osrm-extract -p /opt/foot.lua /data/streets.osm.pbf
run osrm-partition /data/streets.osrm
run osrm-customize /data/streets.osrm
