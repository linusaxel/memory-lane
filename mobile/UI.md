# UI guide

For agents working in `mobile/`. Three tabs, four modals and one mechanic; this file
says what it looks like, why, and how to check you did not break it.

Read this before changing anything under `mobile/src/` or `App.tsx`.

## The app today

Three stages, one map, four modals. The stage is plain state in `App.tsx`
(`'loading' | 'plan' | 'preview' | 'walk'`); the map stays mounted through all
of them (rule 9).

```
Plan (src/Plan.tsx)            opaque page over the mounted map; no tab bar
├─ "How far today?"            34/700
├─ "4 km"                      the slider's value, mono 30
├─ slider                      1-10 km, 0.5 steps (WALK_KM)
└─ "Show me the walk"          ink button; asks for location, then previews

Preview                         the map, fitted to the start and every stop
├─ Marker per stop, numbered   not tappable - a look, not a walk
├─ the loop, drawn             RouteLine from the start and back
└─ card (Preview)              "5 stops · 3.8 km loop", Accept / Change length;
     "No walk that long from here"; "Planning from Midtown…" with no position

MapView (the walk, full bleed)  only today's accepted stops, nothing else
├─ Marker per stop            tap -> MemorySheet.  One pin, see Markers
├─ "+ Add"                    top right, opens Submit. See "Writing"
├─ "Today's route · N of 5 · 2.4 km"   bottom centre, above Near me;
│    "Next: <place> · 350 m" once started, "Route walked · 5 of 5" when done,
│    "You're at stop N · open it" seal and breathing while standing at any stop
└─ "Near me"                  bottom centre, recentres on GPS

MemorySheet (pageSheet modal) - two compositions, not one with holes in it

  locked                            open
  ├─ place name       26/700        ├─ place name       26/700
  ├─ "locked"         13, muted     ├─ distance
  ├─ padlock                        ├─ summary  17/26 - the hero
  ├─ distance         44/700        ├─ photo / recording   if it has any
  ├─ "Get within 20 m"              ├─ tags     pills
  ├─ "1 attachment waiting"         ├─ "Filed by X", or the channel and avatar
  ├─ "Walk there"     outlined      ├─ "Edit this memory"  own submissions only
  └─ or, in reach: the ring         └─ "Watch at 12:04"  ink, YouTube at the second

  The locked side says how many attachments are waiting and never which. A
  photograph of the place is the memory as much as the text is.

Submit (pageSheet modal, from "+ Add") - see Writing

Memories (the second tab, src/Memories.tsx)
└─ Unlocked: what this device has earned, newest first; a row opens the sheet.
   My memories: what you filed

Settings (the third tab, "You")
├─ unlocked / places / filed, as numbers
├─ your name                what submissions are signed with. Blank = Anonymous
├─ account                  Apple / Google. Never a wall; see SignIn.tsx
├─ how unlocking works      the one place that answers "why can't I read this"
├─ location state + action
└─ privacy policy, and what signing out does and does not delete

TabBar                         hidden on the map until the walk is accepted
└─ Map | Memories (N) | You
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
| `src/MemoryMarker.tsx` | one pin, lit when it can be opened from here |
| `src/UnlockButton.tsx` | the hold, the ring, the haptics |
| `src/Plan.tsx` | the plan page and the preview card: how far, then accept |
| `src/useBreath.ts` | the only thing on the map that animates, the "at a stop" pill |
| `src/Memories.tsx` | what the walking was for |
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
| `seal` | `#8A5A17` / `#D9A54B` | **openable.** The reach pill, the unlock ring, the in-reach pin. Nothing else, ever |
| `sealSoft` | `#F0E4C8` / `#3D3018` | the ring filling during a hold |
| `sealDeep` | `#5C3A0E` / `#F0C878` | the padlock inside the ring, the count tag on a reachable pin |

The watch button is **ink**, not the accent. It was YouTube red back when the
map pins were red too; that stopped being true, and the accent is spoken for.

**Shipped 2026-09-23: `seal` moved from a stamp red to a warm ochre**
(`TODO.md`'s founder-brainstorm "warm accent, not a reskin" - hybrid, not a
reskin of the palette: the map style, card layout and type system are
untouched, only this one accent moved). `sealSoft`/`sealDeep` moved with it as
the same ramp, `halo` (below) and the two hardcoded map-`Circle` colours in
`App.tsx` (which cannot take a `dual()` value - see "Light and dark" above)
were updated to match, and `api/card.py`'s `--accent` copy was updated
alongside `theme.ts` so `tests/test_palette.py`'s
`test_the_card_uses_the_apps_palette` still holds. Every contrast pair below
was re-measured against the new hex values before this shipped, same
requirement as before.

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
"Near me" and the preview card, which genuinely hover over a map; both carry
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
| card | `0,8` / 18 / 0.14 | `elevation: 6` | the preview card |
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
| `paper` on `seal` | 5.4:1 | 8.3:1 |
| `paper` on `faded` | 4.6:1 | 5.9:1 |
| `sealDeep` on `paper` | 9.3:1 | 11.6:1 |
| `sealDeep` on `sealSoft` | 8.1:1 | 8.1:1 |

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
| `FALLBACK_REGION` | `0.09` | 10 km | Before anything is known; its centre is the Midtown planning anchor |
| `LOCATED_DELTA` | `0.01` | 1.1 km tall | Centred on the person |

Landing on the person at street scale is the whole point: at 10 km a 20 m
unlock radius is less than a pixel and the mechanic is invisible, so the app reads as
a map of things you cannot have. At 1.1 km the reach circle is about a quarter
of the screen and "walk two blocks" is a visible distance.

The preview ignores both: it fits the map to the start and every stop
(`fitToCoordinates`), which is the zoom that shows a whole walk.

**The reach circle** is drawn once, around the person, at the server's radius —
never around each pin, which would be fifteen overlapping circles and no
information. It is `seal` at low opacity: present, and never competing with the
pins it is there to qualify. No position, no circle.

Nothing is fetched by viewport any more: the map draws the walk's stops and
nothing else, so panning never asks the server anything.

## Rules that are load-bearing

Each of these exists because something broke or would have been rejected.

1. **Never show a blank grey map, or a dead end.** With permission denied the
   walk is planned from Midtown (`FALLBACK_REGION`'s centre) and the preview
   says so, because store reviewers routinely tap Deny and an empty map is a
   rejection. Any new view needs the same treatment: an empty state that still
   shows something real.
2. **Location is foreground-only by default, and background is opt-in, single-purpose,
   and explicit.** `ACCESS_BACKGROUND_LOCATION` is a named line in `app.json`'s
   Android allowlist, not a side effect of some other permission; on iOS
   `NSLocationAlwaysAndWhenInUseUsageDescription` is a real, specific purpose
   string. Both exist for exactly one feature — the proximity notification
   (`geofence.ts`, Settings.tsx's "Notify me when a memory is nearby" toggle,
   off unless the person turns it on) — and nothing else in the app asks for
   position while it is not open. The other two keys expo-location can inject —
   `NSLocationAlwaysUsageDescription` (the pre-iOS11 fallback, not needed for an
   app that only supports iOS 13+) and `NSMotionUsageDescription` (no motion
   feature) — stay `false` in the plugin's options, which deletes them from the
   Info.plist. All of this is asserted by `tests/test_app_config.py`.

   **The iOS half was missing until the first native build**, before the
   proximity notification existed. `app.json` set only the when-in-use string,
   and the plugin filled the other three with its own boilerplate ("Allow
   MemoryLane to access your location"), so the built app declared always-on
   location and motion for features it did not have. A purpose string is what
   review reads as intent. Nothing caught it because the Android side *was*
   handled, which made the pair look done — and because the test read
   `app.json` rather than the generated plist. If you add a config plugin,
   check what it put in the manifest:
   `plutil -convert xml1 -o - ios/MemoryLane/Info.plist`.

   **Shipped 2026-09-23** (`TODO.md`'s "Ideas — founder brainstorm" section,
   the proximity-notification half of "streak + proximity notification,
   reopened" — the streak half, F27, needed none of this). Code and config are
   both in; what has **not** happened yet is a real device verifying the
   background delivery end to end, or updating the actual App Store Connect /
   Play Console listings — that is a human step, not a gate the pytest suite
   can pass. `isIosBackgroundLocationEnabled` was deliberately left `false`:
   geofencing is CoreLocation region monitoring, which wakes the app on its
   own and does not need continuous `UIBackgroundModes: ["location"]` the way
   `startUpdatingLocation` in the background would — asking for the stronger
   capability than the feature needs is exactly the kind of over-declaration
   this rule exists to prevent.
3. **Retired: debounce map-driven fetches.** Nothing is fetched by viewport any
   more; the map draws only today's walk. If a map-driven fetch ever returns,
   so does the debounce - panning fires `onRegionChangeComplete` continuously.
4. **Retired: the API is radius-only.** Same reason. `/v1/memories/nearby`
   still clamps `radius_km` to 0.1–100 for anyone else who calls it.
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
    covers noticeably more ground. Nothing fetches on a move today, but the
    region `useMapCamera` reports is what pins group by, so move the camera
    and let it report back; the hook also reports a long flight itself, which
    never lands audibly. See `docs/10-decisions.md#the-app`.
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
  whole product is the difference. Declining location opens it without a position,
  and it says "Waiting for your location" and holds Post; location allowed but
  no fix yet opens it and says "Waiting for your location", because
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
and then change network, the plan page says "Can't reach Memory Lane right
now." — the app still works, it just cannot reach the API. Restart the dev server
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

The real corpus is a US comedy podcast — from Copenhagen the preview will
correctly say "No walk that long from here" and you will think you broke
something.

Pure map maths goes in `src/region.ts` with a `node --test` case beside it;
the gate runs `mobile/src/*.test.ts`. Component behaviour is currently untested
and there is no RN test runner installed — do not add one without asking.

## States

The app has four stages (`App.tsx`'s `Stage`), and they must stay distinct:

| Stage | Shows | Leaves by |
|---|---|---|
| loading | paper, while the cache and `GET /v1/routes/today` answer | a walk found → walk; none → plan |
| plan | "How far today?" and the slider | "Show me the walk" → preview |
| preview | the walk on the map, the card | Accept → walk; Change length → plan |
| walk | today's stops, the pill, the tabs | nothing - the day is locked |

A failed request on plan or preview leaves you there with "Can't reach Memory
Lane right now." under the button. With no location permission the walk's button
reads **"Turn on location"** instead of "Near me": nothing can unlock without a
position, and a walk of pins that never open with no explanation is the worse
bug. Requests time out after `REQUEST_TIMEOUT_MS` (8s) in `src/api.ts`.

## Markers

One marker is a *coordinate*, not a memory and not a place. 121 of 215 placed
memories sit on 28 shared coordinates, so a marker routinely stands for several
memories at several venues. A group of more than one carries a count badge, and
the sheet pages through it with "1 of 23 here".

Group in `src/cluster.ts`, never in the component — it is pure and unit-tested,
and the Times Square centroid is one of the test cases. `precisionFor()` makes
the grid follow the zoom, in four bands rather than continuously: `region`
changes on every gesture, so a precision derived from the raw delta would
regroup every frame.

A group carries `spanMeters`, the furthest a memory in it sits from the point
they are all drawn on. Zero at a genuine shared centroid, kilometres once the
grid loosens. Past `CLUSTER_SPAN_M` a tap **zooms instead of opening a sheet** —
paging through venues miles apart is not "1 of 23 here", it is a lie.

### One pin

Every coordinate draws the same pin: a 24px `ink` disc, 2px `paper` edge, an
8px `paper` eye in the middle. It changes for one reason only — **it can be
opened from where you stand**, and on a route day only if it is one of the
route's stops (F25) — and then it grows to 32px in `seal`, eye 12px,
over a `halo` wash. That is the whole visual language. Simplified 2026-09-23
from five ink states, a round-or-folded-card shape per layer and a ranked
corner slot of padlock and tag glyph: it was a legend nobody should need.

| When | Geometry | Tokens |
|---|---|---|
| every pin | disc 24, border 2; eye 8 | fill `ink`, edge + eye `paper` |
| `unlockable`: inside the radius **and openable by walking** | disc 32, border 2; eye 12; wash 46 | fill `seal`, edge + eye `paper`, wash `halo` |
| a stack, or one of today's stops | tag min-w 20, h 20, radius 10, border 2, top right | `ink` (`sealDeep` on a lit pin), count `paper` |

**The eye is the point.** The pin you can open is the pin you are standing on,
so the blue location dot lands in the hole rather than disappearing under a
disc. The badge sits in the corner for the same reason.

**`seal` means openable now, and nothing else.** A seal-coloured pin you
cannot open is an invitation that refuses you (F11). Locked near, locked far,
earned and never gated all draw the same ink pin; the difference is in the
marker's `title` (VoiceOver and Maestro still hear every state from
`STATE_LABEL`) and in the sheet. `reachOf` in `src/reach.ts` still computes all
five, because the banner and the walk hint need them.

**A seal is not a distance.** A time-locked memory (F23) is `locked` at every
distance, so it never lights. `isSealed` in `src/reach.ts` is the one
predicate, checked there because the pin, the within-reach banner's count and
the walk hint all ask "can this be opened from here".

**The wrap is the tap target, not decoration.** Every pin sits in a 46px box,
over Apple's 44 floor, which also makes the stacked pins downtown separable by
thumb rather than by luck.

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
the "at a stop" pill (`useBreath`), which is not a marker.

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
65% after a primer. The plan page's "Show me the walk" is the ask: a press
with a reason, walks start from where you are, and only then the system dialog.
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
