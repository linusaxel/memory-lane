#!/usr/bin/env bash
#
# Watch the user flows happen. See e2e/README.md.
#
#   ./e2e/run.sh              every flow, in order
#   ./e2e/run.sh walk         flows whose file starts "walk-" (.maestro/walk-*.yml)
#   ./e2e/run.sh --record walk  and keep an mp4 of it
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
[ -x venv/bin/python ]        || infra "no venv/bin/python - see AGENTS.md Quick start"
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
  printf '\033[2m     Metro is down: the app icon now opens "No script URL provided".\n'
  printf '     To poke at it: cd mobile && npx expo start --dev-client (or run with --keep)\033[0m\n'
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
  local seed=(--at "$START")
  [ "${1:-}" = lakes ] && seed=(--routes lakes)
  psql_on memorylane "DROP DATABASE IF EXISTS $DB WITH (FORCE)" >/dev/null \
    || infra "could not drop $DB"
  psql_on memorylane "CREATE DATABASE $DB" >/dev/null || infra "could not create $DB"
  docker compose exec -T db psql -q -U memorylane -d "$DB" < db/schema.sql >/dev/null \
    || infra "could not load db/schema.sql into $DB"
  DATABASE_URL="$DB_URL" MEDIA_DIR="$ROOT/media" ROUTING_URL="$ROUTING" \
    venv/bin/python -m pipeline.seed_dev "${seed[@]}" > "$LOGS/seed.log" 2>&1
  local seeded=$?
  [ "$seeded" = 3 ] && return 3
  [ "$seeded" = 0 ] || { cat "$LOGS/seed.log" >&2; exit 1; }
  # The 4 km default is four stops, and the route is seeded on device, so with
  # five in reach travel.py's device and the app's pick different fours. Four
  # in reach leaves nothing to pick. No flow names the bridge.
  [ "${1:-}" = lakes ] || psql_on "$DB" "DELETE FROM places WHERE name = 'Nørrebrogade bridge, dev seed'" >/dev/null \
    || infra "could not drop the bridge from $DB"
}

# F27's streak needs a walk stop unlocked yesterday, by a device id the app has
# not minted yet. So whichever device turns up first is given a one-stop walk
# yesterday and its unlock, of a memory at 0,0: never a route candidate, never
# on screen, and no stop's date moves.
yesterday_unlock() {
  psql_on "$DB" "
    WITH p AS (INSERT INTO places (name, place_query, coordinates)
               VALUES ('Yesterday', 'e2e yesterday', ST_MakePoint(0, 0)::geography) RETURNING id)
    INSERT INTO memories (place_id, content_id, summary)
      SELECT p.id, (SELECT id FROM content LIMIT 1), 'Unlocked yesterday.' FROM p;
    CREATE FUNCTION yesterday() RETURNS trigger AS \$\$ BEGIN
      INSERT INTO unlocks (device_id, memory_id, unlocked_at)
        SELECT NEW.id, m.id, now() - interval '1 day' FROM memories m
        JOIN places p ON p.id = m.place_id WHERE p.place_query = 'e2e yesterday';
      INSERT INTO daily_routes (device_id, route_date, memory_ids)
        SELECT NEW.id, (now() - interval '1 day')::date, ARRAY[m.id] FROM memories m
        JOIN places p ON p.id = m.place_id WHERE p.place_query = 'e2e yesterday';
      RETURN NEW;
    END \$\$ LANGUAGE plpgsql;
    CREATE TRIGGER yesterday AFTER INSERT ON devices FOR EACH ROW EXECUTE FUNCTION yesterday();
  " >/dev/null || infra "could not seed yesterday's unlock into $DB"
}

# F31's history for lakes-loop, the same way: whichever device turns up first
# walked the south end three days ago (5 of 5) and gave up two days ago (2 of
# 5; the two it had already earned). A device turns up on Accept, so the
# preview before it is planned without this history.
past_walks() {
  psql_on "$DB" "
    CREATE FUNCTION past_walks() RETURNS trigger AS \$\$
    DECLARE
      walked int[] := ARRAY(SELECT m.id FROM unnest(ARRAY['Sortedams Sø 4', 'Peblinge Sø 5',
          'Sankt Jørgens Sø 6', 'Sankt Jørgens Sø 7', 'Sankt Jørgens Sø 8']) WITH ORDINALITY n(name, i)
        JOIN places p ON p.name = n.name || ', dev seed' JOIN memories m ON m.place_id = p.id ORDER BY n.i);
      abandoned int[] := ARRAY(SELECT m.id FROM unnest(ARRAY['Peblinge Sø 5', 'Sortedams Sø 4',
          'Sortedams Sø 3', 'Sortedams Sø 2', 'Sortedams Sø 1']) WITH ORDINALITY n(name, i)
        JOIN places p ON p.name = n.name || ', dev seed' JOIN memories m ON m.place_id = p.id ORDER BY n.i);
    BEGIN
      INSERT INTO unlocks (device_id, memory_id, unlocked_at)
        SELECT NEW.id, unnest(walked), now() - interval '3 days';
      INSERT INTO daily_routes (device_id, route_date, memory_ids, completed_at) VALUES
        (NEW.id, (now() - interval '3 days')::date, walked, now() - interval '3 days'),
        (NEW.id, (now() - interval '2 days')::date, abandoned, NULL);
      RETURN NEW;
    END \$\$ LANGUAGE plpgsql;
    CREATE TRIGGER past_walks AFTER INSERT ON devices FOR EACH ROW EXECUTE FUNCTION past_walks();
  " >/dev/null || infra "could not seed past walks into $DB"
}

# subscribe-from-the-peek needs a paid-up account with no store. The app
# mints its account when a name is typed in You, so whichever user turns up
# first is given a month (the seed's own user was inserted before this).
subscriber() {
  psql_on "$DB" "
    CREATE FUNCTION subscriber() RETURNS trigger AS \$\$ BEGIN
      INSERT INTO subscriptions (user_id, expires_at) VALUES (NEW.id, now() + interval '30 days');
      RETURN NEW;
    END \$\$ LANGUAGE plpgsql;
    CREATE TRIGGER subscriber AFTER INSERT ON users FOR EACH ROW EXECUTE FUNCTION subscriber();
  " >/dev/null || infra "could not seed a subscriber into $DB"
}

# A walkable point in central Copenhagen, different every run. The seed is
# planted round it and the journeys start there, so the app is driven from
# somewhere nobody chose. E2E_START=lat,lng replays one.
random_start() {
  venv/bin/python -c 'import json, random
p = random.choice(json.load(open("pipeline/cph_ways.json")))
print(f"{p[0]},{p[1]}")'
}

say "1/5  database"
docker compose up -d db >/dev/null 2>&1 || infra "docker compose up -d db failed"
for _ in $(seq 30); do
  docker compose exec -T db pg_isready -U memorylane >/dev/null 2>&1 && break
  sleep 1
done
docker compose exec -T db pg_isready -U memorylane >/dev/null 2>&1 \
  || infra "postgres never became ready"

# Streets, as a person gets them: the flows name stops in the order OSRM walks
# them and travel along its street shapes, and the 20m gate drops any pin a
# street cannot reach. Without the sidecar that is a different app.
ROUTING="${E2E_ROUTING_URL:-http://localhost:5001}"
curl -fsS -m 3 "$ROUTING/nearest/v1/foot/12.57586,55.67886" >/dev/null 2>&1 \
  || infra "no OSRM at $ROUTING - ./osrm/build.sh once, then docker compose --profile routing up -d osrm"

# Some starts cannot carry the walk journey (a stop lands in the start's gate,
# or the stack comes first); seed_dev and travel.py exit 3 and we roll again.
for _ in $(seq 20); do
  START="${E2E_START:-$(random_start)}"
  if ! reset_database; then
    [ -n "${E2E_START:-}" ] && { cat "$LOGS/seed.log" >&2; exit 1; }
    START=
    continue
  fi
  PYTHONPATH="$ROOT" DATABASE_URL="$DB_URL" ROUTING_URL="$ROUTING" venv/bin/python e2e/travel.py "$START" \
    > "$LOGS/travel.log" 2>&1
  case $? in
    0) break ;;
    3) [ -n "${E2E_START:-}" ] && { cat "$LOGS/travel.log" >&2; exit 1; }; START= ;;
    *) cat "$LOGS/travel.log" >&2; exit 1 ;;
  esac
done
[ -z "$START" ] && infra "twenty random starts in a row could not carry the walk journey"
ENV_ARGS=(--env APP_ID="$APP_ID" --env START_LAT="${START%,*}" --env START_LNG="${START#*,}")
while IFS= read -r line; do ENV_ARGS+=(--env "$line"); done < "$OUT/legs/env"
echo "     seeded $DB round $START (E2E_START=$START replays it)"
echo "     walk: $(tail -1 "$LOGS/travel.log")"

# ---------------------------------------------------------------- api

# Free the port first, exactly as the Metro step does. Skipping this is not a
# tidy-up detail: an API left behind by --keep goes on answering on :8090 with
# ITS database, the health check below is satisfied by the impostor, and the
# run seeds a fresh database that nothing ever reads. The symptom is an app
# that looks broken - a memory 300m away rendering as already collected -
# which costs an afternoon before anybody suspects the port.
say "2/5  api on :$API_PORT"
kill_port "$API_PORT"
DATABASE_URL="$DB_URL" MEDIA_DIR="$ROOT/media" ROUTING_URL="$ROUTING" SCREEN_POSTS=0 \
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
# A new native module (a pod) is invisible to Metro: the installed binary runs
# the new JS and dies on the missing module. So a Podfile.lock that differs
# from the one last built is a rebuild.
BUILT_LOCK=mobile/ios/build/Podfile.lock.built
cmp -s mobile/ios/Podfile.lock "$BUILT_LOCK" || BUILD=1
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
  cp mobile/ios/Podfile.lock "$BUILT_LOCK"
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
  reset_database "${name%%-*}"
  [ "$name" = walk-and-unlock ] && yesterday_unlock
  [ "$name" = lakes-loop ] && past_walks
  [ "$name" = subscribe-from-the-peek ] && subscriber
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
  "$MAESTRO" test --device "$DEVICE" "${ENV_ARGS[@]}" "$flow" &
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
