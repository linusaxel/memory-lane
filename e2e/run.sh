#!/usr/bin/env bash
#
# Watch the user flows happen. See e2e/README.md.
#
#   ./e2e/run.sh              every flow, in order
#   ./e2e/run.sh f7           just the unlock
#   ./e2e/run.sh --record f7  and keep an mp4 of it
#
# Exit codes follow loop/verify.sh: 0 pass, 1 a flow failed, 2 the environment
# needs a human.

set -uo pipefail
cd "$(dirname "$0")/.."
ROOT=$(pwd)

# Per-process, for the same reason tests/conftest.py suffixes its own: two
# runs sharing one Postgres is normal (two sessions on the repo, or a run you
# forgot you backgrounded), and with a fixed name one run's teardown DROPs the
# database the other is halfway through loading. The failure surfaces as
# "server closed the connection unexpectedly" nowhere near the cause.
DB=memorylane_e2e_$$
DB_URL="postgresql://memorylane:memorylane@localhost:5432/$DB"
API_PORT=8090
METRO_PORT=8081
OUT="$ROOT/e2e/out"
# Long enough for the slowest flow on a busy machine (f15 has taken 86s under
# load), short enough that a wedged driver is noticed rather than waited on.
FLOW_TIMEOUT=${E2E_FLOW_TIMEOUT:-300}
LOGS="$OUT/logs"

RECORD=0
BUILD=0
KEEP=0
FLOWS=()

for arg in "$@"; do
  case "$arg" in
    --record) RECORD=1 ;;
    --build)  BUILD=1 ;;
    --keep)   KEEP=1 ;;
    -*)       echo "unknown option: $arg" >&2; exit 2 ;;
    *)        FLOWS+=("$arg") ;;
  esac
done

STARTED=$(date +%s)
LAST=$STARTED

# Every phase prints what it cost. You cannot speed up a loop you cannot see,
# and this one is run dozens of times an hour while iterating.
say() {
  local now took
  now=$(date +%s)
  took=$((now - LAST))
  LAST=$now
  if [ "$took" -gt 0 ]; then
    printf '\n\033[1m%s\033[0m \033[2m(+%ss)\033[0m\n' "$*" "$took"
  else
    printf '\n\033[1m%s\033[0m\n' "$*"
  fi
}
infra() { printf '\033[33mINFRA\033[0m %s\n' "$*" >&2; exit 2; }

# ---------------------------------------------------------------- preflight

MAESTRO=$(command -v maestro || true)
[ -z "$MAESTRO" ] && [ -x "$HOME/.maestro/bin/maestro" ] && MAESTRO="$HOME/.maestro/bin/maestro"
[ -z "$MAESTRO" ] && infra "maestro not found. curl -fsSL https://get.maestro.mobile.dev | bash"

command -v xcrun >/dev/null   || infra "no xcrun - Xcode command line tools are not installed"
[ -x venv/bin/python ]        || infra "no venv/bin/python - see CLAUDE.md Quick Start"
docker info >/dev/null 2>&1   || infra "docker is not running"
[ -d mobile/node_modules ]    || infra "mobile/node_modules is missing - cd mobile && npm ci"

APP_ID=$(venv/bin/python -c \
  "import json; print(json.load(open('mobile/app.json'))['expo']['ios']['bundleIdentifier'])") \
  || infra "could not read the bundle id out of mobile/app.json"

# A simulator on the NEWEST installed runtime, because Xcode 26 refuses to
# build against iOS 18.3 (loop/TASKS.yaml W3-12 hit this too). Override with
# E2E_DEVICE=<udid> to watch it on a different one.
DEVICE=${E2E_DEVICE:-$(venv/bin/python - <<'PICK'
import json, subprocess
out = json.loads(subprocess.run(
    ["xcrun", "simctl", "list", "devices", "available", "-j"],
    capture_output=True, text=True).stdout)["devices"]


def version(runtime):
    return [int(n) for n in runtime.split("iOS-")[-1].split("-")] if "iOS-" in runtime else [0]


for runtime in sorted((r for r in out if "iOS-" in r), key=version, reverse=True):
    phones = [d for d in out[runtime] if d["name"].startswith("iPhone")]
    if phones:
        print(sorted(phones, key=lambda d: not d.get("state") == "Booted")[0]["udid"])
        break
PICK
)}
[ -z "$DEVICE" ] && infra "no iPhone simulator available - open Xcode once, or set E2E_DEVICE"
xcrun simctl bootstatus "$DEVICE" -b >/dev/null 2>&1 || xcrun simctl boot "$DEVICE" 2>/dev/null
open -a Simulator --args -CurrentDeviceUDID "$DEVICE" 2>/dev/null

mkdir -p "$LOGS"

# A recording interrupted mid-write leaves a partial behind under its own
# sandbox name, and it is the size of however long it ran - one killed run left
# 210MB. They are never picked up again, so they go at the start of the next.
rm -f "$OUT"/*.sb-* 2>/dev/null

# ---------------------------------------------------------------- teardown

API_PID=""
REC_PID=""

kill_port() {
  local pids
  pids=$(lsof -ti:"$1" 2>/dev/null)
  [ -n "$pids" ] && kill -9 $pids 2>/dev/null
  return 0
}

psql_on() {
  docker compose exec -T db psql -U memorylane -d "$1" -c "$2"
}

cleanup() {
  [ -n "$REC_PID" ] && kill -INT "$REC_PID" 2>/dev/null && wait "$REC_PID" 2>/dev/null
  if [ "$KEEP" = 1 ]; then
    say "--keep: API on :$API_PORT, Metro on :$METRO_PORT and $DB are still up"
    return
  fi
  [ -n "$API_PID" ] && kill "$API_PID" 2>/dev/null
  kill_port "$METRO_PORT"
  psql_on memorylane "DROP DATABASE IF EXISTS $DB WITH (FORCE)" >/dev/null 2>&1
}
trap cleanup EXIT

# ---------------------------------------------------------------- database
# Its own database, built from db/schema.sql exactly as tests/conftest.py does.
# Every run starts identical, and the extracted corpus in `memorylane` is never
# touched - re-extracting it costs real money.

# Rebuilt before EVERY flow, not once per run.
#
# Two things outlive an app relaunch and would otherwise leak between flows.
# The database is obvious. The device id is not: it lives in the keychain
# (expo-secure-store), which `clearState: true` does not touch - by design, so
# a collection survives clearing app data. So f15 unlocking "the bench
# outside" left f7 opening a memory it was supposed to have to walk to.
# Dropping the database takes the unlocks with it and the device becomes a
# stranger again.
reset_database() {
  psql_on memorylane "DROP DATABASE IF EXISTS $DB WITH (FORCE)" >/dev/null \
    || infra "could not drop $DB"
  psql_on memorylane "CREATE DATABASE $DB" >/dev/null || infra "could not create $DB"
  docker compose exec -T db psql -q -U memorylane -d "$DB" < db/schema.sql >/dev/null \
    || infra "could not load db/schema.sql into $DB"
  DATABASE_URL="$DB_URL" MEDIA_DIR="$ROOT/media" venv/bin/python -m pipeline.seed_dev \
    > "$LOGS/seed.log" 2>&1 || { cat "$LOGS/seed.log" >&2; exit 1; }
}

say "1/5  database"
docker compose up -d db >/dev/null 2>&1 || infra "docker compose up -d db failed"
for _ in $(seq 30); do
  docker compose exec -T db pg_isready -U memorylane >/dev/null 2>&1 && break
  sleep 1
done
docker compose exec -T db pg_isready -U memorylane >/dev/null 2>&1 \
  || infra "postgres never became ready"

reset_database
echo "     seeded $DB"

# ---------------------------------------------------------------- api

# Free the port first, exactly as the Metro step does. Skipping this is not a
# tidy-up detail: an API left behind by --keep goes on answering on :8090 with
# ITS database, the health check below is satisfied by the impostor, and the
# run seeds a fresh database that nothing ever reads. The symptom is an app
# that looks broken - a memory 300m away rendering as already collected -
# which costs an afternoon before anybody suspects the port.
say "2/5  api on :$API_PORT"
kill_port "$API_PORT"
DATABASE_URL="$DB_URL" MEDIA_DIR="$ROOT/media" \
  venv/bin/python -m uvicorn api.main:app --port "$API_PORT" > "$LOGS/api.log" 2>&1 &
API_PID=$!
for _ in $(seq 30); do
  curl -fsS "http://localhost:$API_PORT/" >/dev/null 2>&1 && break
  sleep 1
done
curl -fsS "http://localhost:$API_PORT/" >/dev/null 2>&1 \
  || { cat "$LOGS/api.log" >&2; infra "the api never answered on :$API_PORT"; }

# ---------------------------------------------------------------- app

#
# xcodebuild rather than `npx expo run:ios`: with any physical iPhone paired to
# this Mac, the Expo CLI resolves the simulator UDID correctly and then takes
# the physical-device branch anyway, and dies asking for a signing certificate.
# A simulator build needs no signing, so we drive it ourselves. `npx expo
# prebuild` and pod install are still Expo's job - this only compiles what is
# already in mobile/ios.

say "3/5  app"
if [ "$BUILD" = 1 ] || ! xcrun simctl get_app_container "$DEVICE" "$APP_ID" >/dev/null 2>&1; then
  echo "     building $APP_ID (several minutes)"
  (cd mobile/ios && xcodebuild \
      -workspace MemoryLane.xcworkspace -scheme MemoryLane \
      -configuration Debug -sdk iphonesimulator \
      -destination "id=$DEVICE" -derivedDataPath build build) > "$LOGS/build.log" 2>&1 \
    || { tail -40 "$LOGS/build.log" >&2; infra "xcodebuild failed"; }
  APP=$(find mobile/ios/build/Build/Products -maxdepth 2 -name "MemoryLane.app" | head -1)
  [ -z "$APP" ] && infra "the build produced no MemoryLane.app"
  xcrun simctl install "$DEVICE" "$APP" || infra "could not install $APP"
  echo "     installed"
else
  echo "     $APP_ID already installed"
fi

# ---------------------------------------------------------------- metro
#
# EXPO_PUBLIC_DEV_LOCATION must be BLANK and that is the load-bearing line here.
# When it is set, goToMyLocation takes the pinned coordinate and never starts
# watchPositionAsync - so the simulator's location has no effect on the app at
# all and walking cannot be simulated. Blank is falsy in devLocation(), and
# Expo's dotenv does not override an already-set variable, so this beats
# mobile/.env without editing it.

say "4/5  metro on :$METRO_PORT"
kill_port "$METRO_PORT"
# Discovered rather than listed. Every EXPO_PUBLIC_DEV_* knob is something
# that makes the app skip a step for a human looking at it, and each one is a
# step these flows are here to drive. They arrive faster than a hand-written
# list gets updated - DEV_OPEN_MEMORY and DEV_OPEN_SCREEN both appeared while
# this file was being written - so the list is read off the env files instead.
BLANK_KNOBS=$(grep -hoE '^EXPO_PUBLIC_DEV_[A-Z_]+' mobile/.env mobile/.env.example 2>/dev/null \
  | sort -u | sed 's/$/=/')
echo "     neutralising: $(echo $BLANK_KNOBS)"

(cd mobile && env $BLANK_KNOBS \
  EXPO_PUBLIC_API_URL="http://localhost:$API_PORT" \
  npx expo start --dev-client --port "$METRO_PORT") > "$LOGS/metro.log" 2>&1 &
for _ in $(seq 60); do
  curl -fsS "http://localhost:$METRO_PORT/status" 2>/dev/null | grep -q running && break
  sleep 1
done
curl -fsS "http://localhost:$METRO_PORT/status" 2>/dev/null | grep -q running \
  || { tail -20 "$LOGS/metro.log" >&2; infra "metro never came up on :$METRO_PORT"; }

# ---------------------------------------------------------------- flows

if [ ${#FLOWS[@]} -eq 0 ]; then
  SELECTED=()
  for flow in $(ls .maestro/*.yml | sort); do SELECTED+=("$flow"); done
else
  SELECTED=()
  for name in "${FLOWS[@]}"; do
    match=$(ls .maestro/"$name"-*.yml 2>/dev/null | head -1)
    [ -z "$match" ] && { echo "no flow matches '$name' in .maestro/" >&2; exit 2; }
    SELECTED+=("$match")
  done
fi

say "5/5  ${#SELECTED[@]} flow(s)"
if [ "$RECORD" = 1 ] && [ ${#SELECTED[@]} -gt 1 ]; then
  # Measured, not cautious: without --record this suite passes 6/6 run after
  # run; with it, three of the six fail and a different three each time. The
  # recorder is what is unstable, not the flows. See e2e/README.md.
  printf '\033[33m     warning\033[0m recording several flows is flaky - prefer --record <one flow>\n'
fi
FAIL=0
for flow in "${SELECTED[@]}"; do
  name=$(basename "$flow" .yml)
  flow_started=$(date +%s)
  printf '\n\033[1m  ▸ %s\033[0m\n' "$name"
  reset_database
  # launchApp's own relaunch has been seen to no-op under the load of a screen
  # recording, which leaves the flow looking at the previous one's last screen
  # and failing on its first assertion. Killing it first makes every flow a
  # cold start.
  xcrun simctl terminate "$DEVICE" "$APP_ID" >/dev/null 2>&1

  # And clearing its storage by hand, because `launchApp: clearState: true`
  # does not reliably take AsyncStorage with it. Caught by f7: the collection
  # from an earlier flow survived, so a memory that should have been a padlock
  # 300m away rendered as one already in the collection, and the flow failed
  # describing a bug that was not there. The keychain is deliberately left
  # alone - a device id survives cleared app data on a real phone too, and the
  # fresh database makes it a stranger anyway.
  DATA=$(xcrun simctl get_app_container "$DEVICE" "$APP_ID" data 2>/dev/null)
  [ -n "$DATA" ] && rm -rf "$DATA/Library/Application Support/$APP_ID/RCTAsyncLocalStorage_V1"

  if [ "$RECORD" = 1 ]; then
    rm -f "$OUT/$name.mp4"
    xcrun simctl io "$DEVICE" recordVideo --codec h264 -f "$OUT/$name.mp4" \
      > "$LOGS/$name.record.log" 2>&1 &
    REC_PID=$!
    sleep 2
  fi

  # Under a watchdog, because a wedged driver does not fail - it stops.
  #
  # After a long session Maestro's XCTest driver can start answering
  # "Request for viewHierarchy failed, code: 500" and then `maestro test`
  # simply never returns. Three runs died that way tonight, each hanging until
  # something noticed, which is the worst possible shape for a feedback loop:
  # no result, no error, and no end. A flow that has not finished in
  # FLOW_TIMEOUT is not going to.
  #
  # macOS ships no `timeout`, hence the poll.
  "$MAESTRO" test --device "$DEVICE" --env APP_ID="$APP_ID" "$flow" &
  maestro_pid=$!
  waited=0
  while kill -0 "$maestro_pid" 2>/dev/null; do
    if [ "$waited" -ge "$FLOW_TIMEOUT" ]; then
      printf '\033[31m     giving up after %ss - the driver stopped answering\033[0m\n' "$FLOW_TIMEOUT"
      printf '\033[2m     see "When the driver wedges" in e2e/README.md\033[0m\n'
      kill -9 "$maestro_pid" 2>/dev/null
      pkill -f "xcodebuild test-without-building" 2>/dev/null
      FAIL=1
      break
    fi
    sleep 2
    waited=$((waited + 2))
  done
  wait "$maestro_pid" 2>/dev/null || FAIL=1
  printf '\033[2m     %ss\033[0m\n' "$(( $(date +%s) - flow_started ))"
  LAST=$(date +%s)

  if [ -n "$REC_PID" ]; then
    kill -INT "$REC_PID" 2>/dev/null
    wait "$REC_PID" 2>/dev/null
    REC_PID=""
    echo "     recorded e2e/out/$name.mp4"
  fi
done

TOTAL=$(( $(date +%s) - STARTED ))
if [ "$FAIL" = 0 ]; then
  printf '\n\033[32mE2E=PASS\033[0m  %s flow(s) in %ss\n' "${#SELECTED[@]}" "$TOTAL"
else
  printf '\n\033[31mE2E=FAIL\033[0m  %s flow(s) in %ss - see %s\n' "${#SELECTED[@]}" "$TOTAL" "$LOGS"
fi
exit "$FAIL"
