#!/usr/bin/env bash
# Builds the walking graph `docker compose --profile routing up -d osrm` serves.
# Once per map refresh: Copenhagen (~50 MB) from BBBike, the only city the
# app and its tests walk in. New York was merged in until 2026-09-24 and held
# most of the ~3 GB. A few minutes to build.
set -euo pipefail
cd "$(dirname "$0")"

IMAGE=ghcr.io/project-osrm/osrm-backend:v5.27.1
[ -f cph.osm.pbf ] || curl -fL -o cph.osm.pbf https://download.bbbike.org/osm/bbbike/Copenhagen/Copenhagen.osm.pbf
cp cph.osm.pbf streets.osm.pbf

run() { docker run --rm -t -v "$PWD:/data" "$IMAGE" "$@"; }
run osrm-extract -p /opt/foot.lua /data/streets.osm.pbf
run osrm-partition /data/streets.osrm
run osrm-customize /data/streets.osrm
