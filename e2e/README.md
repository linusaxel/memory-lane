# Watching the flows happen

`./loop/verify.sh` proves the rules hold. This proves the product works, by
driving the real app on a simulator while you watch.

```bash
./e2e/run.sh                 # every flow, in order
./e2e/run.sh f7              # just the unlock
./e2e/run.sh --record f7     # and keep e2e/out/f7-walk-and-unlock.mp4
./e2e/run.sh --build         # force a rebuild of the simulator app
./e2e/run.sh --keep          # leave the sim, Metro and the API up to poke at
```

Exit codes follow the gate: **0** pass, **1** a flow failed, **2** the
environment needs a human.

**Point `--record` at one flow, not at all six.** Recording is not free and it
is not stable in bulk: `./e2e/run.sh` on its own passes 6/6 run after run,
while `./e2e/run.sh --record` fails three of the six - a *different* three each
time, and still a different three after every wait in every flow was raised to
30-45s. `simctl io recordVideo` destabilises the simulator enough to break
whatever happens to be running, and the flows are not what is wrong. A single
`--record f7` is the case that matters anyway: one mp4 of somebody walking into
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
device id survives - which is correct (see the survival table in `CLAUDE.md`)
and means one flow's unlocks are still the server's truth in the next one.
Dropping the database is what makes each flow start as a stranger.

## It is only slow when you are doing something else

Every phase prints what it cost, and the suite prints a total, because the
numbers are surprising. A clean run is **211s**, measured with nothing else
using the machine:

    f1-discover 25s · f15-collection 53s · f19-elsewhere 23s
    f23-seal 25s · f5-file-a-memory 37s · f7-walk-and-unlock 40s

That same suite took **twenty minutes** while a pytest run, a ruff pass and a
docker command were sharing the machine - and `f15` alone went from 50s to 956.
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
| `f1-discover.yml` | F1 discover, F8 be asked for location |
| `f5-file-a-memory.yml` | F5 file your own, F21 be somebody |
| `f7-walk-and-unlock.yml` | F11 nearest, F12 walk there, F13 walk into range, F7 unlock |
| `f15-collection.yml` | F15 reread what you unlocked |
| `f19-elsewhere.yml` | F19 somewhere else entirely |
| `f23-seal.yml` | F23 sealed until a date |

## Writing a flow

Four things that cost an afternoon each to discover.

1. **Text matching is a full-string regex, not a substring.** `Walk there`
   matches only that exact label; `Nearest locked memory` matches nothing,
   because the pill reads `Nearest locked memory · 227 m`.
2. **A marker is named `` `${groupLabel}. ${STATE_LABEL[reach]}.` ``** — its
   place *and* its state, so `tapOn` has to give both. That string is the
   MKAnnotation's `title`; a Marker's `accessibilityLabel` is ignored by iOS
   and `subtitle` never reaches the label either, which is why the state lives
   where it does (`mobile/src/MemoryMarker.tsx`).
3. **iOS location permission takes `always`/`inuse`/`never`/`unset`, not
   `allow`.** `inuse` is also the only honest value - the app is
   foreground-only and `app.json` blocks background location.
4. **`clearState: true` does not clear AsyncStorage.** It is not enough on
   its own, so `e2e/run.sh` deletes `RCTAsyncLocalStorage_V1` before every
   flow. Without that, one flow's collection survives into the next and a
   padlock 300m away renders as a memory already earned - a failure that
   reads exactly like an app bug and is not one.
5. **Always `setLocation` before `launchApp`.** A simulator with no fix at all
   makes `getCurrentPositionAsync` hang, and the app correctly sits on "Turn on
   location" forever, which looks like a bug in your flow.

Coordinates and `dev seed` place names in the YAML are held against
`pipeline/seed_dev.py` by `tests/test_flows.py::test_maestro_flows_still_point_at_the_seed`,
because when they drift the symptom is an empty map rather than an error.

## Bugs these flows found

All fixed. Kept here because two of them are traps worth not re-setting.

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
trusting it. This flow is the only test of it — the behaviour being relied on
belongs to the native map, so there is nothing a unit test could hold.

**A pin never told a screen reader whether it could be opened.** `MemoryMarker`
set `accessibilityLabel`, which iOS drops on a Marker: the label comes from the
MKAnnotation, so VoiceOver announced MapKit's default, "Map pin", or just the
place name. `subtitle` does not reach it either. The state now rides in
`title`, which is the only string that does — and an empty tooltip `Callout`
suppresses the bubble that `title` would otherwise raise, a white system-font
rectangle that also sat on the map after the sheet was dismissed.

## Seeing F16 (the collection with no network)

Not scripted: taking the API down mid-flow is machinery Maestro cannot reach.
By hand, in about ten seconds:

```bash
./e2e/run.sh --keep f15          # earns one memory, leaves everything up
lsof -ti:8090 | xargs kill       # the API goes away
```

The map turns to "Can't reach Memory Lane" and offers "Try again"; the Memories
tab's *Unlocked* section still reads the memory, from the device - *My
memories*, being a server fetch, would not.
