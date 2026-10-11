---
name: shoot
description: Screenshot every screen of the Memory Lane app (or the ones named) in under a minute, without Maestro. Use when asked to capture, screenshot or look at every screen, or to check a UI change across the app.
---

# Shoot every screen

Pictures only. Whether a flow *works* is still `./e2e/run.sh`'s job.

## Before

- `docker compose up -d` (the API on :8080)
- `mobile/scripts/sim.sh` running (Metro and the dev build on the booted sim).
  Start it in the background if it isn't up: `lsof -ti :8081` says.
- Memories near the dev location, or `preview`, `walk` and `done` come out empty.

## Run

```bash
mobile/scripts/shoot.sh                  # every screen, ~1.5 s each
mobile/scripts/shoot.sh paywall journal  # just those
```

The output is `e2e/out/shots/<screen>.png`. Then Read the PNGs that matter.
The screen names are `SCREENS` in `mobile/src/devOpen.ts`. To add a screen, add
its name there and a case in `devApply` in `mobile/App.tsx`.

## How it works, and the traps

- The script writes `screen=<name>` into `Documents/dev-screen` in the app's sim
  container. `devWatch` (in `__DEV__` only) polls the file and calls `devApply`,
  which closes what the last screen opened and then opens this one.
- Not `simctl openurl`: a custom scheme asks "Open in Memory Lane?" every time.
- `walk`, `end-confirm` and `done` take the walk `preview` planned, on the phone
  only. Nothing is accepted on the server, so the day's free walk is not spent.
  Shoot `preview` before them. Running everything does that already.
- `walk`, `end-confirm` and `done` hide the unlock lock, so their own cards
  show even when the dev location stands on a memory. `lock` is the walk with it.
- `crash` shows the crash page without throwing. A real throw in a dev build is
  covered by React Native's red error screen.
- A shot that shows the screen before it means the wait was too short. Raise it
  for that screen in the `case` in `shoot.sh`.
