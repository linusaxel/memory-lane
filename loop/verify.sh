#!/usr/bin/env bash
# ============================================================================
# THE GATE. This is the only thing allowed to say "it works".
#
#   exit 0  GREEN  - everything passes
#   exit 1  RED    - something is broken; fixing it outranks all other work
#   exit 2  INFRA  - the environment needs a human (Docker down, venv missing).
#                    The loop should noop-sleep on this, not "fix" it.
#
# Target: under 60s warm. If it creeps past ~90s, move the slow thing into its
# own milestone task rather than making the gate optional.
# ============================================================================
set -uo pipefail
cd "$(dirname "$0")/.."
FAIL=0

PY=venv/bin/python
[ -x "$PY" ] || { echo "GATE=INFRA venv missing - run: uv venv --python 3.12 venv"; exit 2; }
$PY -c 'import pytest' 2>/dev/null || { echo "GATE=INFRA pytest missing - run: uv pip install --python venv/bin/python -r requirements-dev.txt"; exit 2; }

# --- 1. does anything even import ------------------------------------------
$PY -m compileall -q crawler pipeline api tests >/dev/null 2>&1 || { echo "GATE=RED syntax error"; exit 1; }

# --- 2. database, if any test needs it -------------------------------------
# Only pay the Docker cost when a test is actually marked `db`.
if $PY -m pytest --collect-only -q -m db 2>/dev/null | grep -q '::'; then
  docker info >/dev/null 2>&1 || { echo "GATE=INFRA Docker is not running - a human must start Docker Desktop"; exit 2; }
  docker compose up -d db >/dev/null 2>&1 || { echo "GATE=INFRA db service failed to start"; exit 2; }
  for _ in $(seq 1 30); do
    docker compose exec -T db pg_isready -U memorylane -q 2>/dev/null && break
    sleep 1
  done
  docker compose exec -T db pg_isready -U memorylane -q 2>/dev/null \
    || { echo "GATE=INFRA db never became ready"; exit 2; }
fi

# --- 3. the suite ----------------------------------------------------------
# -m "not credits and not live": never spends money, never needs the network.
$PY -m pytest -q -m "not credits and not live" || FAIL=1

# --- 4. the app, once it exists --------------------------------------------
if [ -f mobile/tsconfig.json ]; then
  ( cd mobile && npx --no-install tsc --noEmit ) || FAIL=1
  for t in mobile/src/*.test.ts; do
    [ -e "$t" ] || continue
    ( cd mobile && node --test "src/$(basename "$t")" ) || FAIL=1
  done
fi

if [ $FAIL -eq 0 ]; then echo "GATE=GREEN"; else echo "GATE=RED"; fi
exit $FAIL
