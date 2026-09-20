# UI guide

For agents working in `mobile/`. The app is two surfaces and one flow; this file
says what it looks like, why, and how to check you did not break it.

Read this before changing anything under `mobile/src/` or `App.tsx`.

## The app today

One screen, four modals.

```
MapView (full bleed)
├─ Marker per coordinate      tap -> MemorySheet.  Four states, see Markers
├─ banner  "N memories here"  top centre, non-interactive
├─ "N within reach"           seal red, breathing, tap -> the nearest unlockable
│    or "Nearest locked · 412 m"   muted and still, when none is in reach
├─ "+ Add"                    top right, opens Submit. See "Writing"
├─ "Near me"                  bottom centre, recentres on GPS
└─ LocationPrimer             bottom card, only until permission is settled

MemorySheet (pageSheet modal) - two compositions, not one with holes in it

  locked                            open
  ├─ place name       26/700        ├─ place name       26/700
  ├─ "locked"         13, muted     ├─ distance · confidence
  ├─ padlock                        ├─ summary  17/26 - the hero
  ├─ distance         44/700        ├─ photo / recording   if it has any
  ├─ "Get within 150 m"             ├─ tags     pills
  ├─ "1 attachment waiting"         ├─ "Filed by X", or the channel and avatar
  ├─ "Walk there"     outlined      ├─ "Report this memory"  submissions only
  └─ or, in reach: the ring         └─ "Watch at 12:04"  red, YouTube at the second

  The locked side says how many attachments are waiting and never which. A
  photograph of the place is the memory as much as the text is.

Submit (pageSheet modal, from "+ Add") - see Writing

Collection (the second tab)
└─ what this device has unlocked, newest first; a row opens the sheet

Settings (the third tab, "You")
├─ unlocked / places / filed, as numbers
├─ your name                what submissions are signed with. Blank = Anonymous
├─ account                  Apple / Google. Never a wall; see SignIn.tsx
├─ how unlocking works      the one place that answers "why can't I read this"
├─ location state + action
└─ privacy policy, and the fact that there is no sign-in yet

TabBar
└─ Map | Unlocked (N) | You
```

**Unlocked memories are readable forever, and the server now holds the copy that
makes that true.** The local store is a cache; `GET /v1/unlocks` is what survives
the app's data being cleared. Signed out it is keyed on the keychain device id;
signed in, on every device of that account — which is the entire point of
sign-in and the only thing its copy is allowed to promise.

**Sign-in is never a gate.** Nothing in the app is behind it. A proximity app
that asks who you are before it shows you anything has the order wrong.

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
| `src/SourceLine.tsx` | who published a memory, with their avatar |
| `src/mapStyle.ts` | how the map gets out of the way |
| `src/reach.ts` | which pins look openable. Pure, and unit-tested |

## Tokens

**`src/theme.ts` is the only place colours and fonts are defined.** Import from
it; never write a hex or a font name inline. If you find yourself reaching for a
Tailwind value or the system font, that is the generic look coming back — see
[`docs/09-visual-design.md`](../docs/09-visual-design.md) part 5 for why this
palette exists at all.

**Every colour is a light/dark pair**, resolved by the platform. An app you use
outdoors at night, walking to a comedy club, cannot be light-only.

`DynamicColorIOS` is why dark mode is one file and not eleven: it returns a
colour the platform resolves at draw time, so `StyleSheet.create` at module
scope keeps working and no component needs a hook or a context. It is iOS-only —
**Android takes the light value** until somebody does the theme-context
refactor. That is a real gap, not a shrug; it is just not worth eleven files
while the app is iOS-first.

Two traps, both hit:

- `app.json` must say `"userInterfaceStyle": "automatic"`. It said `"light"`,
  which pins `useColorScheme()` to light forever and makes a correct dark
  palette look like dead code.
- A MapView `Circle` takes a real colour, not a platform-resolved one, so the
  reach circle branches on `useColorScheme()` by hand. Same for the map's own
  `userInterfaceStyle` and the `StatusBar`, which is `"auto"` — hardcoding it is
  how an app gets black glyphs on a black background.

**Dark is not the light palette inverted.** Paper becomes a warm near-black
rather than a grey, the seal *lightens* so it still reads as the one thing you
can act on, and `faded` lightens too — a locked pin has to survive a dark map,
where the light-mode value disappeared entirely.

**Ink and paper.** The app is an archive of anecdotes pinned to coordinates, so
it is built to look like a field guide rather than a dashboard.

| Token | Hex | Used for |
|---|---|---|
| `paper` | `#F7F4EE` / `#161412` | every surface. Not white, and close to the muted map underneath |
| `paperRaised` | `#FFFDF9` / `#201D19` | the rare surface that must lift off the paper |
| `ink` | `#1C1917` / `#F2EDE4` | primary text, solid buttons |
| `inkSoft` | `#4A443D` / `#BDB5A8` | secondary prose |
| `inkFaint` | `#8A837A` / `#8A8276` | labels, captions |
| `rule` | `#E0D9CC` / `#332E27` | hairlines. Rules do the work shadows used to |
| `faded` | `#776E64` / `#9A9086` | a locked pin out of reach. Dark enough for parchment, light enough for a dark map |

**One accent, and it means one thing.**

| Token | Hex | Meaning |
|---|---|---|
| `seal` | `#C0462B` / `#E2603F` | **openable.** The reach pill, the unlock ring, the in-reach pin. Nothing else, ever |
| `sealSoft` | `#F0D9CE` / `#4A2418` | the ring filling during a hold |
| `sealDeep` | `#8F2F1B` / `#F2A88F` | the padlock inside the ring, the count tag on a reachable pin |

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

**Spread it — `{ ...label }` — rather than retyping its five properties.**
Copying a token is how it stops being one: this voice was hand-retyped across
most of the app at one point and the tracking had already drifted between 1.0,
1.1 and 1.2 before anybody noticed, because nothing about five repeated lines
says they were meant to match.

`theme.ts` exports two more composites for the same reason. **`buttonText`** is
the label voice one step up in size and tracking — 12px, 1.2 — because it is the
thing being pressed; pair it with `color.paper` on ink and `color.ink` on an
outline. **`input`** is the whole text-field block, which renders in both You
and Submit and must not drift between them.

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

Except that the POI half has never actually applied: `App.tsx` passes
`showsPointsOfInterests`, with one `s` too many, and react-native-maps ignores a
prop it does not know. `mutedStandard` has been doing that work alone. Fixing
the spelling will visibly change the map, so it is a change to look at rather
than to land blind.

## Spacing, radii and the two shadows

`theme.ts` names colour and type and stops there, so every padding and every
corner is a literal at its call site. The table below is a census of what those
literals actually are — not a scale imposed over them — taken so that a new
screen can match the existing rhythm instead of inventing a neighbouring value.
Match a row; do not add one between two rows.

| Step | Where it is |
|---|---|
| 2 | baseline nudges: the gap inside a byline, the tab badge's vertical padding |
| 4 | tag padding, the gap between the pause bars |
| 6 | inside a collection row, inside the filed-at card |
| 8 | the default small gap: between tags, a stat and its label, stacked buttons |
| 10 | field label to input, the meta row under a place name |
| 12 | **the most common gap**: sheet actions, section contents, avatar to text |
| 14 | input and audio-row padding, the meta row's horizontal gap |
| 16 | the pill's horizontal padding, a floating card's distance from the edge |
| 18 | a rule to the content under it — a byline, a source line, a You section |
| 20 | the sheet action bar, Submit's body |
| 22 | the sheet body's top padding, the empty-area card |
| 24 | **the screen gutter.** Collection, You and the sheet all indent by this |
| 26 | the sheet's section rhythm, and the gap between collection rows |

Anything above 26 is a one-off (36 between the stats, 38 above a You section,
72 of bottom padding) and stays a literal.

**Corners**, all of them:

| Radius | On |
|---|---|
| 2 | the modal grabber, and nothing else |
| 3 | the small enclosed labels: tags, submission chips, the tab count badge |
| **4** | **the app's radius** — buttons, inputs, photos, thumbnails, the banner, the reach pill. Reach for this first |
| 6 | the two cards that float over the map, and only those |
| half the side | genuinely circular things only: the 84 hold ring, the 44 pager step, an avatar, a pin |

**The two shadows**, in full, because there are only two and a third one is a
rule you have not written yet:

| | Offset / radius / opacity | Android | On |
|---|---|---|---|
| card | `0,8` / 18 / 0.14 | `elevation: 6` | the location primer and the empty-area card |
| locate | `0,6` / 14 / 0.18 | `elevation: 5` | "Near me" — tighter and darker, because it is a small solid shape rather than a sheet of paper |

## Contrast, measured

Checked against the grounds each colour is actually used on, in both themes.
Most pairs pass comfortably; two facts are worth knowing before you reach for a
token.

| Pair | Light | Dark |
|---|---|---|
| `ink` on `paper` | 15.4:1 | 14.2:1 |
| `inkSoft` on `paper` | 8.8:1 | 8.5:1 |
| **`inkFaint` on `paper`** | **3.4:1** | 4.9:1 |
| `faded` on `paper` | 4.6:1 | 6.0:1 |
| `paper` on `seal` | 4.6:1 | 5.3:1 |
| `paper` on `faded` | 4.6:1 | — |
| `sealDeep` on `paper` / on `sealSoft` | 7.4:1 / 6.1:1 | — |

**`inkFaint` misses AA in light**, at 3.4:1, and it carries the label voice —
which is set at 9 to 11px, where the floor matters most. It passes in dark
(4.9:1), so this is a light-mode-only failure and easy to miss on a phone at
night, which is when this app is used.

It is the shipped value and it stays that way until somebody decides otherwise.
Where a label has to pass, **use `faded`**: 4.6:1 light and 6.0:1 dark, the same
warm family, and it already exists. It is not a new colour, it is the one next
to it.

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
10. **Never fetch alongside `animateToRegion`.** It fires
    `onRegionChangeComplete` when it lands, and it does *not* land on the region
    you gave it — the map fits the deltas to the screen, so the settled viewport
    covers noticeably more ground. Moving the camera and calling `load()` in the
    same breath is two requests for one action, the first of them for a
    viewport that never exists. Move the camera; let it report back.
    The one exception is the denied-permission path, which never moves the
    camera and so must load by hand.

## Writing

`Submit.tsx` is the only screen in the app that writes, and three of its rules
are not preferences:

- **It files where you are.** One coordinate, straight from the GPS, used as
  both "where I am" and "where this goes". There is no map picker and there is
  not going to be one - a memory you can pin from your sofa is a pin, and the
  whole product is the difference. With no position the sheet does not open; the
  press asks for location instead.
- **Attachments upload while you type**, not on Post. A phone photo is 4 MB and
  the wait belongs in the part where somebody is composing. Post stays disabled
  while an upload is in flight, and a failed one shows as failed rather than
  disappearing.
- **Tags are a closed list** (`SUBMISSION_TAGS`, mirrored from the API). The
  server drops anything not on it, so a free-text field would silently eat what
  somebody typed. Change it in both places or it is a lie in one of them.

A submission comes back already unlocked and its sheet opens over the map. The
modal closing is not a confirmation, and it is also the first sight of what a
stranger will find at that spot.

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

Writing is F5 (file a memory), F20 (report one) and F21 (be somebody).
Sign-in is F22, and it is Google and Apple only — see `src/SignIn.tsx` for why,
and for why neither button works in Expo Go.
