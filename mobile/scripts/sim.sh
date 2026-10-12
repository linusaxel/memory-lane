#!/usr/bin/env bash
# Start the dev build on the booted simulator: a fresh Metro (in the
# foreground, Ctrl-C stops it), the launch, then nothing unlocked.
# --clear because EXPO_PUBLIC values bake into the bundle, and a Metro an
# `./e2e/run.sh --keep` left behind points at the e2e database.
# --walk blanks EXPO_PUBLIC_DEV_LOCATION, so `simctl location` and Maestro's
# setLocation move the dot; with the pin set they are ignored (e2e/run.sh).
set -euo pipefail
[ "${1:-}" = --walk ] && export EXPO_PUBLIC_DEV_LOCATION=
cd "$(dirname "$0")/.."

BUNDLE=com.PLACEHOLDER.memorylane
lsof -ti :8081 | xargs kill 2>/dev/null || true

(
  until curl -s localhost:8081/status | grep -q running; do sleep 1; done
  xcrun simctl spawn booted defaults write "$BUNDLE" RCT_jsLocation localhost:8081
  ./scripts/reset-unlocks.sh # it launches the app last
) &

REACT_NATIVE_PACKAGER_HOSTNAME=localhost exec npx expo start --dev-client --clear
