# Watching the flows happen

`./loop/verify.sh` proves the rules hold. This proves the product works, by
driving the real app on a simulator.

```bash
./e2e/run.sh                 # every flow, in order
./e2e/run.sh walk            # one flow: a whole name, or the part before its first "-"
./e2e/run.sh --record walk   # and keep e2e/out/walk-and-unlock.mp4
./e2e/run.sh --build         # force a rebuild of the simulator app
./e2e/run.sh --keep          # leave the sim, Metro and the API up to poke at
```

Exit codes follow the gate: **0** pass, **1** a flow failed, **2** the
environment needs a human. A clean run is about 7 minutes; leave the machine
alone while it goes, because the simulator, Metro and XCTest slow down badly
and unevenly under load (one flow once went from 50 s to 956 s).

## What it does

Its own database (`memorylane_e2e_<pid>`, from `db/schema.sql`, seeded by
`pipeline/seed_dev.py` round a random walkable start; `E2E_START=lat,lng`
replays one), its own API on `:8090`, Metro on `:8081`, and
[Maestro](https://maestro.dev) driving the app. The corpus in `memorylane` is
never touched.

The database is rebuilt **before every flow**. `clearState: true` keeps the
keychain, so the device id survives (correctly, see `docs/architecture.md`), and
only a fresh database makes each flow a stranger. A flow needing more than the
seed has `e2e/sql/<flow>.sql`, applied after the reset: six days of walks for
the streak, past walks for the lakes, a paid account once renamed Paid. Each is a
trigger on the device or user the app has not minted yet. Signing in and
planning mint neither (reads create nothing), so a flow whose trigger must fire
before the first walk mints one with `steps/rename.yml` first. A flow named
`lakes-*` is seeded round the lakes (`seed_dev --routes lakes`) instead.

It needs the OSRM sidecar (`./osrm/build.sh` once, then `docker compose
--profile routing up -d osrm`; `E2E_ROUTING_URL` points elsewhere): the walk is
OSRM's route, and `e2e/travel.py` writes each leg as two fixes into
`e2e/out/legs/`.

## The flows

Named after `docs/08-ux-flows.md`, which is the specification. One file per
journey, not per id: every flow pays a fresh database and a cold start. A new
id joins the journey it belongs to; a step two flows share goes in
`.maestro/steps/`, which run.sh never runs on its own.

| File | Flow |
|---|---|
| `walk-and-unlock.yml` | F13 walk into range, F28 the nearby notification with the app in the background, F7 unlock, F25 today's route, F30 finish, F27 the streak, F15 reread (a linked name previews from Wikipedia), F26 heart, F33 a note rewritten, F31 the walk in the journal, F35 the paywall once walked out, then a walk once paid |
| `lakes-loop.yml` | F8 be asked for location (and refused), F1 the planner and its list (one way, nothing walkable, the whole slider, the longest walk), F32 another walk until the far lake, F31 past walks |
| `file-and-edit.yml` | F5 file your own: the story's markdown, every toolbar block, a placed and wrapped photo, the in-story camera, ↑ reorder, Preview; F21 be somebody, F24 manage what you filed, the author hearing back |

| Step | Used by |
|---|---|
| `launch.yml` | every flow: stand at LAT,LNG, cold start, sign in |
| `start-walk.yml` | walk-and-unlock: plan and accept the 4-stop loop |
| `unlock-stop.yml` | walk-and-unlock, once per stop |
| `rename.yml` | walk-and-unlock, to mint the account and to pay |

## Writing a flow

Each of these cost an afternoon.

1. **Text matching is a full-string regex, case-insensitive.** `Walk there`
   matches only that label; anything longer needs `.*`.
2. **Assert a sentence by `testID`, a label by its text.** A copy pass once
   meant editing seven flows. Long prose (`walk-done`, `end-walk-warning`,
   `no-walk`, ...) carries a testID; short button and pill labels stay prose.
3. **A pin is named `${groupLabel}. ${STATE_LABEL[reach]}.`**, place *and*
   state, from the MKAnnotation's `title` (iOS ignores a Marker's
   `accessibilityLabel`). A pin stays tappable under a modal, so match a
   journal row's own shape, `"<place>, .*"`.
4. **Location permission is `always`/`inuse`/`never`/`unset`**, and
   `setLocation` goes before `launchApp`: with no fix the app waits on "Turn
   on location" forever.
5. **`clearState: true` does not clear AsyncStorage**, so run.sh deletes
   `RCTAsyncLocalStorage_V1` before every flow.
6. **A system prompt outlives the app.** Left unanswered, it sits over every
   later launch, which fails on "Memory Lane". iOS 26 asks for full photo
   access despite run.sh's `simctl privacy grant`; answer it with an optional
   tap. The photo picker runs out of process, so Maestro reads no text in it:
   `waitForAnimationToEnd`, then tap a cell by point.
7. **`hideKeyboard` fails on a multi-line field.** Scroll to the next control
   instead.
8. **Maestro sees only the app in front.** A notification banner is
   SpringBoard's: put another app in front (`launchApp: com.apple.Preferences`),
   tap where the banner sits, and assert on text only this app shows. Check a
   new assertion fails with the thing removed.
9. **A geofence registered from inside never fires.** Stand still outside
   every fence for a few seconds first (`extendedWaitUntil` with
   `optional: true` is the pause).
10. **A bottom tap that does nothing: look for `WARN` in
    `e2e/out/logs/metro.log`.** A `console.warn` raises the dev toast over the
    bottom of the screen. Fix the warning.
11. **The first-pick card covers the lower map** until the welcome unlock is
    spent. Tap a pin above it, or pick first.
12. **The keyboard covers the bottom of a sheet.** A `KeyboardAvoidingView` in
    a page sheet does not lift it, and the suggestion strip takes taps meant
    for what is under it. Put controls a flow taps while typing at the top of
    the sheet.

To see a screen mid-flow, add `- takeScreenshot: name`; it lands in
`e2e/out/shots/<flow>/takeScreenshot/name.png`, beside the failure screenshots and Maestro's
logs. `walk-and-unlock` keeps two: `walk-card` and `finish-card`.

Coordinates and `dev seed` names in the YAML are held against `seed_dev.py` by
`tests/test_flows.py::test_maestro_flows_still_point_at_the_seed`: when they
drift, the symptom is an empty map, not an error.

## When it breaks for no reason

- **"No script URL provided" on the icon:** the Debug build loads its JS from
  Metro, which the run stops. Use `--keep`, or `cd mobile && npx expo start
  --dev-client` against `docker compose up -d`.
- **"xcodebuild failed":** read `e2e/out/logs/build.log` for `error:`. A
  missing codegen file is `pod install`; a missing font or asset means
  `mobile/ios` predates an app.json change: `npx expo prebuild --platform ios
  --clean`, then `pod install`.
- **The driver wedges** after dozens of runs (`viewHierarchy failed, code:
  500`, then `maestro test` hangs; run.sh gives up after `FLOW_TIMEOUT`):

      pkill -f maestro.cli; pkill -f "xcodebuild test-without-building"
      xcrun simctl shutdown booted && xcrun simctl boot <udid>

  A killed run may leave `memorylane_e2e_*` databases behind; drop them.
- **`--record` on several flows** fails a different three each time: the
  recorder destabilises the simulator. Record one flow.

## The three layers

| | Where | Runs in CI | Answers |
|---|---|---|---|
| Rules | `tests/test_api_*.py` | yes | is each rule right |
| Flows, headless | `tests/test_flows.py` | yes | do the rules compose into a journey |
| Flows, watchable | `.maestro/*.yml` | no | does the product work |

A Maestro flow goes red: run `./loop/verify.sh` first. If `tests/test_flows.py`
is green, the API is fine and the app moved.

## What no flow covers

- **F2** opens a video in the browser, which leaves the app.
- **F10 / F16** need the network taken away mid-flow. F16 by hand:
  `./e2e/run.sh --keep walk`, then `lsof -ti:8090 | xargs kill`. The map says
  "Can't reach Memory Lane"; the journal's *Unlocked* still reads the memory.
- **F22**, a real Google or Apple sign-in.
- **F28** with the app killed or the phone locked.

## Bugs these flows found

All fixed; the full diagnoses are in this file's git history.

- **Nearby notifications never started on iOS:** `startGeofencingAsync` needs
  `UIBackgroundModes: location`, and App.tsx swallowed the error.
- **The map crashed on a marker mutation** under Fabric
  (`AIRMap insertReactSubview:atIndex:`); fixed in react-native-maps 1.29.6.
- **A long `animateToRegion` never reports back**, so the pins stayed behind
  (docs/10, *The app*). `useMapCamera` watches a flight rather than trusting it.
- **Photo uploads failed unseen** under SDK 57's `expo/fetch`; file-and-edit now
  attaches one.
