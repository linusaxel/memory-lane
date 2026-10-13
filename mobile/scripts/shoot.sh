#!/usr/bin/env bash
# A screenshot of every screen of the running dev build: no Maestro, no taps.
# Each is asked for in a file the app polls (useDevScreen in src/devOpen.ts).
# Needs scripts/sim.sh running and the dev API up.
#
#   scripts/shoot.sh                  every screen, into ~/Downloads/memory-lane-shots/
#   scripts/shoot.sh paywall walk     just those
#
# Names and order: SCREENS in src/devOpen.ts, after `startup`, which relaunches
# the app. What comes after preview builds on the walk it planned.
#
# The memory- screens want a memory that has what they show: a quote, a
# Wikipedia link, notes, an author to block. This picks one each from the dev
# database and unlocks it for the simulator's device, the rows
# scripts/reset-unlocks.sh takes away again.
set -euo pipefail
cd "$(dirname "$0")/.."

# Without Metro every shot is the home screen, and it still says it took them:
# e2e/run.sh stops Metro when it ends.
if ! lsof -ti :8081 >/dev/null; then
  echo "Metro is down: start scripts/sim.sh first." >&2
  exit 2
fi

OUT=~/Downloads/memory-lane-shots
mkdir -p "$OUT"
BUNDLE=com.PLACEHOLDER.memorylane
ASK="$(xcrun simctl get_app_container booted "$BUNDLE" data)/Documents/dev-screen"
if [ $# -gt 0 ]; then
  SCREENS=("$@")
else
  rm -f "$OUT"/*.png
  # Read from devOpen.ts so the list cannot drift.
  SCREENS=(startup $(sed -n '/^export const SCREENS/,/] as const/p' src/devOpen.ts | grep -o "'[a-z0-9-]*'" | tr -d "'"))
fi

sql() { (cd .. && docker compose exec -T db psql -U memorylane -v ON_ERROR_STOP=1 -tAc "$1"); }
ME="WITH me AS (SELECT id, user_id FROM devices ORDER BY last_seen DESC NULLS LAST LIMIT 1)"
pick() { sql "$ME SELECT m.id FROM memories m, me WHERE NOT m.hidden AND m.user_id IS DISTINCT FROM me.user_id AND $1 ORDER BY m.walk_score DESC NULLS LAST LIMIT 1"; }
OPEN=$(pick "m.enrichment ? 'pictures' AND m.contrast_note IS NOT NULL")
QUOTE=$(pick "m.quote IS NOT NULL")
WIKI=$(pick "m.links::text LIKE '%wikipedia.org%'")
NOTES=$(pick "m.id IN (SELECT memory_id FROM memory_notes WHERE NOT hidden GROUP BY memory_id)")
BLOCK=$(pick "m.user_id IS NOT NULL")
sql "$ME INSERT INTO unlocks (device_id, memory_id) SELECT me.id, m FROM me,
  unnest(ARRAY[$OPEN, $QUOTE, $WIKI, $NOTES, $BLOCK]) m ON CONFLICT DO NOTHING" >/dev/null

started=$(date +%s)
for screen in "${SCREENS[@]}"; do
  memory=
  case "$screen" in
    memory-open | memory-report | notes-*) memory=$OPEN ;;
    memory-quote) memory=$QUOTE ;;
    memory-wiki) memory=$WIKI ;;
    memory-notes) memory=$NOTES ;;
    memory-block) memory=$BLOCK ;;
  esac
  # What a screen waits on: the API for a plan, a memory or the past walks, a
  # sheet's slide, the seal's fall.
  case "$screen" in
    preview | plan-walk* | plan-long* | plan-ends-here | plan-unreachable | customize*) wait=6 ;;
    preview-customized | offline-plan) wait=4 ;;
    memory-* | notes-* | past | journal* | collector* | rank-up | submit-editor | submit-delete) wait=3 ;;
    settings-lower) wait=2.5 ;;
    seal-first) wait=2.2 ;;
    *) wait=1.5 ;;
  esac
  if [ "$screen" = startup ]; then
    xcrun simctl terminate booted "$BUNDLE" 2>/dev/null || true
    xcrun simctl launch booted "$BUNDLE" >/dev/null
    sleep 0.8
    xcrun simctl io booted screenshot "$OUT/$screen.png" >/dev/null 2>&1
    echo "$OUT/$screen.png"
    sleep 6 # the bundle loads and the map settles before the next one is asked for
    continue
  fi
  echo "screen=$screen&memory=$memory&n=$RANDOM$RANDOM" >"$ASK"
  sleep "$wait"
  xcrun simctl io booted screenshot "$OUT/$screen.png" >/dev/null 2>&1
  echo "$OUT/$screen.png"
done
echo "${#SCREENS[@]} screens in $(($(date +%s) - started))s"
