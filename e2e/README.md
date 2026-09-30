# Watching the flows happen

`./loop/verify.sh` proves the rules hold. This proves the product works, by
driving the real app on a simulator while you watch.

```bash
./e2e/run.sh                 # every flow, in order
./e2e/run.sh walk            # just the walk and unlock
./e2e/run.sh --record walk   # and keep e2e/out/walk-and-unlock.mp4
./e2e/run.sh --build         # force a rebuild of the simulator app
./e2e/run.sh --keep          # leave the sim, Metro and the API up to poke at
```

Exit codes follow the gate: **0** pass, **1** a flow failed, **2** the
environment needs a human.

**Tapping the icon afterwards shows "No script URL provided".** The simulator
app is a Debug build with no JS bundle of its own: it loads one from Metro on
:8081, and the run kills Metro on exit. Either run with `--keep`, or start
Metro against the compose API (`docker compose up -d`, `mobile/.env` from
`.env.example`): `cd mobile && npx expo start --dev-client`, then tap the icon.

**To see a screen mid-flow**, add `- takeScreenshot: name` to the flow for one
run. An absolute path fails the step; a bare name lands in
`~/.maestro/tests/<timestamp>/<flow>/takeScreenshot/name.png`.

**It needs the OSRM sidecar** (`./osrm/build.sh` once, then `docker compose
--profile routing up -d osrm`). The walk is the route OSRM picks, and without
streets the app picks a different one. Each leg is walked in two fixes, halfway
along its street shape and the stop, because every `setLocation` is a driver
round trip and turn by turn the walk spent most of the journey on them.
`E2E_ROUTING_URL` points it elsewhere.

Those shapes are pasted into `walk-and-unlock.yml`, so a solver change that
reorders the walk breaks it. `./e2e/run.sh --keep walk`, then
`venv/bin/python e2e/travel.py` writes every leg afresh.

**Point `--record` at one flow, not at all of them.** Recording is not free and it
is not stable in bulk: `./e2e/run.sh` on its own passes 6/6 run after run,
while `./e2e/run.sh --record` fails three of the six - a *different* three each
time, and still a different three after every wait in every flow was raised to
30-45s. `simctl io recordVideo` destabilises the simulator enough to break
whatever happens to be running, and the flows are not what is wrong. A single
`--record walk` is the case that matters anyway: one mp4 of somebody walking into
range and holding the ring, rather than 300MB nobody watches.

The waits are sized for a loaded machine. `extendedWaitUntil` returns the
moment its condition holds, so a generous timeout costs nothing when nothing is
wrong, and is the difference between a real failure and a flake when something
else on the machine is busy — the autonomous loop in `loop/`, for instance,
which edits `mobile/` and will hot-reload the app out from under a run.

## What it does

Its own database (`memorylane_e2e`, built from `db/schema.sql` and seeded by
`pipeline/seed_dev.py`), its own API on `:8090`, Metro on `:8081`, and
[Maestro](https://maestro.dev) driving the app. The extracted corpus in
`memorylane` is never touched - re-extracting it costs money.

The database is rebuilt **before every flow**, and that is not belt-and-braces.
`launchApp: clearState: true` wipes AsyncStorage but not the keychain, so the
device id survives - which is correct (see the survival table in `docs/architecture.md`)
and means one flow's unlocks are still the server's truth in the next one.
Dropping the database is what makes each flow start as a stranger.

One exception, for F27: before `walk-and-unlock` the run plants a memory at
0,0 and a trigger that unlocks it *yesterday* for whichever device first
appears, so the walk-done card has a two-day streak to show. The app mints its
device id itself, so there is no id to seed ahead of time.

And `lakes-loop` gets `seed_dev --routes lakes` instead of the random-start
cluster: a flow named `lakes-*` is planted round the Copenhagen lakes. The same
kind of trigger (`past_walks`) gives its device two walks from earlier in the
week, one finished and one given up, so F31 has a history to open.

## It is only slow when you are doing something else

Every phase prints what it cost, and the suite prints a total, because the
numbers are surprising. A clean run spends **182s** in flows, measured with
nothing else using the machine (the eight per-id files it replaced took 316s):

    file-and-edit 66s · look-around 49s · walk-and-unlock 67s

The old suite once took **twenty minutes** while a pytest run, a ruff pass and
a docker command were sharing the machine - one flow alone went from 50s to 956.
The simulator, Metro and the XCTest runner all lose badly under CPU contention,
and they lose unevenly, so the result looks like one flow has become
pathological rather than like the machine being busy.

If a run looks inexplicably slow, the first question is what else is running.
Start the suite and leave the machine alone; it is faster in wall-clock terms
than working in parallel and then re-running it because the timings made no
sense.

## When the driver wedges

After a long session - dozens of runs - Maestro's XCTest driver can stop
answering and take the run with it:

    Assert that "…" is not visible...
    Exception in thread "main" UnknownFailure(errorResponse=Request for
    viewHierarchy failed, code: 500, body: )

`maestro test` then hangs rather than exiting, so the run never finishes and
nothing says why. It is the driver, not the app and not the flow: the same
flow passes immediately afterwards.

    pkill -f maestro.cli; pkill -f "xcodebuild test-without-building"
    xcrun simctl shutdown booted && xcrun simctl boot <udid>

Then run again. If a run was killed mid-flight it may also have left its
database behind, since the teardown never ran:

    docker compose exec db psql -U memorylane -d memorylane \
      -c "SELECT datname FROM pg_database WHERE datname LIKE 'memorylane_e2e%'"

## The three layers

| | Where | Runs in CI | Answers |
|---|---|---|---|
| Rules | `tests/test_api_*.py` | yes | is each rule right |
| Flows, headless | `tests/test_flows.py` | yes | do the rules compose into a journey |
| Flows, watchable | `.maestro/*.yml` | no | does the product work |

When a Maestro flow goes red, run `./loop/verify.sh` first: if
`tests/test_flows.py` is green the API is fine and the app moved.

## The flows

Named after `docs/08-ux-flows.md`, which is the specification.

| File | Flow |
|---|---|
| `look-around.yml` | F29 the map of what is locked and its peek, F1 plan a walk (and nothing walkable), F32 show me another, F8 be asked for location |
| `walk-and-unlock.yml` | F13 walk into range, F7 unlock, F25 today's route, F30 finish a walk, F27 the streak on its card, F15 reread what you unlocked, F26 heart it, F33 leave a note and rewrite it, F31 look back at a walk |
| `lakes-loop.yml` | F1 the whole slider round the lakes, "The longest from here.", F32 show me another until the far lake, F31 look back at past walks |
| `file-and-edit.yml` | F5 file your own, F21 be somebody, F24 manage what you filed, and the author hearing back (hearts, notes, "New") |
| `notify-nearby.yml` | F28 the nearby notification, with the app in the background, and its banner bringing the app back |
| `open-from-afar.yml` | F7 a free unlock from anywhere, from a pin's peek, and the step count at the top counting it |
| `subscribe-when-out-of-steps.yml` | F35 the paywall when an unlock is refused for want of steps, then the same pin opening once the account has paid |

Six journeys rather than one file per id: every flow pays a fresh database
and a cold start, and the old per-id files performed the same unlock three
times and the same filing twice. A new id joins the journey it belongs to; a step a journey repeats goes in
`.maestro/steps/` (`launch.yml` is every flow's cold start and sign-in), which `run.sh` does not run on its own.

## Writing a flow

Things that cost an afternoon each to discover.

1. **Text matching is a full-string regex, not a substring.** `Walk there`
   matches only that exact label; `Nearest locked memory` matches nothing,
   because the pill reads `Nearest locked memory · 227 m`.
2. **A marker is named `` `${groupLabel}. ${STATE_LABEL[reach]}.` ``** — its
   place *and* its state, so `tapOn` has to give both. That string is the
   MKAnnotation's `title`; a Marker's `accessibilityLabel` is ignored by iOS
   and `subtitle` never reaches the label either, which is why the state lives
   where it does (`mobile/src/MemoryMarker.tsx`).
3. **iOS location permission takes `always`/`inuse`/`never`/`unset`, not
   `allow`.** `inuse` everywhere but `notify-nearby.yml`: only the opt-in
   nearby toggle asks for `always`.
4. **`clearState: true` does not clear AsyncStorage.** It is not enough on
   its own, so `e2e/run.sh` deletes `RCTAsyncLocalStorage_V1` before every
   flow. Without that, one flow's collection survives into the next and a
   padlock 300m away renders as a memory already earned - a failure that
   reads exactly like an app bug and is not one.
5. **Always `setLocation` before `launchApp`.** A simulator with no fix at all
   makes `getCurrentPositionAsync` hang, and the app correctly sits on "Turn on
   location" forever, which looks like a bug in your flow.
6. **Maestro sees only the app in front, and matching ignores case.**
   `pressKey: home` left this app in front, and `.*A memory is nearby.*` then
   matched the toggle's label "Notify me when a memory is nearby": a
   notification that never came passed. Put another app in front with
   `launchApp: com.apple.Preferences`. A notification banner is SpringBoard's
   and Maestro reads no text in it, so tap where it sits and assert on text
   only this app shows. Check a new assertion fails with the thing removed.
7. **A geofence registered with you inside it never fires.** locationd starts
   it Inside and sends no Enter. Registration lands a second or two after the
   toggle, so stand still outside every fence for a few seconds first
   (`extendedWaitUntil` with `optional: true` is the pause).
8. **A tap on a button at the bottom does nothing: check `e2e/out/logs/metro.log`
   for `WARN`.** Any `console.warn` raises the dev build's "Open debugger to
   view warnings" toast over the bottom of the screen, and the tap lands on it.
   Fix the warning; a retry only hides it. (A deprecated DateTimePicker
   `onChange` covered the sheet's Close.)
9. **A map pin stays tappable under a modal.** Your own memories are pins
   (docs/10, *A map of what is locked*), and a pin's label starts with the
   place name, so `.*<place>.*` in the journal tapped the pin behind it.
   Match the row's own shape, `"<place>, .*"`.

Coordinates and `dev seed` place names in the YAML are held against
`pipeline/seed_dev.py` by `tests/test_flows.py::test_maestro_flows_still_point_at_the_seed`,
because when they drift the symptom is an empty map rather than an error.

## Bugs these flows found

All fixed. Kept here because two of them are traps worth not re-setting.

**The nearby notification could never start on iOS.** `startGeofencingAsync`
throws unless `UIBackgroundModes` has `location`, which `app.json` never asked
for (`isIosBackgroundLocationEnabled`), and App.tsx swallowed the error: the
toggle showed on and nothing was watched. Now it warns, and the mode is set.

**The map crashed on a marker mutation.** `AIRMap insertReactSubview:atIndex:`
threw `NSRangeException` — under Fabric, `prepareForRecycle` hands back an
AIRMap with an empty `_reactSubviews` and the mount instructions are replayed
at their original indices. Two independent flows hit it. Fixed upstream in
react-native-maps 1.29.6, which clamps with
`MIN(atIndex, _reactSubviews.count)`; this project was on 1.27.2.

**A long `animateToRegion` never reports back**, so F19 never rendered and
"Show me New York" moved the camera and left the pins behind. Fly 40m and the
map announces where it settled; fly 6,000km and it says nothing, so the fetch
that every camera move gets for free never happened. Full reasoning in
`docs/10-decisions.md#the-app`; `useMapCamera` now watches a flight rather than
trusting it. F19 is gone and no flow flies that far any more, so nothing tests it —
the behaviour being relied on belongs to the native map, so there is nothing
a unit test could hold.

**A pin never told a screen reader whether it could be opened.** `MemoryMarker`
set `accessibilityLabel`, which iOS drops on a Marker: the label comes from the
MKAnnotation, so VoiceOver announced MapKit's default, "Map pin", or just the
place name. `subtitle` does not reach it either. The state now rides in
`title`, which is the only string that does — and an empty tooltip `Callout`
suppresses the bubble that `title` would otherwise raise, a white system-font
rectangle that also sat on the map after the sheet was dismissed.

## What no flow covers

Implemented, and out of a simulator's reach:

- **F2** opens a video in the browser, which leaves the app Maestro is driving.
- **F10 / F16** need the network taken away mid-flow; F16 has a by-hand recipe below.
- **F22** is a real Google or Apple sign-in, which neither works on a simulator
  nor in a scripted one.
- **F28** with the app killed or the phone locked. `notify-nearby.yml` covers
  the app in the background; neither Maestro nor simctl can lock a simulator.

## Seeing F16 (the collection with no network)

Not scripted: taking the API down mid-flow is machinery Maestro cannot reach.
By hand, in about ten seconds:

```bash
./e2e/run.sh --keep walk         # earns one memory, leaves everything up
lsof -ti:8090 | xargs kill       # the API goes away
```

The map turns to "Can't reach Memory Lane" and offers "Try again"; the Memories
tab's *Unlocked* section still reads the memory, from the device - *My
memories*, being a server fetch, would not.
