#!/usr/bin/env bash
# A screenshot of every screen of the running dev build: no Maestro, no taps.
# Each is asked for in a file the app polls (devWatch in src/devOpen.ts).
# Needs scripts/sim.sh running and the dev API up.
#
#   scripts/shoot.sh                  every screen, into ~/Downloads/memory-lane-shots/
#   scripts/shoot.sh paywall walk     just those
#
# Names and order: SCREENS in src/devOpen.ts. walk, end-confirm and done take
# the walk preview planned, so they want preview shot first.
set -euo pipefail
cd "$(dirname "$0")/.."

OUT=~/Downloads/memory-lane-shots
mkdir -p "$OUT"
BUNDLE=com.PLACEHOLDER.memorylane
ASK="$(xcrun simctl get_app_container booted "$BUNDLE" data)/Documents/dev-screen"
if [ $# -gt 0 ]; then
  SCREENS=("$@")
else
  # Read from devOpen.ts so the list cannot drift.
  SCREENS=($(sed -n '/^export const SCREENS/,/] as const/p' src/devOpen.ts | grep -o "'[a-z0-9-]*'" | tr -d "'"))
fi

started=$(date +%s)
for screen in "${SCREENS[@]}"; do
  # What a screen waits on: the API for a plan or the past walks, a sheet's slide.
  case "$screen" in
    preview) wait=6 ;;
    past | journal*) wait=3 ;;
    *) wait=1.5 ;;
  esac
  echo "screen=$screen&n=$RANDOM$RANDOM" >"$ASK"
  sleep "$wait"
  xcrun simctl io booted screenshot "$OUT/$screen.png" >/dev/null 2>&1
  echo "$OUT/$screen.png"
done
echo "${#SCREENS[@]} screens in $(($(date +%s) - started))s"
