# UI guide

For agents working in `mobile/`. Three tabs, four modals and one mechanic; this file
says what it looks like, why, and how to check you did not break it.

Read this before changing anything under `mobile/src/` or `App.tsx`.

## The app today

One screen, four modals.

```
MapView (full bleed)
├─ Marker per coordinate      tap -> MemorySheet.  Five states, see Markers
├─ banner  "N memories here"  top centre, non-interactive
├─ "N within reach"           seal red, breathing, tap -> the nearest unlockable
│    or "Nearest locked · 412 m"   muted and still, when none is in reach
├─ "+ Add"                    top right, opens Submit. See "Writing"
├─ "Near me"                  bottom centre, recentres on GPS
└─ LocationPrimer             bottom card, only until permission is settled

MemorySheet (pageSheet modal) - two compositions, not one with holes in it

  locked                            open
  ├─ place name       26/700        ├─ place name       26/700
  ├─ "locked"         13, muted     ├─ distance
  ├─ padlock                        ├─ summary  17/26 - the hero
  ├─ distance         44/700        ├─ photo / recording   if it has any
  ├─ "Get within 150 m"             ├─ tags     pills
  ├─ "1 attachment waiting"         ├─ "Filed by X", or the channel and avatar
  ├─ "Walk there"     outlined      ├─ "Edit this memory"  own submissions only
  └─ or, in reach: the ring         └─ "Watch at 12:04"  ink, YouTube at the second

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
└─ privacy policy, and what signing out does and does not delete

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
| `src/MemoryMarker.tsx` | a coordinate's five states, and its layer's shape |
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
· 19/31 prose (the summary — the hero when nothing is attached) · 16/25 prose (body)
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

**`showsPointsOfInterests` is spelled correctly.** The plural is
react-native-maps' own name for the prop, all the way down to `AIRMap.mm`, which
then sets Apple's singular `showsPointsOfInterest` on the `MKMapView`. It reads
like a typo, tsc will confirm the plural, and "correcting" it silently turns POI
suppression off — the library drops a prop it does not know. Left alone.

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

Every pair below is a real one — the token on the left is set as text, or as a
mark that carries meaning, on the ground to its right — and every one clears
WCAG AA in **both** themes. `tests/test_palette.py` reads these values straight
out of `theme.ts` and fails if any pair drops under 4.5:1, so this table cannot
quietly go stale.

| Pair | Light | Dark |
|---|---|---|
| `ink` on `paper` | 15.9:1 | 15.8:1 |
| `inkSoft` on `paper` | 8.8:1 | 9.0:1 |
| `inkFaint` on `paper` | 4.6:1 | 5.3:1 |
| `inkFaint` on `paperRaised` | 5.0:1 | 4.8:1 |
| `faded` on `paper` | 4.6:1 | 5.9:1 |
| `paper` on `seal` | 4.6:1 | 5.2:1 |
| `paper` on `faded` | 4.6:1 | 5.9:1 |
| `sealDeep` on `paper` | 7.4:1 | 9.4:1 |
| `sealDeep` on `sealSoft` | 6.0:1 | 6.9:1 |

**`inkFaint` moved in both themes to get here**, and the way it failed is worth
keeping. The light value was `#8A837A` — 3.4:1, well under AA, on the colour
that carries the 9–11px label voice. The dark value was `#8A8276`, which cleared
AA on `paper` at 4.8:1 and missed it on `paperRaised` at 4.4:1 — and
`paperRaised` is where the text inputs and the audio row sit.

Neither was going to be caught by eye. A light-mode-only failure is invisible to
anyone reviewing an app built to be used outdoors at night, and the second one
only appeared on one of two grounds. That is the argument for the test rather
than for a careful look.

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
2. **Location is foreground-only, on both platforms.** `ACCESS_BACKGROUND_LOCATION`
   is blocked in `app.json`; on iOS the three keys expo-location injects by
   default — `NSLocationAlwaysAndWhenInUseUsageDescription`,
   `NSLocationAlwaysUsageDescription` and `NSMotionUsageDescription` — are each
   set to `false` in the plugin's options, which deletes them from the
   Info.plist. Both halves are asserted by `tests/test_app_config.py`.

   **The iOS half was missing until the first native build.** `app.json` set
   only the when-in-use string, and the plugin filled the other three with its
   own boilerplate ("Allow MemoryLane to access your location"), so the built
   app declared always-on location and motion for features it does not have. A
   purpose string is what review reads as intent. Nothing caught it because the
   Android side *was* handled, which made the pair look done — and because the
   test read `app.json` rather than the generated plist. If you add a config
   plugin, check what it put in the manifest:
   `plutil -convert xml1 -o - ios/MemoryLane/Info.plist`.
3. **Debounce map-driven fetches** (currently 400ms). Panning fires
   `onRegionChangeComplete` continuously; without it you DoS your own API.
4. **The API is radius-only.** `regionToRadiusKm()` circumscribes the viewport
   and clamps to 0.1–100km; outside that the API returns 422. There is no bbox
   endpoint.
5. **A memory with no coordinates cannot be drawn.** The API filters those out;
   do not assume `coordinates` is always present on types that allow null.
6. **`content.url` is already resolved.** The server points it at the document,
   or at the video's right second. Never rebuild a YouTube URL by hand.
   `content.timestamp_start` is null when the source is not a recording, and the
   button says "Open the source" instead of naming a second that does not exist.
7. **Never cover the map attribution.** The Apple Maps logo and Legal link in
   the bottom-left corner are a condition of using the map and have to stay
   visible and tappable. A floating tally in that corner is what made this a
   rule; the tab bar moved it out of the way.
8. **`onRequestClose` is required on every Modal**, or the Android back button
   does nothing.
9. **No tab unmounts.** Switching tabs uses `display: 'none'`, not a
   conditional render. Unmounting the map means refetching, losing the viewport
   and re-animating to GPS every time somebody glances at their collection.
10. **Never fetch alongside `animateToRegion`.** It fires
    `onRegionChangeComplete` when it lands, and it does *not* land on the region
    you gave it — the map fits the deltas to the screen, so the settled viewport
    covers noticeably more ground. Moving the camera and calling `load()` in the
    same breath is two requests for one action, the first of them for a
    viewport that never exists. Move the camera; let it report back.
    Two exceptions, both in code rather than in your head: the
    denied-permission path never moves the camera and so must load by hand, and
    `useMapCamera` reports a flight itself when the map does not — a long
    `animateToRegion` never lands audibly, so anything that flies you to
    another city needs the hook, not a `load()` of your own. See
    `docs/10-decisions.md#the-app`.
11. **The credit never scrolls.** Place name above the scroll, credit pinned
    below it, story in between. Geo-gated content cannot be shared by linking
    to it — you had to be there — so a screenshot is the only way it travels,
    and a screenshot that has lost the attribution is both a broken
    distribution channel and a broken legal posture. `styles.credit` in
    `MemorySheet.tsx` is that strip; it carries the one hairline, so the three
    credit variants inside it have none of their own. Anything new that can
    appear under a summary goes *in* the scroll, not between the two.

## Writing

`Submit.tsx` is the only screen in the app that writes, and three of its rules
are not preferences:

- **It files where you are.** One coordinate, straight from the GPS, used as
  both "where I am" and "where this goes". There is no map picker and there is
  not going to be one - a memory you can pin from your sofa is a pin, and the
  whole product is the difference. Declining location keeps the sheet shut and
  brings back the primer, which is the screen that explains why; location
  allowed but no fix yet opens it and says "Waiting for your location", because
  a button that does nothing for the three seconds a GPS takes is worse than
  one that tells you what it is waiting for. `ready` requires a position either
  way, so neither path can file from a sofa.
- **Attachments upload while you type**, not on Post. A phone photo is 4 MB and
  the wait belongs in the part where somebody is composing. Post stays disabled
  while an upload is in flight, and a failed one shows as failed rather than
  disappearing.
- **Tags are a closed list** (`SUBMISSION_TAGS`, mirrored from `api/write.py`,
  itself a subset of `pipeline/tags.py`). The server drops anything not in the
  vocabulary, so a free-text field would silently eat what somebody typed.
  `tests/test_api_submit.py` holds the app's copy equal to the server's - this
  used to be a convention and the two had already drifted.

Three things about the shape of it:

- **The story leads.** "What happened?" is the first field. Somebody opens this
  because something happened to them, not because they wanted to name a bench.
- **The rule under the header is the progress.** It fills as the two required
  fields land and turns seal when the thing can be posted - the same promise
  the unlock ring makes, and it costs a line rather than adding one. Under it,
  one hint, and only ever the next thing to do: "Say what happened here", then
  "Name the place", then "Ready to file". A greyed-out Post that does not say
  why is a dead end on the only screen that writes.
- **Every chip answers being touched** - `selectionAsync` and a spring, skipped
  on mount so the sheet does not flinch as it opens. The tick is the map's
  selection one, not the unlock's: this is picking, not earning, and it must
  not borrow that weight.

Anything the sheet offers has to be something Post can honour. Choosing
"Nobody until" and leaving the year blank used to file a memory anybody
standing there could read - the person said who may read it and was quietly
overruled - so the seal is computed once, by `sealOpensAt`, and both the draft
and the button read that one answer.

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
# 1. API, and memories you can actually reach
docker compose up -d --build
python -m pipeline.seed_dev            # --clear takes them away again

# 2. cp .env.example .env  (once). It carries EXPO_PUBLIC_DEV_LOCATION, which
#    pins the app's position to the seed under __DEV__ - so the Simulator's
#    location stops being something you set after every boot.
cd mobile && npx expo start --ios

# 3. pre-grant location, or the permission dialog covers the first screen
#    ("booted" is a literal simctl accepts - no need to look up a UUID)
xcrun simctl privacy booted grant location-always host.exp.Exponent
xcrun simctl location booted set 40.7484,-73.9857   # Manhattan: where the data is

# 4. screenshot it
xcrun simctl io booted screenshot /tmp/app.png
```

If the dialog still appears, terminate and relaunch — the grant applies at
launch: `xcrun simctl terminate booted host.exp.Exponent` then re-open the
`exp://` URL.

**Taps can be scripted now.** `./e2e/run.sh` drives the real app through the
flows in `docs/08-ux-flows.md` — including walking into range and holding the
unlock ring — and `--record` leaves an mp4. It seeds its own throwaway
database, so it does not disturb the corpus. Read `e2e/README.md` before
writing a flow; four of its rules are not guessable.

For a single screenshot the recipe below is still shorter than a flow.
`EXPO_PUBLIC_DEV_OPEN_MEMORY` opens one memory on launch, so every state the
sheet can render is reachable from a script:

```bash
python -m pipeline.seed_dev                      # prints the id of each state
EXPO_PUBLIC_DEV_OPEN_MEMORY=265 REACT_NATIVE_PACKAGER_HOSTNAME=localhost   npx expo start --dev-client                    # restart Metro; ids bake in
xcrun simctl launch booted com.PLACEHOLDER.memorylane
xcrun simctl io booted screenshot /tmp/sealed.png
```

What this recipe still cannot do by hand: press the unlock ring, or reach
anything below the fold. Both are what `./e2e/run.sh` is for — `f7` holds the
ring and `f5` fills in and posts the whole submit sheet.

**For the real build, not Expo Go**, which is what `W3-13` is about: Expo Go
shows its own permission copy and no native manifest.

```bash
cd mobile && npx expo run:ios     # builds, installs, launches, then exits
```

It bakes the LAN IP into the launch URL and exits with Metro, so start Metro
yourself afterwards with `REACT_NATIVE_PACKAGER_HOSTNAME=localhost` and
`xcrun simctl launch` — the dev client remembers the last URL it loaded. Do not
re-open the `com.PLACEHOLDER.memorylane://` URL by hand: the "Open in Memory
Lane?" system alert it raises cannot be dismissed without a tap and sits over
every screenshot until the simulator is rebooted.

**Use `localhost` for the simulator, a LAN IP only for a physical phone.** Expo
bakes `EXPO_PUBLIC_API_URL` in at dev-server start, so if you pass your LAN IP
and then change network, the app silently shows "0 memories here" with no error
— the map still works, it just cannot reach the API. Restart the dev server
rather than debugging the app. Likewise `exp://<stale-ip>:8081` hangs on
"Opening project"; `exp://localhost:8081` does not.

Only one dev server can hold port 8081, and `npx expo start` cannot prompt in a
non-interactive shell — it just prints "Skipping dev server". Kill the old one
first: `lsof -ti:8081 | xargs kill -9`.

**Without the seed you cannot exercise the unlock at all**, and moving the
Simulator does not help. Every dense point in the real corpus is a model-guessed
centroid and therefore deliberately ungated (F7), and the memories that *are*
gated are the scattered ones — so the nearest thing you could open is kilometres
from any round-number coordinate. `pipeline/seed_dev.py` plants one of every
state at `FALLBACK_REGION`: one in reach, one 400m away, a stack, an open
centroid pair, and one filed by a person with a photo and a recording.

The real corpus is a US comedy podcast — from Copenhagen you will correctly see
an empty map and think you broke something.

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

One marker is a *coordinate*, not a memory and not a place. 121 of 215 placed
memories sit on 28 shared coordinates, so a marker routinely stands for several
memories at several venues. A group of more than one carries a count badge, and
the sheet pages through it with "1 of 23 here".

Group in `src/cluster.ts`, never in the component — it is pure and unit-tested,
and the Times Square centroid is one of the test cases. `precisionFor()` makes
the grid follow the zoom, in four bands rather than continuously: `region`
changes on every gesture, ahead of the fetch debounce, so a precision derived
from the raw delta would regroup every frame.

A group carries `spanMeters`, the furthest a memory in it sits from the point
they are all drawn on. Zero at a genuine shared centroid, kilometres once the
grid loosens. Past `CLUSTER_SPAN_M` a tap **zooms instead of opening a sheet** —
paging through venues miles apart is not "1 of 23 here", it is a lie.

### The ink ladder

A pin is a stamp impression on paper. Two axes compose, and nothing else does:
the **ink state** is your relationship to the coordinate, the **shape** is which
layer it belongs to. The state has to be on the pin, because otherwise you learn
a pin is unreadable only by tapping it.

The walk, at the server's default 150 m gate. Distance is measured from the
person to the nearest locked memory in the group, so these are real thresholds
and not map distances:

```
   over 450m        450 - 150m         inside 150m        after the hold
    locked     ->      warm      ->     unlockable   ->      stamped
  faded disc      paper disc,        seal ring 44px      ink disc, ring
  + padlock       ink edge+lock      + halo + tag        inside. Permanent.
```

Every measurement, because the alternative is six numbers drifting apart in one
StyleSheet. `WARM_MULTIPLIER = 3` and the radius is always the server's.

| State | When | Geometry | Tokens |
|---|---|---|---|
| `plain` (one) | never gated | dot 18px, radius 9, border 2 | fill `ink`, edge `paper` |
| `plain` (several) | never gated, a stack | badge min-w 26, h 26, radius 13, border 2, pad-x 6 | fill `ink`, edge + count `paper` |
| `stamped` | you walked here and opened it | disc 28, radius 14, border 2; impression 14, radius 7, border 2 | fill `ink`, edge + impression `paper`, count tag `ink` |
| `warm` | locked, inside 3x the radius | disc 28, radius 14, border 2; padlock 9.52 | fill `paper`, edge + padlock + count `ink` |
| `locked` | locked, further than that | disc 28, radius 14, border 2; padlock 9.52 | fill `faded`, edge + padlock `paper` |
| `unlockable` | locked, inside the radius **and openable by walking** | ring 44, radius 22, border 5; tag min-w 20, h 20, radius 10, border 2 | edge `seal`, fill `paper`, tag `sealDeep`, wash `halo` |

**A seal is not a distance, and the ladder does not apply to one.** A
time-locked memory (F23) is `locked` at every distance, so it draws `locked`
wherever you stand. `isSealed` in `src/reach.ts` is the one predicate; it is
checked there rather than in the component because three separate things ask
"can this be opened from here" — the pin's ink state, the within-reach banner's
count, and the walk hint — and a seal answered yes to all three. It was `locked`
and it was 128 m away, so the pin wore the seal ring, the banner counted it, and
`nearestLocked` (which returns null the moment anything is `unlockable`) could
suppress the hint pointing at a pin somebody genuinely could reach. Grey is not
a perfect reading of "shut until 2031" — but it is true, and it needs no new
visual language. Marked `ponytail:` in `reach.ts` if it ever earns its own mark.

The card shape swaps the radius only — 2 on the dot, 3 on the badge and disc, 4
on the ring — and adds a 9px fold at the face's top right corner. The fold is
`paper`, drawn as a border triangle on a 0x0 view.

**The padding is the tap target, not decoration.** A 28px disc is 28px of
hittable pin and Apple's floor is 44, so every state carries a wrap: 9px around
the 28 and 44px faces, 14px around the 18px dot. Both land at 46, which also
makes the stacked pins downtown separable by thumb rather than by luck.

**`warm` is ink and not seal**, and that is the rule that keeps the accent
honest. `seal` means *openable now*; a seal-red pin you cannot open is an
invitation that refuses you. F11 says the same thing about the pill: "'Walk
400 m' is information; only something you can actually open is an invitation."
The ladder still reads as a gradient because value and weight carry it — faded,
then an ink outline, then a seal ring.

**`stamped` is what the map is for.** Until it existed, a memory you walked to
and earned drew identically to one that was never gated, so the collection left
no mark on the map at all. The mark is a ring inside the disc — a small copy of
the ring you held to open it, `paper` on `ink`, the same pair the count already
uses. It is permanent: `src/unlocked.ts` is the source of truth and survives
walking away, a restart and a reinstall. `reachOf` needs the earned set passed
in to draw it, because `/v1/memories/nearby` never takes a position and reports
earned and never-gated memories identically.

**Shape is the layer**, which is how F4 gets answered without new chrome:
`historical` is round, `stranger` is a card — square corners and a turned-down
top right, drawn with the border-triangle trick because there is no SVG here.
The fold is opaque on purpose; a real notch needs clipping, and a transparent
wedge over a street map reads as a rendering fault. A mixed group falls back to
round rather than claiming the stack for one layer.

**Anchor every marker `{ x: 0.5, y: 0.5 }`.** iOS centres a custom view on the
coordinate already, but Android defaults to bottom-centre whatever you draw, so
without it every pin hangs its own height above the point it names — which was
~70 m at street zoom, and meant the ring you were standing inside was not
centred on you.

Custom views are never decluttered: `displayPriority` collision-hiding only
applies to the default pin, which the ink dot replaced. Density is now
clustering's job, not MapKit's.

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

A group is locked if any memory in it is — anything left to open outranks
anything already earned, because a marker with something behind a gate is an
invitation and not a souvenir. `reachOf()` in `src/reach.ts` measures from the
*person*, never from the map centre — panning to another city must not make its
pins look reachable — and to the **nearest locked memory in the group**, never
to the point they are drawn on. That point is a rounded coordinate; once the
grid loosens with the zoom it can sit kilometres from everything under it, and
measuring to it would say "walk a kilometre" while you stand on the thing.

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
- **The fill is linear, and stays linear.** It is a promise about when you may
  let go, and an eased progress bar is a progress bar that lies. Everything
  that builds is layered over it rather than baked into it, which is the only
  way to have both suspense and an honest instrument.
- **Haptics carry the feel, and they accelerate.** `Light` on press-in, then
  `Soft` at 340ms, `Light` at 590ms and `Rigid` at 780ms — gaps closing, taps
  sharpening — and `notificationAsync(Success)` at the end. 900ms of silence
  is a long time to wonder whether a control is working, and the closing
  tempo is where the anticipation comes from while the ring stays truthful.
  `Success` is reserved: it is the one pattern in the app that means a thing
  was earned. Never on release-cancel, which would read as a reward for
  failing. One more `Light` fires in `App.tsx` the moment the reachable set
  goes empty to non-empty — walking into range is the moment the app is for,
  and it used to happen in silence. The transition, not the state:
  `withinReach` gets a new array identity every 25 m, so the effect keys on a
  boolean and a ref, not on the array or its length.
- **The last quarter strains.** An inner ring fades up and closes in from 78%,
  arriving with the third tick, and the padlock swells as it is worked. Both
  are interpolations of the same value the fill uses, so they cost one
  animation and cannot drift out of sync with it.
- **The burst plays over the request, not after it.** A completed hold fires
  the unlock and the flare in the same frame, so the round trip happens behind
  something worth watching. The payoff proper is not here — it is the wax
  stamp coming down in `MemorySheet`, and this hands off to it.
- **Transform and opacity only.** Those are what `useNativeDriver` can carry;
  an animated colour puts the whole control back on the JS thread for the
  900ms it most needs to be smooth.
- **A refusal resets the ring.** Success unmounts the control — the sheet
  swaps to its open composition — so `busy` falling back to false is always a
  no, and a ring left full beside an error reads as "it worked".
- **The walk in is the same ring.** Out of reach, `src/Approach.tsx` draws the
  same 84px circle with a rim that thickens inward as you close — empty at
  three radii (`WARM_MULTIPLIER`, so the sheet and the pin agree about
  "nearly"), complete at the radius. Arriving swaps it for the control, and
  the ring you were filling is the ring you now hold. Two rules hold it
  together: it is never seal, because seal means openable and this cannot be
  opened from here; and it fills a **rim** and not the middle, because the
  middle belongs to the hold — an approach that filled the centre would make
  arriving look like the ring draining just as you got there. `approachOf` is
  in `reach.ts` with the rest of the distance logic, and is unit-tested.
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
`POST /v1/memories/{id}/unlock` and the server re-measures, so a
completed hold can still come back refused when GPS has drifted. Say so —
"Not close enough yet" — rather than leaving a control that looks broken.

## Flows

Documented flows live in `docs/08-ux-flows.md`. Build toward those, and when a
flow changes, change that file in the same commit.

Writing is F5 (file a memory), F20 (report one) and F21 (be somebody).
Sign-in is F22, and it is Google and Apple only — see `src/SignIn.tsx` for why,
and for why neither button works in Expo Go.
