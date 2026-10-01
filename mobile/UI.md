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
└─ the bottom row              Journal, "Plan a walk" (ember) -> Preview, drawn at once, Add

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
├─ the steps pill             top centre, every stage (src/StepsPill.tsx, src/wallet.ts). The one
│                              thing to know, rolling when it changes: "2 free today" / "4,210 steps";
│                              none free, "4,210 steps" alone; short, a small ember ring
│                              filling to the price and "600 to go" / "400 steps". A tap recounts and opens
│                              How it works (src/HowItWorks.tsx): the balance, then what a pin is,
│                              what opening one costs, where steps come from, wander or walk
├─ the filter, Settings       top right, 44pt glass circles, the two rare ones. The filter before a
│                              walk only, left of Settings so Settings never moves: a native menu,
│                              All memories / Locked / Unlocked (src/MapFilter.tsx), its glyph
│                              filled while it hides something. Settings (`gearshape`) opens its
│                              sheet. Top left stays empty
├─ the bottom row             edge to edge, bottom 70 (12pt over Apple's logo), the map and the
│                              walk, never over a card with its own buttons (Preview, EndWalk,
│                              WalkDone). Journal (`book.closed`, a 10pt ember dot: a heart or a
│                              note came back on something you filed, src/seen.ts) opens the drawer,
│                              as does a swipe in from the left edge (src/Drawer.tsx). In the
│                              middle Plan a walk, ember glass, `figure.walk` -> Preview, before a
│                              walk; the walk card on one. Add (an ember `plus`) files a memory,
│                              no walk needed. See "Writing"
├─ the walk card             the bottom row's middle, glass (F9): "Next: <place> · 350 m" over
│    "2 of 5 · 4.1 km left" (the next stop's number, as on its pin), "Every stop unlocked"
│    when done. A tap zooms out around you and the next stop; the ✕ ("End walk") ends it,
│    and with stops left asks first in a card (EndWalk): "End this walk?", End walk / Keep
│    walking. Never a plain tap. Standing at any stop, the unlock ring (src/UnlockHere.tsx)
│    takes its place and carries the same second line:
│    the ring, the place, year or source, "1 attachment waiting" and what it
│    costs. Everyone gets it on the map before a walk too. Tapping a pin
│    in reach points it at that pin; the hold opens the sheet on the story. Short of steps
│    there is no ring to hold: the full faded Approach ring, "600 steps to go · about 6 min
│    walking" and Skip the steps (the paywall)
├─ "Center on me"             bottom right, above Add, a 44pt glass `location.fill` circle (F10). On a walk the
│                              camera follows you; a one-finger drag lets go and this shows until
│                              tapped. Before a walk, it shows once the map is off you by a sixth
│                              of the screen. Custom: showsMyLocationButton is Android-only
├─ "Turn on location"         bottom centre, above the bottom row, only while there is no position
└─ card (WalkDone)            once, when the last stop's sheet closes: the map unpins and fits
                               the whole loop, drawn; "Nice walk." 34/700, "5 memories · 4.1 km
                               loop · 52 min", the streak, Done. A relaunch does not show it again

MemorySheet (over the map: a floating card when locked, a 92% sheet when open; a pageSheet from the journal) - two compositions, not one with holes in it

  locked                            open
  ├─ place name       28/700        ├─ place name       28/700, ⋯ beside the ×
  ├─ padlock                        ├─ avatar 20 + "Anna · 17 June 1978 · on this day · 40 m away"  label
  │                                 ├─ the lede  17/26 semibold: the first sentence, the peak
  │                                 ├─ the rest  17/26, #tags semibold
  │                                 ├─ "their words"  17/26 semibold, ember rule, "— Mads, at 12:04"
  │                                 ├─ "Then and now"  17/26 inkSoft   contrast_note, when known
  ├─ distance         52/700        ├─ photo / recording   if it has any
  ├─ "Get within 20 m"              ├─ "Watch from 12:04 →" ember 17 semibold, the episode under
  ├─ "1 attachment waiting"         │    it in label; the heart at the right of the same row (F11):
  │                                 │    a bare count before the glyph, in a slot kept at zero.
  │  (in reach it is not opened:    │    The link says where it goes (F12): "Watch on YouTube",
  └─  the ring is on the map)       │    "Read it in the book", "Read the 1856 article"
                                    └─ notes  17/26, "You  Rewrite  Remove" in label
                                    Nothing is pinned, bar the pager under a stacked pin.

  The open side's byline sits under the place name, above the meta line:
  "Retold from <channel>" with its avatar and the episode or book, or "Left by X".
  ⋯ holds Edit this memory on your own, Report and Block on anyone else's.

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

Journal (src/Memories.tsx in src/Drawer.tsx)  a panel from the left over the mounted map,
│                              screen width less 44 (at most 380), the map dimmed by `scrim` at
│                              its right. Springs in with a little overshoot and a light haptic on
│                              landing; header, sections and list arrive a beat apart. Swipe it
│                              left, tap the map or × to close. Reduce Motion: no spring, no
│                              cascade. The journal is you as well
├─ header                      44pt photo or initial, your name 28/700 (or "Journal"), and under
│                              it "12 memories · 4 places · 2 added · 5 hearts", zeros left out
│                              but the first. Tapping it opens Edit profile. × top right
├─ Walks                       the streak, large (F27; not at 0), then one row per walk that
│                              opened something, date and length; a row opens in place to its
│                              earned stops, numbered on an ember rail. Cached for the train
├─ Unlocked Memories           what you opened; "♡ Hearted" at the right of its count shows only
│                              what you hearted
└─ My Memories                 what you added; a row opens Submit as the editor. "3 hearts ·
                               1 note · last heart yesterday", never who

Settings and Edit profile are sections of nothing: a section is what you did,
and the account is not (docs/10, "The journal is a drawer; settings are the
map's"). They open as pageSheet modals, Settings from the map and Edit profile
over the journal, which stays mounted under it.

Settings (src/Settings.tsx, pageSheet, from the map's ⚙) - "Settings" 34/700, × top right
├─ Account                     which sign-ins, add the other, sign out (back to the gate),
│                              delete; the subscription
├─ How unlocking works         the one place that answers "why can't I read this"
├─ Location, Notifications     state + action; the Switch is why this is not inside the cover (rule 9)
└─ About                       privacy policy, contact, OpenStreetMap

Edit profile (src/EditProfile.tsx, pageSheet, from the header) - "Profile" 34/700, × top right
├─ the photo, 112pt            Choose photo / Take photo, square crop; Remove photo. Public,
│                              like the name: it signs what you file (src/Avatar.tsx)
└─ Your name                   what submissions are signed with, saved as typed. Blank = Anonymous

There are no tabs on the map. Before a walk the map draws what is around you, locked and
unlocked, behind a filter; on a walk it draws only that walk. Three pins a day
open from anywhere, from the peek; after that, standing on one and 1,000 steps.
The bottom is where you act, one tap each: Journal, Plan a walk (the one
ember thing) or the walk card, Add. The top is where you read: the step
count, and the filter and Settings in the corner (docs/10, "Act at the
bottom, read at the top").
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
| `src/Glyph.tsx` | every icon: an SF Symbol at a point size, in a theme colour, bouncing when `bounce` changes. The pin is the one drawn mark |
| `src/MemoryMarker.tsx` | one pin, lit when it can be opened from here |
| `src/UnlockButton.tsx` | the hold, the ring, the haptics |
| `src/UnlockHere.tsx` | the ring over the map, with the place it opens; short of steps, how far off |
| `src/StepsPill.tsx` | the top of the map: what opens memories today, the number rolling (`@expo/ui`) |
| `src/wallet.ts` | what the pill says and whether standing on a pin can pay. Pure, and unit-tested |
| `src/Plan.tsx` | the preview card: a walk drawn at once, its length and shape, then accept |
| `src/useBreath.ts` | the next stop's hop |
| `src/Memories.tsx` | the journal, which is you: photo, name, numbers, then walks, unlocked, and what you filed |
| `src/Settings.tsx` | account, how unlocking works, location, notifications, about. Its own sheet, from the map's ⚙ |
| `src/Drawer.tsx` | the journal's panel from the left: the edge swipe, the spring, the scrim |
| `src/EditProfile.tsx` | the photo and the name. Its own sheet, from the journal's header |
| `src/Avatar.tsx` | a photo, an initial or nobody, in one circle at any size |
| `src/CloseButton.tsx` | the × that closes a card, sheet or page (rule 12) |
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
| `seal` | `#F2B53A` / `#F5C542` | **openable.** The in-reach pin, the reach circle. A fill, never text |
| `sealInk` | `#2B1D05` / `#1F1605` | anything drawn on seal: a lit pin's edge and eye, the pill's words |
| `sealSoft` | `#FCEBC2` / `#3E3112` | the ring filling during a hold |
| `sealDeep` | `#7A4F00` / `#F7D074` | seal as words or a thin mark on paper: the unlock ring, its lock, "attachments waiting" |

Ember and seal differ in lightness on purpose: the earlier ochre `seal` and
ember were one colour under protanopia (docs/09 part 8).

**Buttons are `button.solid`, `button.quiet` or `button.outline`** from
`theme.ts`, with `buttonText` inside: 52pt capsules, ember with paper text,
soft ember with ink text, or a rule outline. A screen adds only where one sits
(margin, alignSelf), never its own padding or border. Post is the
same capsule at 36pt: spread `button.small` after it, `buttonTextSmall` inside,
`hitSlop={4}`. An action inside a page is not a button but `label` text with
`hitSlop={12}`: inkSoft for Rewrite, Remove and the photo actions, ember for
Leave note and Delete. Edit this memory is in ⋯ (docs/10, "Reading and writing
are one page").

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
**`input`** is the whole text-field block, which renders in both Edit profile
and Submit and must not drift between them.

**Scale**: 34 display (screen titles) · 28/34 (place name) · 52 `figure` (the
gate's distance, the streak, the stats) · 36 `figureSmall` (the peek's
distance, under its place) · 17/26 prose (the story, then-and-now, notes)
· 16/25 prose (body elsewhere) · 13 `label` (everything labelled) · 17
buttons. A memory, open or being written, is `story` in `theme.ts` and
nothing else: 28, 17 and 13.


**Corners are soft**: `radius` in `theme.ts` — capsules for anything you press.

**Glass over the map, flat inside sheets.** The controls floating over the map
(Journal, Plan a walk, Add, the walk card, the steps pill, the filter,
Settings, Center on me, Turn on location) are `GlassButton` from `src/Glass.tsx`: iOS 26's Liquid Glass, tinted
only on the one prominent control, or raised paper with `lift` where glass is
unavailable. Never glass on a sheet or a card, never glass on glass. **One
tint in view**: Plan a walk's before a walk, Turn on location's on one. The walk card is
untinted: the next stop's pin is the ember on the map. No `GlassContainer`: two circles merging read as
one odd shape (the founder, 2026-10-01), and the container swallows taps in
its gaps. Glass takes colour from what is under it: Journal reads cyan over a lake,
and that is the material, not a bug. A glass
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
| 18 | a rule to the content under it — a byline, a source line, a Settings section |
| 20 | the sheet action bar, Submit's body |
| 22 | the sheet body's top padding, the empty-area card |
| 24 | **the screen gutter.** Journal, Settings and the sheet all indent by this |
| 26 | the sheet's section rhythm, and the gap between collection rows |

Anything above 26 is a one-off (28 and 32 above a section or a page's first
line, 38 above a Settings section, 40 of gate padding, 72 of
bottom padding) and stays a literal. So is 11 of chip padding in Submit, which
makes a 40pt chip with the label's line box.

**Four tokens in `theme.ts` carry the rest**: `pill` (44 tall, 16 either side,
a capsule: every glass control over the map but the one button-sized Turn on
location), `floating` (`paperRaised`, `card` corner, `lift`: the unlock card,
Plan's card and the peek, each with its own padding), and `figure` /
`figureSmall`.

**Corners**, all of them (`radius` in `theme.ts`):

| Radius | On |
|---|---|
| 2 | the modal grabber and the peek's grey bars, and nothing else |
| `field` 14 | inputs, photos, thumbnails |
| `card` 28 | the cards that float over the map, and only those |
| `pill` | **anything you press**: buttons, chips, the glass controls |
| half the side | genuinely circular things only: the 84 hold ring, the 44 pager step and glass circles, an avatar, a pin |

**Two shadows.** `lift` (`0,4` / 16 / 0.12, `elevation: 4`): the paper cards
over the map, and the glass controls' fallback. And the hold ring's glow
(`seal`, centred, 14 / 0.5), because the ring is the one thing that asks to be
touched. A third is a rule you have not written yet.

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
   button names the kind instead of a second that does not exist
   (`sourceAction` in `src/format.ts`).
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
11. **The credit never scrolls.** Place name and its byline above the scroll
    ("Retold from <source>" or "Left by X"), the button and the heart pinned
    below it, story in between (F12, 2026-10-01; the credit was a pinned strip
    at the bottom before). Geo-gated content cannot be shared by linking to it
    — you had to be there — so a screenshot is the only way it travels, and a
    screenshot that has lost the attribution is both a broken distribution
    channel and a broken legal posture. Up top it is also the first thing seen
    with an AI-written story, which is where AI Act Art 50 wants it said.
    `api/card.py` puts it in the same place. Anything new that can appear
    under a summary goes *in* the scroll.
12. **Every view has a way out.** A card over the map dismisses with an × in
    its top-trailing corner, on the title line (Apple Maps' convention, HIG
    Toolbars: a back chevron retraces a hierarchy, a close dismisses a layer).
    Never a new floating control top left: it is kept empty, and it is
    the least accurate tap on the screen (Hoober 2017: corner targets need
    ~12 mm against ~7 mm at the centre). The glyph is 30pt with `hitSlop` to
    44pt (HIG Buttons). It is `src/CloseButton.tsx` everywhere: the walk
    preview, Journal, Settings, Edit profile, a memory's sheet, Add a memory.
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

The shape of it is the open sheet's (docs/10, "Reading and writing are one
page"):

- **The same page with empty slots.** The title in `story.title`, the byline
  ("Anna · 1 October 2026 ▾ · here", the date tappable), the story in
  `story.body`, photos at the size they are read at. No boxes and no field
  labels: the placeholder and the cursor say what is editable. Nothing asks
  for a name: the account signs it (Settings), and a blank one is Anonymous.
- **Cancel and Post are the only chrome**, the × left and Post right, as in
  every composer. Post is held until the title and the story are there.
- **Every other action is text** in the label voice: Take photo, Choose photo,
  Remove photo, Delete this memory (ember, two taps).

A submission comes back already unlocked and its sheet opens over the map. The
modal closing is not a confirmation, and it is also the first sight of what a
stranger will find at that spot.

## Copy

Write like a friend pointing at a corner, not like a manual. The product is
simple and a bit of fun; the copy should be too. Rewritten on 2026-09-27
against Apple's HIG (Writing), NN/g on errors and empty states, and a list of
the tells that make text read as machine-written.

- **Short, concrete, contracted.** "Not quite there. Take a few
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
# 1. API. The dev database is real data: 38 memories within 500 m of the
#    fallback coordinate below.
docker compose up -d --build

# 2. cp .env.example .env  (once). It carries EXPO_PUBLIC_DEV_LOCATION, which
#    pins the app's position to central Copenhagen under __DEV__ - so the Simulator's
#    location stops being something you set after every boot.
cd mobile && npx expo start --ios

# 3. pre-grant location, or the permission dialog covers the first screen
#    ("booted" is a literal simctl accepts - no need to look up a UUID)
xcrun simctl privacy booted grant location-always host.exp.Exponent
xcrun simctl location booted set 55.67886,12.57586   # central Copenhagen
#    With EXPO_PUBLIC_DEV_LOCATION set the app ignores that: long-press the map
#    to move instead (__DEV__ only), or a pin to stand on it. Maestro
#    cannot trigger it: neither longPressOn nor a held swipe reaches the map.

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
curl -s 'localhost:8080/v1/memories/nearby?lat=55.67886&lng=12.57586&radius_km=1'   # pick an id
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
`xcrun simctl launch` — the dev client remembers the last URL it loaded, if
it ever loaded one. A fresh install has none and shows "No script URL
provided"; tell it once: `xcrun simctl spawn booted defaults write
com.PLACEHOLDER.memorylane RCT_jsLocation localhost:8081`. Do not
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

**The dev database is real data**, and it is enough (2026-09-29): 38 memories
within 500 m of `FALLBACK_REGION`, 14 of them gated. Long-press the map or a pin
to stand where one is: on a pin, you land on it. A marker swallowed the map's
long-press until `patches/react-native-maps+1.29.8.patch` gave the recognizer a
delegate; before that, a draggable marker stood in for it and left a system
pin behind. The seed (`pipeline/seed_dev.py`, one of every state the
sheet can render) goes only into an empty database, which is what e2e builds;
beside the real corpus it copied real summaries into duplicates, so it refuses.

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
| unlocked (`plain`, `stamped`): every memory in it opened | same geometry, inside out | fill `paper`, edge + eye `ember` |
| `unlockable`: inside the radius **and openable by walking** | disc 32, border 2; eye 12; wash 46 | fill `seal`, edge + eye `sealInk`, wash `halo` |
| the next stop on today's walk, not yet in reach | disc 32, border 2; eye 12; hops (`useHop`), still under Reduce Motion | fill `ember`, edge + eye `paper`. Size and the hop tell it apart |
| a stack, or one of today's stops | tag min-w 20, h 20, radius 10, border 2, top right | `ember`, count `paper` (`seal` with `sealInk` on a lit pin) |

**The eye is the point.** The pin you can open is the pin you are standing on,
so the blue location dot lands in the hole rather than disappearing under a
disc. The badge sits in the corner for the same reason.

**`seal` means openable now, and nothing else.** A seal-coloured pin you
cannot open is an invitation that refuses you (F11). That includes paying:
with no free one left and short of the price, a pin you stand on stays ember
and its reach reads `locked` (`short` in `App.tsx`, from `src/wallet.ts`). Locked near and locked
far draw the same ember pin, and earned and never gated the same paper one
(2026-10-01, docs/10 "A map of what is locked"); the rest is in the
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
- Every state that colour distinguishes is also written or drawn: the lock
  (`lock.fill`, a shape, read out as "Locked"), "within reach", "Nearest locked memory".

## The unlock control

`src/UnlockButton.tsx`. The one place in this app allowed to be playful. Everything else is a quiet
map; this is the moment the product is *about*, so it gets the animation
budget. Spec, so it does not get re-invented per screen:

- **Alive at rest, quiet under the thumb.** Borrowed from Shazam: before
  it is touched, the ring breathes (1 to 1.03) and two seal ripples leave it
  half a breath apart (`IDLE_MS`, 2.4s), over a static seal glow. It asks
  to be pressed. On press-in the ripples fade and the ring squishes to 0.94,
  so the press is answered in the same frame. The squish reacts to the press
  and the fill is the progress; one never stands in for the other. Letting go
  pops it back with a little overshoot. It never loops while `busy` or with
  Reduce Motion on.
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
  arriving with the third tick, and the lock swells as it is worked. Both
  are interpolations of the same value the fill uses, so they cost one
  animation and cannot drift out of sync with it. On the Success the lock
  becomes `lock.open.fill`, with the symbol's own bounce.
- **The burst plays over the request, not after it.** A completed hold fires
  the unlock and the flare in the same frame, so the round trip happens behind
  something worth watching. The payoff proper is not here — it is the story
  rising into `MemorySheet` as it opens (`revealId`), and this hands off to
  it: the lede, the rest, the quote, then "Then and now" and the
  credit, each rising 12 px over 360 ms, 90 ms after the last (630 ms in
  all, one native-driver value). Reduce Motion keeps the fades and drops the
  rise. No haptic of its own: the Success has already fired on the hold.
- **Transform and opacity only.** Those are what `useNativeDriver` can carry;
  an animated colour puts the whole control back on the JS thread for the
  900ms it most needs to be smooth.
- **It lives on the map, alone, in the middle.** `src/UnlockHere.tsx` centres
  a 136px ring over the map, over your own dot, because you are standing on
  it. There are no words: no caption, place, cost or error. The map still pans
  around it, and it needs no × because walking away takes it away (rule 12).
  The cost is in the steps pill (docs/10, "The lock alone").
- **A refusal resets the ring and shakes its head.** Success unmounts the
  control (the memory is no longer locked, and the sheet opens on it), so
  `busy` falling back to false is always a no. The ring springs empty, shakes
  side to side and fires `notificationAsync(Warning)`, and a screen reader is
  told the reason, since nothing draws it.
- **Short of steps, the lock is faded.** It is the approach ring at full size,
  never seal, and a tap opens the paywall. Its label is the shortfall
  ("580 steps to go · about 6 min walking").
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
completed hold can still come back refused when GPS has drifted. The head
shake says so, and VoiceOver hears "Not quite there. Take a few more steps."
rather than meeting a control that looks broken.

## Flows

Documented flows live in `docs/08-ux-flows.md`. Build toward those, and when a
flow changes, change that file in the same commit.

Writing is F5 (file a memory), F20 (report or block) and F21 (be somebody).
Sign-in is F22, the first flow, and it is Google and Apple only — see
`src/SignIn.tsx` for why, and for why neither button works in Expo Go.

The paywall is F35 (`src/Paywall.tsx`). One sheet at a time: it opens from Settings,
or when a hold is refused for want of steps, never on top of a sheet. No
price is ever written in the app; the store's `priceString` is. Without a
RevenueCat key it says "Subscriptions aren't available right now.", never a
button that cannot work, and **Not now** is always there (rule 1).
