# UI guide

For agents working in `mobile/`. One map, one journal, the modals and one mechanic; this file
says what it looks like, why, and how to check you did not break it.

Read this before changing anything under `mobile/src/` or `App.tsx`.

## The app today

Four stages, one map, four modals. The stage is plain state in `App.tsx`
(`'loading' | 'map' | 'plan' | 'preview' | 'walk'`); the map stays mounted through all
of them (rule 9).

```
SignInScreen (src/SignIn.tsx)  the first screen, and the only one until signed in
├─ the logo tile               where StartupLogo left it, at rest
├─ "Memory Lane"               34/700
├─ one line                   what the app is, 17 prose, inkSoft
├─ Apple's own button          white on the dark paper, black on the light
├─ "Continue with Google"      outlined; absent without a client id
└─ "Skip (dev build)"          __DEV__ only, so a release bundle has none

MapView (before a walk)        the first screen after sign-in, unless today's walk is accepted
├─ you, and the reach circle   centred on you, or central Copenhagen with no position
├─ Marker per locked memory    within 5 km (MAP_RADIUS_KM); tap -> MemorySheet's peek
└─ "Plan a walk"               ember glass capsule, bottom centre -> Preview, drawn at once

Preview (src/Plan.tsx)          the map, fitted to the start and every stop. Draw first, adjust after
├─ Marker per stop, numbered   not tappable - a look, not a walk
├─ the loop, drawn             RouteLine from the start and back, washed-out ember under labels so the pins pop
└─ card (Preview)              every change on it redraws the walk
   ├─ "A walk from here"        23/700, the × trailing; "A walk through <place>" from Walk here
   ├─ ‹ "4 stops · 3.8 km loop" ›   pages, 44pt each: no ‹ on the first, no › once none is left; "Finding a walk…" first; "No walk within 10 km from here."
   ├─ "Nothing at 4 km; this is the nearest."   an empty length moved up to one with a walk
   ├─ "Planning from central Copenhagen…"   with no position
   ├─ "4 km" + slider           1-10 km, 0.5 steps (WALK_KM), uncontrolled: redraws on release
   ├─ Loop · One way            Submit's Chip; One way adds "Pick where it ends"
   └─ Start walk

MapView (the walk, full bleed)  only today's accepted stops, nothing else. With a
│                              position the camera is pinned on you: it follows,
│                              does not pan or rotate, and a pinch stays centred
├─ Marker per stop            tap -> MemorySheet.  One pin, see Markers; the next one hops. No line
├─ "Journal"                  top left, every stage, preview included. Glass (src/Glass.tsx)
├─ You, Add                   top right, 44pt glass circles (YouGlyph, AddGlyph), every stage.
│                              You opens Settings; Add files a memory, no walk needed. See "Writing"
├─ "On a walk · 2 of 5"       top centre, the corners' capsule tinted ember: the walk's one
│                              signal, and a tap ends it (F34). With stops left, a card
│                              (EndWalk): "End this walk?", End walk / Keep walking. No system dialog
├─ NextStopArrow              ember, on the screen's edge, pointing at the next
│                              stop while it is off screen (src/NextStopArrow.tsx)
├─ "2.4 km to go"             bottom centre, no count (the bar has it); tap zooms out around
│    you to the next stop; "Next: <place> · 350 m" once started, "Every stop unlocked" when done,
│    "Unlock memory" seal while standing at any stop
├─ "Turn on location"         bottom centre, below the pill, only while there is no position
└─ card (WalkDone)            once, when the last stop's sheet closes: the map unpins and fits
                               the whole loop, drawn; "Nice walk." 34/700, "5 memories · 4.1 km
                               loop · 52 min", the streak, Done. A relaunch does not show it again

MemorySheet (pageSheet modal) - two compositions, not one with holes in it

  locked                            open
  ├─ place name       26/700        ├─ place name       26/700
  ├─ "within reach"   13, seal      ├─ distance
  ├─ padlock                        ├─ summary  17/26, #tags semibold
  ├─ distance         44/700        ├─ photo / recording   if it has any
  ├─ "Get within 20 m"              ├─ "Left by X", or the channel and avatar; the heart trailing on that line
  ├─ "1 attachment waiting"         │    (a count only, on your own memory)
  │                                 ├─ "Edit this memory"  own submissions only
  └─ or, in reach: the ring         └─ "Watch at 12:04"  ink, YouTube at the second

  peek (the map, before a walk: a card over the live map, sized to its content)
  ├─ place name
  ├─ "From Vega Archive", or a person glyph + "Left by Anna"   who, directly under the name
  ├─ #music  #nightlife      every tag, outline pills in displaySemi, under the name
  ├─ Approach ring  +  "472 m"  36/700      the lock as the distance still to go
  │                    "1978 · 12 hearts"   the year off the source line: it is when, not when published
  │                    "1 attachment waiting"
  └─ "Walk here"              ink, in the bottom bar; opens Plan for a walk through that pin (F1)

  The locked side says how many attachments are waiting and never which. A
  photograph of the place is the memory as much as the text is.

Submit (pageSheet modal, from Add) - see Writing

You (src/Settings.tsx, pageSheet modal, from You) - "You" 34/700, × top right, then the settings

Journal (src/Memories.tsx)     opaque, over the mounted map; × top right
├─ the streak, large           F27: days in a row with a walk stop unlocked. Not shown at 0
├─ Walks                       one row per walk that opened something, date and length;
│                              a row opens in place to its earned stops, numbered on a
│                              ember rail. An earned one opens the sheet. Cached for the train
└─ Memories                    what you added; a row opens Submit as the editor
   ├─ unlocked / places / added, as numbers
   ├─ your name                what submissions are signed with. Blank = Anonymous
   ├─ account                  which sign-ins, add the other, sign out (back to the gate)
   ├─ how unlocking works      the one place that answers "why can't I read this"
   ├─ location state + action
   └─ privacy policy, and what signing out does and does not delete

There are no tabs. Before a walk the map draws what is locked around you; on a
walk it draws only that walk. Only today's walk unlocks (docs/10, "A map of
what is locked, and only today's walk unlocks").
```

**Unlocked memories are readable forever, and the server now holds the copy that
makes that true.** The local store is a cache; `GET /v1/unlocks` is what survives
the app's data being cleared. Signed out it is keyed on the keychain device id;
signed in, on every device of that account — which is the entire point of
sign-in and the only thing its copy is allowed to promise.

**Sign-in comes first.** No account, no app: the first screen is Apple and
Google and nothing else, and signing out lands back on it (docs/10, *Sign-in
comes first*). Because nothing can be tried before it, that one screen has to
earn the tap on its own. The last answer is kept locally, so a signed-in person
with no network is never stopped at the gate.

| File | What it owns |
|---|---|
| `src/Padlock.tsx` | the one symbol, at any size, in any colour |
| `src/MemoryMarker.tsx` | one pin, lit when it can be opened from here |
| `src/UnlockButton.tsx` | the hold, the ring, the haptics |
| `src/Plan.tsx` | the preview card: a walk drawn at once, its length and shape, then accept |
| `src/useBreath.ts` | the next stop's hop |
| `src/Memories.tsx` | the journal: streak, walks, unlocked, and what you filed |
| `src/Settings.tsx` | You: name, account, how unlocking works. Its own sheet |
| `src/AddGlyph.tsx` | the Add button: an ember pin with a plus |
| `src/CloseButton.tsx` | the × that closes a card, sheet or page (rule 12) |
| `src/YouGlyph.tsx` | the You button: head and shoulders |
| `src/theme.ts` | **every colour, font, corner and the one shadow.** Start here |
| `src/Glass.tsx` | a control floating over the map: Liquid Glass, or paper and `lift` |
| `src/SourceLine.tsx` | who published a memory, with their avatar |
| `src/mapStyle.ts` | how the map gets out of the way |
| `src/reach.ts` | which pins look openable. Pure, and unit-tested |

## Tokens

**`src/theme.ts` is the only place colours and fonts are defined.** Import from
it; never write a hex or a font name inline. If you find yourself reaching for a
Tailwind value, that is the generic look coming back — see
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
- A MapView `Circle` or `Polyline`, an Svg fill and the splash take a real
  colour, not a platform-resolved one. They read `solid(dark)` from `theme.ts`
  with `useColorScheme()`, never a hex of their own. Same for the map's own
  `userInterfaceStyle` and the `StatusBar`, which is `"auto"` — hardcoding it is
  how an app gets black glyphs on a black background.

**Dark is not the light palette inverted.** Paper becomes a warm near-black
rather than a grey, ember *lightens* so it holds on a dark map, and `faded`
lightens too — a locked pin has to survive a dark map, where the light-mode
value disappeared entirely.

**Warm and rounded** since 2026-09-27 (`docs/09-visual-design.md` part 8):
paper and one rounded face, one warm accent, capsules, and glass only over the map.

| Token | Hex | Used for |
|---|---|---|
| `paper` | `#F7F4EE` / `#161412` | every surface. Not white, and close to the muted map underneath |
| `paperRaised` | `#FFFDF9` / `#201D19` | the rare surface that must lift off the paper |
| `ink` | `#1C1917` / `#F2EDE4` | primary text, solid buttons |
| `inkSoft` | `#4A443D` / `#BDB5A8` | secondary prose |
| `inkFaint` | `#746D65` / `#908979` | labels, captions |
| `rule` | `#E0D9CC` / `#332E27` | hairlines. Rules do the work shadows used to |
| `faded` | `#776E64` / `#9A9086` | a locked pin out of reach. Dark enough for parchment, light enough for a dark map |

**Two warm colours, and each means one thing.** Blue is left to the map and
to your location dot.

| Token | Hex | Meaning |
|---|---|---|
| `ember` | `#A8350F` / `#F2703F` | **a memory, and the way to it.** Every pin, the next stop (bigger, hops), the preview's line (washed out: `solid().line`), the walk's bar, the primary button, errors |
| `emberSoft` | `#F6E2D8` / `#3A2219` | the quiet button's fill |
| `seal` | `#F2B53A` / `#F5C542` | **openable.** The in-reach pin, the reach circle, the "Unlock memory" pill. A fill, never text |
| `sealInk` | `#2B1D05` / `#1F1605` | anything drawn on seal: a lit pin's edge and eye, the pill's words |
| `sealSoft` | `#FCEBC2` / `#3E3112` | the ring filling during a hold |
| `sealDeep` | `#7A4F00` / `#F7D074` | seal as words or a thin mark on paper: the unlock ring, the padlock, "within reach" |

Ember and seal differ in lightness on purpose: the earlier ochre `seal` and
ember were one colour under protanopia (docs/09 part 8).

**Buttons are `button.solid`, `button.quiet` or `button.outline`** from
`theme.ts`, with `buttonText` inside: 52pt capsules, ember with paper text,
soft ember with ink text, or a rule outline. A screen adds only where one sits
(margin, alignSelf), never its own padding or border. An action inside a page
rather than ending it (Leave note, Rewrite, Remove, Edit this memory) is the
same capsule at 36pt: spread `button.small` after it, `buttonTextSmall` inside,
`hitSlop={4}`. Only links to somewhere else stay text: Terms, Privacy, the
OpenStreetMap credit, Restore purchases.

## Type

One family: **SF Pro Rounded** (`fontFamily: 'ui-rounded'`), the system's own.
It sits with Apple Maps' labels, which are SF Pro, and its round terminals keep
the app friendly. Nothing to bundle or load. Android has no rounded cut and
gets Roboto, which is Google Maps' label face there.

| Token | Weight | Used for |
|---|---|---|
| `font.display` / `displaySemi` | 700 / 600 | titles, place names, the big figures |
| `font.prose` | 400 | the stories and every sentence |
| `font.ui` / `uiMedium` / `uiBold` | 400 / 500 / 600 | buttons, labels, distances, counts. Sentence case |

Each `font` token is a style to spread, `{ ...font.display, fontSize: 34 }`,
so trying another family or weight is an edit to `theme.ts` alone.

**The label voice** is `label` in `theme.ts`: 600 at 13, `inkFaint`,
sentence case. Use it wherever a screen *names* a thing rather than says
something — section headings, meta rows. Nothing labelled goes under 12.

**Spread it — `{ ...label }` — rather than retyping its properties.** Copying a
token is how it stops being one: the old mono voice was hand-retyped across most
of the app and its tracking had drifted three ways before anybody noticed.

**`buttonText`** is 600 at 17, the HIG's Headline size; pair it with
`color.paper` on ember and `color.ink` on the quiet and outlined buttons.
**`input`** is the whole text-field block, which renders in both You and Submit
and must not drift between them.

**Scale**: 34 display (screen titles) · 30 (place name) · 52 (the distance figure)
· 19/31 prose (the summary — the hero when nothing is attached) · 16/25 prose (body)
· 12–15 (everything labelled) · 17 buttons.


**Corners are soft**: `radius` in `theme.ts` — capsules for anything you press.

**Glass over the map, flat inside sheets.** The controls floating over the map
(Journal, You, Add, the walk bar, the distance pill, Plan a walk, Turn on
location) are `GlassButton` from `src/Glass.tsx`: iOS 26's Liquid Glass, tinted
only on the one prominent control, or raised paper with `lift` where glass is
unavailable. Never glass on a sheet or a card, never glass on glass. A glass
control scales rather than dims when pressed: opacity on a glass view's parent
stops the effect rendering. Inside sheets, hierarchy is still hairlines and
weight.

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
| 2 | baseline nudges: the gap inside a byline |
| 4 | the gap between the pause bars |
| 6 | inside a collection row, inside the filed-at card |
| 8 | the default small gap: a stat and its label, stacked buttons |
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

**Corners**, all of them (`radius` in `theme.ts`):

| Radius | On |
|---|---|
| 2 | the modal grabber and the peek's grey bars, and nothing else |
| `field` 14 | inputs, photos, thumbnails |
| `card` 28 | the cards that float over the map, and only those |
| `pill` | **anything you press**: buttons, chips, the glass controls |
| half the side | genuinely circular things only: the 84 hold ring, the 44 pager step and glass circles, an avatar, a pin |

**One shadow**, `lift` (`0,4` / 16 / 0.12, `elevation: 4`): the paper cards
over the map, and the glass controls' fallback. A second one is a rule you have
not written yet.

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
| `sealInk` on `seal` | 8.9:1 | 11.0:1 |
| `paper` on `faded` | 4.6:1 | 5.9:1 |
| `paper` on `ember` | 6.0:1 | 6.3:1 |
| `ink` on `emberSoft` | 14.0:1 | 12.7:1 |
| `sealDeep` on `paper` | 6.5:1 | 12.5:1 |
| `sealDeep` on `sealSoft` | 6.0:1 | 8.6:1 |

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
| `FALLBACK_REGION` | `0.09` | 10 km | Before anything is known; its centre is the Copenhagen planning anchor |
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

Nothing is fetched by viewport: the map before a walk asks once, around where
you are, and a walk draws only its stops, so panning never asks the server
anything.

## Rules that are load-bearing

Each of these exists because something broke or would have been rejected.

1. **Never show a blank grey map, or a dead end.** With permission denied the
   walk is planned from central Copenhagen (`FALLBACK_REGION`'s centre) and the preview
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

   **Shipped 2026-09-23** (`docs/10-decisions.md`, "A streak and a proximity
   notification, after all" — the streak half, F27, needed none of this). Code and config are
   both in; what has **not** happened yet is a real device verifying the
   background delivery end to end, or updating the actual App Store Connect /
   Play Console listings — that is a human step, not a gate the pytest suite
   can pass.

   **`isIosBackgroundLocationEnabled` is `true`, as of 2026-09-26.** It was
   left `false` on the reasoning that CoreLocation region monitoring wakes the
   app on its own and needs no `UIBackgroundModes: ["location"]`. True of
   CoreLocation, but expo-location's `startGeofencingAsync` refuses to start
   without the mode (`LocationModule.swift`, `hasBackgroundModeEnabled`), and
   App.tsx swallowed the error, so for three days the toggle showed on and
   nothing was watched. `.maestro/notify-nearby.yml` is what caught it. The
   mode is declared for the geofence only; nothing calls
   `startLocationUpdatesAsync`.
3. **Nothing fetches by viewport.** The map before a walk fetches by position
   (on entering it, and when a position first arrives), and a walk fetches
   nothing; if a fetch ever follows the viewport, debounce it, because panning
   fires `onRegionChangeComplete` continuously.
4. *(Retired with Explore: the viewport-to-radius maths.)*
5. **A memory with no coordinates cannot be drawn.** The API filters those out;
   do not assume `coordinates` is always present on types that allow null.
6. **`content.url` is already resolved.** The server points it at the document,
   or at the video's right second. Never rebuild a YouTube URL by hand.
   `content.timestamp_start` is null when the source is not a recording, and the
   button says "Open the source" instead of naming a second that does not exist.
7. **Never cover the map attribution.** The Apple Maps logo and Legal link in
   the bottom-left corner are a condition of using the map and have to stay
   visible and tappable. A floating tally in that corner is what made this a
   rule; nothing floats in that corner now.
8. **`onRequestClose` is required on every Modal**, or the Android back button
   does nothing.
9. **The map never unmounts.** The journal is hidden with `display: 'none'`,
   not a conditional render, and the map sits under it. Unmounting the map
   means losing the viewport and re-animating to GPS every time somebody
   glances at their journal. The map is the exception: anything else under a
   cover that holds a native control (Slider, Switch) unmounts, since iOS 26
   draws native glass controls through an opaque cover. `Plan` in `App.tsx`
   renders only while `!journalOpen` for that reason.
10. **Never fetch alongside `animateToRegion`.** It fires
    `onRegionChangeComplete` when it lands, and it does *not* land on the region
    you gave it — the map fits the deltas to the screen, so the settled viewport
    covers noticeably more ground. Pins group by the region `useMapCamera`
    reports, so move the camera and let it
    report back; the hook also reports a long flight itself, which
    never lands audibly. See `docs/10-decisions.md#the-app`.
11. **The credit never scrolls.** Place name above the scroll, credit pinned
    below it, story in between. Geo-gated content cannot be shared by linking
    to it — you had to be there — so a screenshot is the only way it travels,
    and a screenshot that has lost the attribution is both a broken
    distribution channel and a broken legal posture. `styles.credit` in
    `MemorySheet.tsx` is that strip; it carries the one hairline, so the three
    credit variants inside it have none of their own. Anything new that can
    appear under a summary goes *in* the scroll, not between the two.
12. **Every view has a way out.** A card over the map dismisses with an × in
    its top-trailing corner, on the title line (Apple Maps' convention, HIG
    Toolbars: a back chevron retraces a hierarchy, a close dismisses a layer).
    Never a new floating control top left: Journal owns that corner, and it is
    the least accurate tap on the screen (Hoober 2017: corner targets need
    ~12 mm against ~7 mm at the centre). The glyph is 30pt with `hitSlop` to
    44pt (HIG Buttons). It is `src/CloseButton.tsx` everywhere: the walk
    preview, You, Journal, a memory's sheet, Add a memory.
    Always trailing, never leading: a sheet's own action is not a corner
    word but the solid button at the end of the page (Post, Save). A text
    button stays only where it says more than close: Not now on the paywall.

## Writing

`Submit.tsx` is the only screen in the app that writes, and three of its rules
are not preferences:

- **It files where you are.** One coordinate, straight from the GPS, used as
  both "where I am" and "where this goes". There is no map picker and there is
  not going to be one - a memory you can pin from your sofa is a pin, and the
  whole product is the difference. Without a fix, declined or still coming,
  Post stays held: `ready` requires a position, so no path can file from a sofa.
- **Attachments upload while you type**, not on Post. A phone photo is 4 MB and
  the wait belongs in the part where somebody is composing. Post stays disabled
  while an upload is in flight, and a failed one shows as failed rather than
  disappearing.
- **Tags are the #words in the description**, as on X: there is no picker. The
  server reads them (`pipeline/tags.py`, `from_text`) and the sheet draws the
  same words in `font.displaySemi`, not a colour, since every colour here
  already means something. `mobile/src/hashtags.ts` must match the server;
  `tests/fixtures/hashtags.json` is read by both tests. Not tappable. The
  placeholder ends in `#nightlife` so the form explains it.

Three things about the shape of it:

- **Title, Description, When.** In that order, and nothing asks for a name:
  the account filing it signs it (Settings), and a blank one is Anonymous.
- **The rule under the header is the progress.** It fills as the two required
  fields land and turns seal when the thing can be posted - the same promise
  the unlock ring makes, and it costs a line rather than adding one. No hint
  text under it: the form is short enough to read as its own checklist.
- **Every chip answers being touched** - `selectionAsync` and a spring, skipped
  on mount so the sheet does not flinch as it opens. The tick is the map's
  selection one, not the unlock's: this is picking, not earning, and it must
  not borrow that weight.

A submission comes back already unlocked and its sheet opens over the map. The
modal closing is not a confirmation, and it is also the first sight of what a
stranger will find at that spot.

## Copy

Write like a friend pointing at a corner, not like a manual. The product is
simple and a bit of fun; the copy should be too. Rewritten on 2026-09-27
against Apple's HIG (Writing), NN/g on errors and empty states, and a list of
the tells that make text read as machine-written.

- **Short, concrete, contracted.** "You made it." "Not quite there. Take a few
  more steps." Second person, active voice, sentence case.
- **Buttons are verbs that say what happens**: Start walk, Plan a walk,
  Keep walking. Clear beats cute on anything you tap; the personality goes in
  the line above the button.
- **Errors say what happened and what to do.** "That didn't save. Try again in
  a moment." Never "Could not", never an error code, never blame.
- **Empty states point at the next move.** "No walks yet. Unlock a stop and
  your walk lands here."
- **Never defend the design to the person using it.** Why the server withholds
  text belongs in `docs/10-decisions.md`; the app says "No peeking from the
  sofa" and stops.
- **No "we".** Apple's rule: nobody knows who "we" is.
- **Avoid the machine-written tells**: em dashes in UI text, "X. Yours to Y."
  aphorisms, "not X, but Y", three-part lists picked for rhythm, and "quietly",
  "truly", "hidden gem".
- **One word per thing.** A *memory* is what is pinned, a *walk* is today's
  plan (never "route" on screen), *unlock* is what the hold does.

No exclamation marks: celebrations are in the words ("Nice walk.") and the
haptic, not the punctuation. Count strings are singular/plural aware ("1 memory
here"). Store-facing copy in `mobile/store/` has character limits enforced by
`tests/test_store_copy.py`.

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
xcrun simctl location booted set 55.67886,12.57586   # central Copenhagen: where the dev seed is

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
xcrun simctl io booted screenshot /tmp/sheet.png
```

What this recipe still cannot do by hand: press the unlock ring, or reach
anything below the fold. Both are what `./e2e/run.sh` is for — `f7` holds the
ring and `f5` fills in and posts the whole submit sheet.

**For the real build, not Expo Go**, which is what `W3-13` is about: Expo Go
shows its own permission copy and no native manifest.

```bash
cd mobile && npx expo run:ios     # builds, installs, launches, then exits
```

**With an iPhone paired to this Mac it dies asking for a signing
certificate**, even with `--device <simulator>`: the CLI takes the
physical-device branch anyway. `./e2e/run.sh` builds with `xcodebuild` for that
reason (its step 3/5, which also rebuilds whenever `Podfile.lock` changed), and
running it is the shortest way to a fresh simulator build.

It bakes the LAN IP into the launch URL and exits with Metro, so start Metro
yourself afterwards with `REACT_NATIVE_PACKAGER_HOSTNAME=localhost` and
`xcrun simctl launch` — the dev client remembers the last URL it loaded. Do not
re-open the `com.PLACEHOLDER.memorylane://` URL by hand: the "Open in Memory
Lane?" system alert it raises cannot be dismissed without a tap and sits over
every screenshot until the simulator is rebooted.

**Use `localhost` for the simulator, a LAN IP only for a physical phone.** Expo
bakes `EXPO_PUBLIC_API_URL` in at dev-server start, so if you pass your LAN IP
and then change network, the preview says "Can't reach Memory Lane right
now." — the app still works, it just cannot reach the API. Restart the dev server
rather than debugging the app. Likewise `exp://<stale-ip>:8081` hangs on
"Opening project"; `exp://localhost:8081` does not.

**"No script URL provided" is Metro not running.** The installed app (from
`expo run:ios` or `./e2e/run.sh`) is a Debug build: it has no bundle of its
own and there is no dev launcher to fall back to. Start Metro first: `cd
mobile && npx expo start --dev-client`.

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
correctly say "No walk within 10 km from here" and you will think you broke
something.

Pure map maths goes in `src/region.ts` with a `node --test` case beside it;
the gate runs `mobile/src/*.test.ts`. Component behaviour is currently untested
and there is no RN test runner installed — do not add one without asking.

## States

The app's stages (`App.tsx`'s `Stage`) must stay distinct:

| Stage | Shows | Leaves by |
|---|---|---|
| loading | paper, while the cache and `GET /v1/routes/today` answer | a walk found → walk; none → map |
| preview | the walk on the map, the card with its length and shape | Start walk → walk; × → map |
| walk | today's stops, the pill | nothing - the day is locked |

A failed request on the preview leaves you there with "Can't reach Memory
Lane right now." under the button. With no location permission the walk's button
reads **"Turn on location"**, and it is the only time that button exists: nothing can unlock without a
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

Every coordinate draws the same pin: a 24px `ember` disc, 2px `paper` edge, an
8px `paper` eye in the middle. It changes for one reason only — **it can be
opened from where you stand**, and on a route day only if it is one of the
route's stops (F25) — and then it grows to 32px in gold `seal` with a `sealInk`
edge and eye 12px, over a `halo` wash. That is the whole visual language. Simplified 2026-09-23
from five ink states, a round-or-folded-card shape per layer and a ranked
corner slot of padlock and tag glyph: it was a legend nobody should need.
The resting disc went from `ink` to teal on 2026-09-26 (black read as grim),
and to `ember` on 2026-09-27: teal read as water and park.

| When | Geometry | Tokens |
|---|---|---|
| every pin | disc 24, border 2; eye 8 | fill `ember`, edge + eye `paper` |
| `unlockable`: inside the radius **and openable by walking** | disc 32, border 2; eye 12; wash 46 | fill `seal`, edge + eye `sealInk`, wash `halo` |
| the next stop on today's walk, not yet in reach | disc 32, border 2; eye 12; hops (`useHop`), still under Reduce Motion | fill `ember`, edge + eye `paper`. Size and the hop tell it apart |
| a stack, or one of today's stops | tag min-w 20, h 20, radius 10, border 2, top right | `ember`, count `paper` (`seal` with `sealInk` on a lit pin) |

**The eye is the point.** The pin you can open is the pin you are standing on,
so the blue location dot lands in the hole rather than disappearing under a
disc. The badge sits in the corner for the same reason.

**`seal` means openable now, and nothing else.** A seal-coloured pin you
cannot open is an invitation that refuses you (F11). Locked near, locked far,
earned and never gated all draw the same ink pin; the difference is in the
marker's `title` (VoiceOver and Maestro still hear every state from
`STATE_LABEL`) and in the sheet. `reachOf` in `src/reach.ts` still computes all
five, because the banner and the walk hint need them.

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
exactly when their state changes and never otherwise.

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
65% after a primer. "Plan a walk" (or a pin's "Walk here") is the ask: a press
with a reason, walks start from where you are, and only then the system dialog.
`getForegroundPermissionsAsync` runs first so somebody who already said yes is
never asked twice, and a hard refusal (`canAskAgain === false`) swaps the button
for **Open Settings**, which is the only route back.

Position is then *watched*, not read once (`watchPositionAsync`, 5m interval,
foreground only). Walking into range has to change the map by itself.

## A link that can fail

`Linking.openURL` rejects when nothing on the device can handle the link — no
browser, a managed device. The watch link goes through a helper in
`MemorySheet` that catches it and says so. A control that
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
- Every state that colour distinguishes is also written or drawn: the padlock
  (a shape, read out as "Locked"), "within reach", "Nearest locked memory".

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
  `withinReach` gets a new array identity every 5 m, so the effect keys on a
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

Writing is F5 (file a memory), F20 (report or block) and F21 (be somebody).
Sign-in is F22, the first flow, and it is Google and Apple only — see
`src/SignIn.tsx` for why, and for why neither button works in Expo Go.

The paywall is F35 (`src/Paywall.tsx`). One sheet at a time: it opens after
the peek or You closes, never on top. **Open it now** is an outline beside
the solid **Walk here**, because the free way stays the one thing to do. No
price is ever written in the app; the store's `priceString` is. Without a
RevenueCat key it says "Subscriptions aren't available right now.", never a
button that cannot work, and **Not now** is always there (rule 1).
