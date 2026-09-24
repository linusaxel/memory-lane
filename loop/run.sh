#!/usr/bin/env bash
# Runs /ml-tick until STATE.md says TERMINAL. Each tick is its own `claude -p`
# session, so every task starts on an empty context: the /clear between tasks.
#
# INFRA is decided here, not in the tick: ScheduleWakeup does nothing under -p.
set -uo pipefail
cd "$(dirname "$0")/.."

MAX_TICKS=${MAX_TICKS:-100}

for ((i = 1; i <= MAX_TICKS; i++)); do
  head -1 loop/STATE.md | grep -q TERMINAL && { echo "loop: TERMINAL, see loop/STATE.md"; exit 0; }

  ./loop/verify.sh >/dev/null
  if [ $? -eq 2 ]; then
    echo "loop: gate INFRA, sleeping 15m"
    sleep 900
    continue
  fi

  echo "loop: tick $i"
  claude -p "/ml-tick" --permission-mode auto || { echo "loop: tick $i failed"; exit 1; }
done
echo "loop: stopped after $MAX_TICKS ticks"
