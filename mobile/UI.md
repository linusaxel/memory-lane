# UI guide

For agents working in `mobile/`. The app is two surfaces and one flow; this file
says what it looks like, why, and how to check you did not break it.

Read this before changing anything under `mobile/src/` or `App.tsx`.

## The app today

One screen, three modals.

```
MapView (full bleed)
├─ Marker per coordinate      tap -> MemorySheet.  Four states, see Markers
├─ banner  "N memories here"  top centre, non-interactive
├─ "N within reach"           seal red, breathing, tap -> the nearest unlockable
│    or "Nearest locked · 412 m"   muted and still, when none is in reach
├─ "Near me"                  bottom centre, recentres on GPS
└─ LocationPrimer             bottom card, only until permission is settled

MemorySheet (pageSheet modal) - two compositions, not one with holes in it

  locked                            open
  ├─ place name       26/700        ├─ place name       26/700
  ├─ "locked"         13, muted     ├─ distance · confidence
  ├─ padlock                        ├─ summary  17/26 - the hero, no images
  ├─ distance         44/700        ├─ tags     pills
  ├─ "Get within 150 m"             ├─ source video title  italic, muted
  ├─ "Walk there"     outlined      └─ "Watch at 12:04"  red, YouTube at the second
  └─ or, in reach: the ring

Collection (the second tab)
└─ what this device has unlocked, newest first; a row opens the sheet

Settings (the third tab, "You")
├─ what this device has unlocked, as a number
├─ how unlocking works      the one place that answers "why can't I read this"
├─ location state + action
└─ privacy policy, and the fact that nothing is synced

TabBar
└─ Map | Unlocked (N) | You
```

**Unlocked memories are readable forever, and that is a device promise, not a
server one.** There are no accounts, so "forever" means as long as the app's
storage survives. A new phone starts empty. Making that portable needs identity
— Phase 3.

| File | What it owns |
|---|---|
| `src/Padlock.tsx` | the one symbol, at any size, in any colour |
| `src/MemoryMarker.tsx` | a coordinate's four states on the map |
| `src/UnlockButton.tsx` | the hold, the ring, the haptics |
| `src/ReachBanner.tsx` | the only thing on the map that animates |
| `src/LocationPrimer.tsx` | asking before the system does |
| `src/Collection.tsx` | what the walking was for |
| `src/TabBar.tsx` | three tabs, hand-rolled |
| `src/Settings.tsx` | the "You" tab |
| `src/theme.ts` | **every colour and font.** Start here |
| `src/mapStyle.ts` | how the map gets out of the way |
| `src/reach.ts` | which pins look openable. Pure, and unit-tested |

## Tokens

**`src/theme.ts` is the only place colours and fonts are defined.** Import from
it; never write a hex or a font name inline. If you find yourself reaching for a
Tailwind value or the system font, that is the generic look coming back — see
[`docs/09-visual-design.md`](../docs/09-visual-design.md) part 5 for why this
palette exists at all.

**Ink and paper.** The app is an archive of anecdotes pinned to coordinates, so
it is built to look like a field guide rather than a dashboard.

| Token | Hex | Used for |
|---|---|---|
| `paper` | `#F7F4EE` | every surface. Not white, and close to the muted map underneath |
| `paperRaised` | `#FFFDF9` | the rare surface that must lift off the paper |
| `ink` | `#1C1917` | primary text, solid buttons |
| `inkSoft` | `#4A443D` | secondary prose |
| `inkFaint` | `#8A837A` | labels, captions |
| `rule` | `#E0D9CC` | hairlines. Rules do the work shadows used to |
| `faded` | `#776E64` | a locked pin out of reach. Dark enough to survive the parchment map |

**One accent, and it means one thing.**

| Token | Hex | Meaning |
|---|---|---|
| `seal` | `#C0462B` | **openable.** The reach pill, the unlock ring, the in-reach pin. Nothing else, ever |
| `sealSoft` | `#F0D9CE` | the ring filling during a hold |
| `sealDeep` | `#8F2F1B` | the padlock inside the ring, the count tag on a reachable pin |

The watch button is **ink**, not red. It was YouTube red back when the map pins
were red too; that stopped being true, and the accent is spoken for.

## Type

Two families, no more.

| Role | Family | Why |
|---|---|---|
| Display, prose | **Fraunces** (`font.display` / `displaySemi` / `prose`) | an old-style serif with its wonk left in. These are stories somebody told, not table rows |
| Apparatus | **IBM Plex Mono** (`font.mono` / `monoMedium` / `monoBold`) | distances, counts, labels, buttons. A number in a mono reads as a measurement |

**The label voice** is `label` in `theme.ts`: uppercase Plex Mono, 11px, 1.1
tracking, `inkFaint`. Use it wherever a screen *names* a thing rather than says
something — section headings, tab labels, meta rows, button text.

**Scale**: 34 display (tab titles) · 30 (place name) · 52 (the distance figure)
· 19/31 prose (the summary — the hero, there are no images) · 16/25 prose (body)
· 11–12 mono (everything labelled).

Fonts load in `App.tsx` via `useFonts`, and the app renders `null` until they
are ready. Two families carry the whole design, so there is no sensible
half-loaded state.

**Corners are 4px**, not pills.

**Elevation is a rule, not a shadow.** Hierarchy comes from hairlines and
weight, which is how editorial layouts have always done it and is the shortest
way out of the stacked-card look. The only two things still casting a shadow are
"Near me" and the location primer, which genuinely hover over a map; both carry
`shadow*` (iOS) and `elevation` (Android), because setting one looks flat on the
other platform.

**The map is muted on purpose.** `mutedStandard` on iOS, a style array on
Android, points of interest off. The app has one subject and it is the pins.

## Zoom, and the reach circle

**Two zoom levels, because the map does two different jobs.**

| | Delta | Roughly | When |
|---|---|---|---|
| `FALLBACK_REGION` | `0.09` | 10 km | No position. A preview of where the corpus is |
| `LOCATED_DELTA` | `0.01` | 1.1 km tall | Centred on the person |

Landing on the person at street scale is the whole point: at 10 km a 150 m
unlock radius is four pixels and the mechanic is invisible, so the app reads as
a map of things you cannot have. At 1.1 km the reach circle is about a quarter
of the screen and "walk two blocks" is a visible distance.

The **fallback stays wide on purpose.** With no permission nothing can unlock,
there is no circle to draw, and the only useful thing the map can say is "here
is roughly where the memories are". Zooming a browse state into an empty street
would break rule 1 for no gain.

**The reach circle** is drawn once, around the person, at the server's radius —
never around each pin, which would be fifteen overlapping circles and no
information. It is `seal` at low opacity: present, and never competing with the
pins it is there to qualify. No position, no circle.

A consequence worth knowing: the fetch radius follows the viewport
(`regionToRadiusKm`), so at this zoom the app asks for ~700 m and the banner
count is honestly what is near you rather than what is in the county. When
nothing is in reach the "nearest locked memory" pill is what points further
out.

## Rules that are load-bearing

Each of these exists because something broke or would have been rejected.

1. **Never show a blank grey map.** `FALLBACK_REGION` points at Manhattan when
   permission is denied, because store reviewers routinely tap Deny and an empty
   map is a rejection. Any new view needs the same treatment: an empty state
   that still shows something real.
2. **Location is foreground-only.** `ACCESS_BACKGROUND_LOCATION` is explicitly
   blocked in `app.json` and asserted by `tests/test_app_config.py`. Requesting
   background location will fail the suite and the store review.
3. **Debounce map-driven fetches** (currently 400ms). Panning fires
   `onRegionChangeComplete` continuously; without it you DoS your own API.
4. **The API is radius-only.** `regionToRadiusKm()` circumscribes the viewport
   and clamps to 0.1–100km; outside that the API returns 422. There is no bbox
   endpoint.
5. **A memory with no coordinates cannot be drawn.** The API filters those out;
   do not assume `coordinates` is always present on types that allow null.
6. **`timestamp_url` is already correct.** It points at the right second. Never
   rebuild a YouTube URL by hand.
7. **Never cover the map attribution.** The Apple Maps logo and Legal link in
   the bottom-left corner are a condition of using the map and have to stay
   visible and tappable. A floating tally in that corner is what made this a
   rule; the tab bar moved it out of the way.
8. **`onRequestClose` is required on every Modal**, or the Android back button
   does nothing.
9. **Neither tab unmounts.** Switching tabs uses `display: 'none'`, not a
   conditional render. Unmounting the map means refetching, losing the viewport
   and re-animating to GPS every time somebody glances at their collection.

## Copy

Sentence case. No exclamation marks. Count strings are singular/plural aware
("1 memory here"). Errors say what failed in plain words — "Could not reach
Memory Lane" — never an error code, never a stack trace. Store-facing copy in
`mobile/store/` has character limits enforced by `tests/test_store_copy.py`.

## Verifying a UI change

`./loop/verify.sh` covers types and the pure logic, not appearance:

```bash
cd mobile && npm run typecheck      # also run by the gate
```

To actually look at it — this works today, no physical device:

```bash
# 1. API with real data
docker compose up -d --build

# 2. dev server on the booted simulator
cd mobile && EXPO_PUBLIC_API_URL=http://localhost:8080 npx expo start --ios

# 3. pre-grant location, or the permission dialog covers the first screen
#    ("booted" is a literal simctl accepts - no need to look up a UUID)
xcrun simctl privacy booted grant location-always host.exp.Exponent
xcrun simctl location booted set 40.7484,-73.9857   # Manhattan: where the data is

# 4. screenshot it
xcrun simctl io booted screenshot /tmp/app.png
```

If the dialog still appears, terminate and relaunch — the grant applies at
launch: `xcrun simctl terminate booted host.exp.Exponent` then re-open the
`exp://` URL. Scripted taps are not available; `osascript` has no assistive
access here, so anything past the first screen needs a human hand.

**Use `localhost` for the simulator, a LAN IP only for a physical phone.** Expo
bakes `EXPO_PUBLIC_API_URL` in at dev-server start, so if you pass your LAN IP
and then change network, the app silently shows "0 memories here" with no error
— the map still works, it just cannot reach the API. Restart the dev server
rather than debugging the app. Likewise `exp://<stale-ip>:8081` hangs on
"Opening project"; `exp://localhost:8081` does not.

Only one dev server can hold port 8081, and `npx expo start` cannot prompt in a
non-interactive shell — it just prints "Skipping dev server". Kill the old one
first: `lsof -ti:8081 | xargs kill -9`.

Set the simulator location to Manhattan. The seeded corpus is a US comedy
podcast — from Copenhagen you will correctly see an empty map and think you
broke something.

Pure viewport maths goes in `src/region.ts` with a `node --test` case beside it;
the gate runs `mobile/src/*.test.ts`. Component behaviour is currently untested
and there is no RN test runner installed — do not add one without asking.

## States

The map has four, and they must stay visually distinct — the bug this replaced
was that "nothing here" and "we could not ask" rendered identically:

| State | Banner | Button |
|---|---|---|
| loading | "Finding memories…" + spinner | Near me |
| ready, n>0 | "N memories here" | Near me |
| ready, n=0 | "No memories here yet" | Near me |
| failed | "Can't reach Memory Lane" | Try again |

With no location permission the button reads **"Turn on location"** instead of
"Near me", in every one of those states. Nothing can unlock without a position,
and a map of pins that never open with no explanation is the worse bug.

A failed refresh keeps the last good pins. Requests time out after
`REQUEST_TIMEOUT_MS` (8s) in `src/api.ts`; `fetch` has no default timeout and a
hung request is what produced the original bug.

## Markers

One marker is a *coordinate*, not a memory and not a place. 111 of 186 placed
memories sit on 34 coordinates, so a marker routinely stands for several
memories at several venues. A group of more than one carries a count badge, and
the sheet pages through it with "1 of 23 here".

Group in `src/cluster.ts`, never in the component — it is pure and unit-tested,
and the Times Square centroid is one of the test cases.

A marker also carries its lock state, because otherwise you learn a pin is
unreadable only by tapping it:

| Pin | Meaning |
|---|---|
| default map pin | never gated, one memory — a shared centroid, open to everyone |
| badge in `ink` | never gated, several |
| disc in `faded` with a padlock | locked, and you are not near enough |
| **ring** in `seal` with a halo | locked, and you are inside the radius |

**The reachable pin is a ring and not a disc**, and that is load-bearing. The
pin you can open is by definition the pin you are standing on, so the blue user
location dot lands exactly on top of it — a disc disappears underneath, count
and all. The dot sits inside the ring instead, the count moves to a corner tag,
and the shape matches the ring in the sheet so the map and the control read as
the same object.

**Nothing on a marker animates.** Animating a custom marker's children is a
known flicker source in react-native-maps. Markers set `tracksViewChanges={false}`
for the frame cost and are keyed `` `${group.key}:${reach}` ``, so they repaint
exactly when their state changes and never otherwise. The one moving thing is
`ReachBanner`, which is not a marker.

A group is locked if any memory in it is. `reachOf()` in `App.tsx` measures from
the *person*, never from the map centre — panning to another city must not make
its pins look reachable.

## Asking for location

Never `requestForegroundPermissionsAsync` on mount. That fires a system dialog
with no context, and one tap makes it permanent — it is the pattern every guide
names as the mistake, and the reported gap is roughly 30% opt-in cold against
65% after a primer. `LocationPrimer` explains the mechanic first, over a map
already showing real pins (rule 1), and only then hands over to the system.
`getForegroundPermissionsAsync` runs first so somebody who already said yes is
never asked twice, and a hard refusal (`canAskAgain === false`) swaps the button
for **Open Settings**, which is the only route back.

Position is then *watched*, not read once (`watchPositionAsync`, 25m interval,
foreground only). Walking into range has to change the map by itself.

## Two links that can fail

`Linking.openURL` rejects when nothing on the device can handle the link — no
browser, no maps app, a managed device. Both the watch link and "Walk there" go
through one helper in `MemorySheet` that catches it and says so. A control that
silently does nothing is the failure people blame on themselves.

## Accessibility

The unlock is a *hold*, which is the easiest gesture to make exclusionary, so
this is not a polish pass:

- The control has a role, a label, and a hint naming the gesture, and VoiceOver's
  plain activation opens it. That covers screen-reader users and not every motor
  impairment — the `ponytail:` marker in the file names the gap.
- Markers carry an `accessibilityLabel` with their state. The callout title says
  *where*; only the colour says whether you can read it, and colour is not
  available to everyone.
- Every state that colour distinguishes is also written: "locked", "within
  reach", "Nearest locked memory".

## The unlock control

`src/UnlockButton.tsx`. The one place in this app allowed to be playful. Everything else is a quiet
map; this is the moment the product is *about*, so it gets the animation
budget. Spec, so it does not get re-invented per screen:

- **Press and hold, not tap.** ~900ms. A tap is a click; a hold is a lock
  turning. It also makes an accidental unlock almost impossible, which matters
  because unlocking is irreversible.
- **A ring fills around the button** over the hold, driven by
  `Animated.timing` with `useNativeDriver`. Releasing early springs it back —
  visibly, so the person understands they let go rather than that it failed.
- **Haptics carry the feel**: `ImpactFeedbackStyle.Light` on press-in, a
  `Medium` at completion. Never on release-cancel, which would read as a
  reward for failing.
- **Locked and unlockable look different on the map**, not just in the sheet.
  If you have to open a pin to learn you cannot read it, the map is not doing
  its job.
- **Never lock something already unlocked.** Re-locking punishes leaving.

Accessibility is not optional here, and a hold gesture is the easy thing to get
wrong: the control needs `accessibilityRole="button"`, a label that states the
gesture, and it must remain operable by a plain activation for anyone who cannot
hold. A gate nobody with a motor impairment can open is a gate on the wrong
people. As built, `onPress` unlocks directly when a screen reader is on, which
covers VoiceOver and not every motor impairment — the `ponytail:` marker in the
file names the gap.

**The button never decides anything.** It asks
`GET /v1/memories/{id}?at_lat=&at_lng=` and the server re-measures, so a
completed hold can still come back refused when GPS has drifted. Say so —
"Not close enough yet" — rather than leaving a control that looks broken.

## Flows

Documented flows live in `docs/08-ux-flows.md`. Build toward those, and when a
flow changes, change that file in the same commit.
