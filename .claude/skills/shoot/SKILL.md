---
name: shoot
description: Screenshot every screen of the Memory Lane app (or the ones named), 76 of them in about 3.5 minutes, without Maestro. Use when asked to capture, screenshot or look at every screen, or to check a UI change across the app.
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
mobile/scripts/shoot.sh                  # every screen, ~3 s each
mobile/scripts/shoot.sh paywall journal  # just those
```

The output is `~/Downloads/memory-lane-shots/<screen>.png`; a full run clears
it first and takes about 3.5 minutes. Then Read the PNGs that matter. The
screen names are `SCREENS` in `mobile/src/devOpen.ts`.

## What it covers

76 screens: startup, sign-in, onboarding, the map, every memory card (locked
near and far, a stack, open with pictures, a quote, a Wikipedia preview,
notes, report, block, your own), the planner and its variants (stops, mystery,
new nearby, nothing at that length, no location, no walk, finding, one way,
ends where tapped, unreachable end, Customize empty and set), the walk (card,
mystery, no location, lock, end, done and the notify ask, the rank-up and "You're already"), the
journal and what opens in it, the Collector's page, Submit at each step (filled, styling, date,
discard, error, seal, editor, delete), Settings top and foot, delete account,
Profile, Paywall, and the crash page. `offline-` screens fail every request to
the API through the real code paths.

Not covered, on purpose:

- **System UI**: the location, camera, photo and mic prompts, the Apple and
  Google sheets, and the memory's "…" menu (an iOS action sheet).
- **Mid-animation frames**: the plan button's walk, the route drawing, the
  locket's slide and opening, the iris into the sheet, and the journal's
  count roll and row pulse.
- **Needs what a simulator lacks**: the paywall's plans (a real store), audio
  (`EXPO_PUBLIC_AUDIO=1`), and linking Google (its client ids).
- **Not drawn at all**: the unlock error only reaches VoiceOver.

## How it works, and the traps

- The script writes `screen=<name>&memory=<id>` into `Documents/dev-screen` in
  the app's sim container. `src/devOpen.ts` (in `__DEV__` only) polls it and
  tells every `useDevScreen` listener: `devApply` in App.tsx closes what the
  last screen opened and opens this one, and each sheet (Submit, MemorySheet,
  Notes, Settings, SignIn, EditProfile) sets its own step.
- The `memory-` screens' memories are picked from the dev database and
  unlocked for the simulator's device. `scripts/reset-unlocks.sh` undoes that.
- To add a screen: its name in `SCREENS`, a case in `devApply` for what opens
  it, and a line in the sheet's own `useDevScreen` for a step inside it.
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
