# UI guide

For agents working in `mobile/`. A walk planner: one map, one journal, the modals and one mechanic; this file
says what it looks like, why, and how to check you did not break it.

Read this before changing anything under `mobile/src/` or `App.tsx`.

## The app today

Four stages, one map, four modals. The stage is plain state in `App.tsx`
(`'loading' | 'end' | 'preview' | 'walk'`); the planner (`preview`) is home, and
the map stays mounted through all of them (rule 9). There is no map of what is
locked (docs/10, "A walk planner, nothing else").

```
SignInScreen (src/SignIn.tsx)  the first screen, and the only one until signed in
├─ the logo tile               where StartupLogo left it, at rest
├─ "Memory Lane"               34/700
├─ one line                   what the app is, 17 prose, inkSoft
├─ Apple's own button          white on the dark paper, black on the light
├─ "Continue with Google"      outlined; absent without a client id
└─ "Skip (dev build)"          __DEV__ only, so a release bundle has none

Preview (src/Plan.tsx)          home: the first screen after sign-in, unless today's walk is accepted,
│                              and where ending a walk lands. The map, fitted to the drawn walk above
│                              the measured card. Draw first, adjust after. Journal and Add top left, level top
│                              centre, you top right; no bottom row
├─ Marker per stop, numbered   not tappable - a look, not a walk
├─ the loop, drawn             RouteLine from the start and back, washed-out gold under labels so the pins pop
└─ card (Preview)              two steps; every change on it redraws the walk
   ├─ "A walk from here"        23/700; nothing to close back to
   ├─ "4 memories · 3.8 km loop"   "Finding a walk…" first; "No walk within 10 km from here."
   ├─ "Nothing at 4 km; this is the nearest."   an empty length moved up to one with a walk
   ├─ "Planning from central Copenhagen." + Use my location   with no position; the location ask
   ├─ "4 km" + slider           1-10 km, 0.5 steps (WALK_KM), uncontrolled: redraws on release
   ├─ Loop · One way            Submit's Chip; One way adds "Pick where it ends"
   ├─ See the stops             primary; step two, the map refits above the taller card
   │  ├─ ‹ Back                 to step one ("Back to the length")
   │  ├─ ‹ "4 memories · 3.8 km loop" ›   pages, 44pt each: no ‹ on the first, no › once none is left
   │  ├─ the list               a row per stop in walk order: gold number, place 16/700, "1978 · Vega
   │  │                         Archive · #music #nightlife", a padlock. Four rows, then it scrolls
   │  └─ Start walk
   └─ walked out (one a day, F35), the card is "Today's walk is done" + More walks

MapView (the walk, full bleed)  only today's accepted stops, nothing else. With a
│                              position the camera is pinned on you: it follows,
│                              does not pan or rotate, and a pinch stays centred
├─ Marker per stop            tap -> MemorySheet.  One pin, see Markers; the next one hops. No line
├─ the level pill             top centre, every stage (src/LevelPill.tsx): "Level 3", a purple
│                              walker before it, a thin XP bar under it, rolling when it changes.
│                              A tap recounts steps and opens Your walks (src/HowItWorks.tsx):
│                              level and XP, every walk as a card drawn as its shape (src/WalkCard.tsx; a tap
│                              shows it on the map under the PastWalk card), then
│                              planning, standing there, finishing to level up, one walk a day
├─ you ("You")                top right, your photo or initial (src/Avatar.tsx, 38pt) in a 44pt
│                              glass circle, and under it a native menu (src/AccountMenu.tsx):
│                              your name as its title, "3-day streak · 27 opened · 2 filed",
│                              "Signed in with Apple" or "Not signed in", Edit profile, then
│                              Settings (`gearshape`)
├─ Journal                    top left, a 44pt glass circle, the planner and the walk, never over a
│                              card with its own buttons. `book.closed`, a 10pt gold dot: a heart
│                              or a note came back on something you filed (src/seen.ts). Opens the
│                              journal sheet
├─ the bottom row             edge to edge, bottom 70 (12pt over Apple's logo), on the walk only,
│                              never over a card with its own buttons (Preview, EndWalk,
│                              WalkDone). Add, a 44pt glass circle with an gold `plus`, files a
│                              memory, no walk needed (see "Writing"). Center on me the same circle
│                              at the other end. Between them the one thing to do, which changes:
│                              Turn on location (gold) with no position, else the walk card.
│                              While a hold would open the ring the walk card stays under it
├─ the walk card             the bottom row's middle, glass (F9): "Next: <place> · 350 m" over
│    ●●○○○ "4.1 km left" (an gold stamp per stop opened, filled from the left, never a ring,
│    which is the hold's; VoiceOver hears "2 of 5", stops opened plus one), "Every stop unlocked"
│    when done. A tap zooms out around you and the next stop; ⏭ ("Skip this stop") drops
│    the next stop without ending the walk; the ✕ ("End walk") ends it,
│    and with stops left asks first in a card (EndWalk): "End this walk?", End walk / Keep
│    walking. Never a plain tap. Standing at any stop, the lock (src/UnlockHere.tsx) comes
│    up above it: the ring low above the bottom row, and under it a card with the place, year
│    or source, and ‹ › with "2 of 3" when more than one is in reach. Only a stop of the
│    walk in progress gets it. Tapping a pin in reach points it at that pin; the hold opens
│    the sheet on the story
├─ "Center on me"             the bottom row's right end, always there (F10). `location.fill`
│                              while the map is on you, `location` when not: on a walk once a
│                              one-finger drag lets go of you, before one once the map is off you
│                              by a sixth of the screen. With no position a tap asks for one.
│                              Custom: showsMyLocationButton is Android-only
├─ "Turn on location"         the bottom row's middle, only on a walk with no position
└─ card (WalkDone)            once, when the last stop's sheet closes: the map unpins and fits
                               the whole loop, drawn; "Nice walk." 34/700, "5 memories · 4.1 km
                               loop · 52 min", the streak, Done. At 7, 30 and 100 days the streak
                               springs in with a purple flame and a second success haptic; any
                               other day it is one quiet line. A relaunch does not show it again

MemorySheet (over the map: a floating card when locked, a 92% sheet when open; a pageSheet from the journal) - two compositions, not one with holes in it

  locked                            open
  ├─ place name       28/700        ├─ place name       28/700, ⋯ beside the ×
  ├─ padlock                        ├─ "17 June 1978 · on this day"  17 inkSoft, its own line
  │                                 ├─ avatar 20 (none if none) + "Left by Anna" / "Retold by AI from X ↗"  label
  │                                 ├─ ❦ the one flourish: byline above, story below
  │                                 ├─ the lede  17/26: the first sentence, the peak, own paragraph
  │                                 ├─ the rest  17/26, #tags semibold
  │                                 ├─ "their words"  callout: gold bar, ❝ "Mads, at 12:04" label, 17/26
  │                                 ├─ then and now  callout: rule bar, clock icon, "Then and now" label, 17/26
  ├─ distance         52/700        ├─ photo / recording   if it has any
  ├─ "Get within 20 m"              └─ ❦ then the notes: "♡ 1  2 notes" header (F11, glyph first),
  ├─ "1 attachment waiting"              a one-line composer that grows, then each note as
  │                                      "Anna · 2 days ago  Rewrite Remove" label over 17/26
  │  (in reach it is not opened:
  └─  the ring is on the map)
                                    Nothing is pinned, bar the pager under a stacked pin.

  The open side's byline sits under the place name, above the meta line:
  "Retold by AI from <channel>" with its avatar, or "Left by X". The credit is the one source
  link: a tap opens the passage or the video at the right second (F12's wording is what
  VoiceOver hears).
  ⋯ holds Edit this memory on your own, Report and Block on anyone else's.

  peek (a walk's stop, not yet reached: a card over the live map, sized to its content)
  ├─ place name
  ├─ "From Vega Archive", or a person glyph + "Left by Anna"   who, directly under the name
  ├─ #music  #nightlife      every tag, outline pills in displaySemi, under the name
  ├─ Approach ring  +  "472 m"  36/700      the lock as the distance still to go
  │                    "1978 · 12 hearts"   the year off the source line: it is when, not when published
  └─                   "1 attachment waiting"

  The locked side says how many attachments are waiting and never which. A
  photograph of the place is the memory as much as the text is.

Submit (pageSheet modal, from Add) - see Writing

Journal (src/Memories.tsx, pageSheet, from the Journal button)  over the mounted map;
│                              header, sections and list arrive a beat apart. Drag it down or
│                              × to close. Reduce Motion: no cascade. The journal is you as well
├─ header                      44pt photo or initial, your name 28/700 (or "Journal"), and under
│                              it "12 memories · 4 places · 2 added · 5 hearts", zeros left out
│                              but the first. Tapping it opens Edit profile. × top right. A
│                              number that grew since the last look rolls up from its old
│                              value (countUp.ts, at most 8 ticks over ~600 ms, a selection
│                              haptic each); one that fell just shows. First look and Reduce
│                              Motion: no roll
├─ Walks                       one row per walk that opened something, date and length; a row
│                              opens in place to its earned stops, numbered on an gold rail.
│                              Cached for the train
├─ Unlocked Memories           what you opened; "♡ Hearted" at the right of its count shows only
│                              what you hearted. One opened since the last look scales in
│                              once, 0.8 → 1.08 → 1 with a selection haptic, the first time
│                              it is drawn (seen.ts). First look and Reduce Motion: no pulse
└─ My Memories                 what you added; a row opens Submit as the editor. "3 hearts ·
                               1 note · last heart yesterday", never who

Settings and Edit profile are sections of nothing: a section is what you did,
and the account is not (docs/10, "The journal is a sheet"). They open as pageSheet modals, Settings from the map and Edit profile
over the journal, which stays mounted under it.

Settings (src/Settings.tsx, pageSheet, from the menu under your photo) - "Settings" 34/700, × top right
├─ Account                     which sign-ins, add the other, sign out (back to the gate),
│                              delete; the subscription
├─ How unlocking works         the one place that answers "why can't I read this"
├─ Location, Notifications     state + action; the Switch is why this is not inside the cover (rule 9)
└─ About                       privacy policy, contact, OpenStreetMap

Edit profile (src/EditProfile.tsx, pageSheet, from the header) - "Profile" 34/700, × top right
├─ the photo, 112pt            Choose photo / Take photo, square crop; Remove photo. Public,
│                              like the name: it signs what you file (src/Avatar.tsx)
└─ Your name                   what submissions are signed with, saved as typed. Blank = Anonymous

There are no tabs on the map, and no map of what is locked: the planner draws the walk it
offers, and a walk draws only itself. Only a stop of the walk in progress opens, standing on it.
On a walk the bottom is where you act, one tap each: Add, the walk card and Center on me;
in the planner the card's own buttons are. The top is where you read:
your level, with Journal top left and you top right (docs/10,
"One gold button that changes").
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
| `src/Glyph.tsx` | every icon: an SF Symbol at a point size, in a theme colour, bouncing when `bounce` changes. Not what is locked: that is always a locket's keyhole face |
| `src/MemoryMarker.tsx` | one locket, keyhole and all until opened, lit when it can be opened from here |
| `src/lockets.ts` | the six lockets: their pin images and the level each opens at |
| `src/LocketUnlock.tsx` | the hold: the key, the ring, the lid, the dive, the haptics; one lid per locket |
| `src/lockMotion.ts` | the worklet curves and pivots LocketUnlock moves by |
| `src/UnlockHere.tsx` | the locket over the map, with the place it opens |
| `src/LevelPill.tsx` | the top of the map: your level and an XP bar, the number rolling (`@expo/ui`) |
| `src/WalkCard.tsx` | a past walk drawn as its shape: the cards in Your walks, the finish card's and journal rows' small shape |
| `src/Plan.tsx` | the planner card, home: a walk drawn at once, its list, length and shape, then accept |
| `src/useBreath.ts` | the next stop's hop |
| `src/Memories.tsx` | the journal, which is you: photo, name, numbers, then walks, unlocked, and what you filed |
| `src/Settings.tsx` | account, how unlocking works, location, notifications, about. Its own sheet, from the map's ⚙ |
| `src/EditProfile.tsx` | the photo and the name. Its own sheet, from the journal's header |
| `src/Avatar.tsx` | a photo, an initial or nobody, in one circle at any size |
| `src/Flourish.tsx` | the leaf-and-curls divider, twice on an open story: under the byline, before the notes |
| `src/CloseButton.tsx` | the × that closes a card, sheet or page (rule 12); with another `icon`, the walk card's skip and a story's ⋯ |
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
rather than a grey, gold *lightens* so it holds on a dark map, and `faded`
lightens too — a locked pin has to survive a dark map, where the light-mode
value disappeared entirely.

**Warm and rounded** since 2026-09-27 (`docs/09-visual-design.md` part 8):
paper and one rounded face, capsules, and glass only over the map. **Gold,
emerald and purple** since 2026-10-04 (docs/10, "Lockets").

| Token | Hex | Used for |
|---|---|---|
| `paper` | `#F7F4EE` / `#161412` | every surface. Not white, and close to the muted map underneath |
| `paperRaised` | `#FFFDF9` / `#201D19` | the rare surface that must lift off the paper |
| `ink` | `#1C1917` / `#F2EDE4` | primary text, solid buttons |
| `inkSoft` | `#4A443D` / `#BDB5A8` | secondary prose |
| `inkFaint` | `#746D65` / `#908979` | labels, captions |
| `rule` | `#E0D9CC` / `#332E27` | hairlines. Rules do the work shadows used to |
| `faded` | `#776E64` / `#9A9086` | a locked pin out of reach. Dark enough for parchment, light enough for a dark map |

**Three colours, and each means one thing.** Blue is left to the map and
to your location dot. The lockets' own metal is `metal` in `theme.ts`, one set
in both themes, for the unlock's Svg only.

| Token | Hex | Meaning |
|---|---|---|
| `gold` | `#86661A` / `#D9B45E` | **a memory, and the way to it.** The next stop's tag, the preview's line (washed out: `solid().line`), the walk's bar, the primary button, a link, errors |
| `goldSoft` | `#F1E4C2` / `#352A14` | the quiet button's fill |
| `goldDeep` | `#5E470F` / `#A8822E` | the ledge under a gold button or chip. A mark, never text |
| `goldSoftDeep` | `#DCC992` / `#241C0C` | the ledge under the quiet button |
| `seal` | `#1F6B4F` / `#3FA57E` | **openable.** Emerald: the in-reach halo and tag, the reach circle, the hold's ring. A fill, never text |
| `sealInk` | `#F7F4EE` / `#0B1F17` | anything drawn on seal: a lit pin's tag, the pill's words |
| `sealSoft` | `#D5EBDF` / `#173528` | the ring filling during a hold |
| `sealDeep` | `#16573F` / `#7FD1AE` | seal as words or a thin mark on paper: "attachments waiting" |
| `purple` | `#5B2A6E` / `#C59BD8` | **what you earned.** The level pill, the streak's flame, an epic's line, your row on the board |

Gold and seal differ in hue and lightness: gold beside gold is no signal, so
openable is the one thing on the map that is not gold.

**Buttons are `button.solid`, `button.quiet` or `button.outline`** from
`theme.ts`, with `buttonText` inside: 52pt capsules, gold with paper text,
soft gold with ink text, or a rule outline. Each sits on a 4pt ledge of its
own colour (`goldDeep`, `goldSoftDeep`, `rule`; 3pt on `small` and on a
chip), and pressed it sinks onto it: `sunk()` in `theme.ts` thins the bottom
border and adds the difference to the top margin, so nothing beside it moves.
`dim()` does this for any style with a ledge; a Pressable whose style is on a
child (Submit's `Chip`) calls `sunk` itself. Two circles take a 3pt lip as well:
a story's ‹ › pager step (rule) and a recording's play disc (gold on
`goldDeep`). A screen adds only where one sits
(margin, alignSelf), never its own padding or border. Post is the
same capsule at 36pt: spread `button.small` after it, `buttonTextSmall` inside,
`hitSlop={4}`. An action inside a page is not a button but `label` text with
`hitSlop={12}`: inkSoft for Rewrite, Remove and the photo actions, gold for
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
`color.paper` on gold and `color.ink` on the quiet and outlined buttons.
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
(Journal, Add, the walk card, the keys pill, you,
Center on me) are `GlassButton` from `src/Glass.tsx`: iOS 26's Liquid Glass,
or raised paper with `lift` where glass is unavailable. Never glass on a sheet
or a card, never glass on glass. The one gold thing in the bottom row, Plan a
walk or Turn on location, is not glass but `button.solid` with its lip
(2026-10-03): a ledge under glass reads as a shadow glued on. The walk card is
untinted: the next stop's pin is the gold on the map. No `GlassContainer`: two circles merging read as
one odd shape (the founder, 2026-10-01), and the container swallows taps in
its gaps. Glass takes colour from what is under it: Journal reads cyan over a lake,
and that is the material, not a bug. Every glass control is warmed by
`solid().frost`, a thin paper tint (a dark gold one in dark mode), so it
reads as frosted paper and not as cold white (2026-10-03). A glass
control squishes to 0.92 and springs back with a little overshoot rather than
dimming: opacity on a glass view's parent stops the effect rendering. Inside sheets, hierarchy is still hairlines and
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
a capsule: every glass control over the map), `floating` (`paperRaised`, `card` corner, `lift`: the unlock card,
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
touched. A third is a rule you have not written yet. The buttons' ledge is a
border, not a shadow.

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
| `sealInk` on `seal` | 5.8:1 | 5.6:1 |
| `paper` on `faded` | 4.6:1 | 5.9:1 |
| `paper` on `gold` | 4.9:1 | 9.3:1 |
| `gold` on `paper` | 4.9:1 | 9.3:1 |
| `gold` on `paperRaised` | 5.3:1 | 8.5:1 |
| `ink` on `goldSoft` | 13.8:1 | 12.1:1 |
| `purple` on `paper` | 9.6:1 | 7.9:1 |
| `sealDeep` on `paper` | 7.7:1 | 10.2:1 |
| `sealDeep` on `sealSoft` | 6.8:1 | 7.4:1 |

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
9. **The map never unmounts.** The journal is a modal over it, not a screen
   in its place, and the map sits under it. Unmounting the map
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
    ("Retold by AI from <source>" or "Left by X"), the button and the heart pinned
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
- **Every other action is text** in the label voice: the toolbar's B, I,
  Heading, Quote, Divider, Photo, Camera, ↑ ↓ and Preview, a photo's S M L
  and Left Center Right, Remove photo, Delete this memory (gold, two taps).
- **The story is blocks** (docs/10, "A story has a little markdown"): a
  paragraph, a heading, a quote, a divider, a photo. Markdown typed works as
  well as the toolbar: a blank line starts a block, `## ` and `> ` turn it,
  `---` is a divider, and the marks stay in, faint. Backspace in an empty
  block takes it away. ↑ ↓ move the block being written, or a tapped photo.
  The toolbar sits under the bar, never over the keyboard. Preview is
  `StoryBody`, the open sheet's own layout, wrap and all.

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
- **Buttons are verbs that say what happens**: Start walk, More walks,
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
| map | you, the streets, Journal, Add and Plan a walk; the locked memories around you, faded, that do not open | Plan a walk → preview |
| preview | the walk on the map, the card with its length and shape | Start walk → walk; × (any step) → map |
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

A memory draws as its locket (docs/10, "Lockets"): the one its author chose,
or one drawn at random for an extracted memory. Locked, it shows its keyhole;
opened, the same locket without one, from `mobile/assets/lockets/` through
`src/lockets.ts`. A spot with several draws the first one's. It changes for
one reason only — **it can be opened from where you stand**, and on a route
day only if it is one of the route's stops (F25) — and then it scales 1.35
over an emerald `halo` wash. That is the whole visual language. The padlock
it replaces (2026-10-02, "a mini lock instead of pins") was drawn in Views;
before that, five ink states and a shape per layer, which was a legend nobody
should need.

| When | Geometry | Tokens |
|---|---|---|
| locked | the locket's keyhole image, 32×32 | the art's own gold |
| unlocked (`plain`, `stamped`): every memory in it opened | the locket without its keyhole, 32×32 | the art's own gold |
| `unlockable`: inside the radius **and openable by walking** | the locked image, scale 1.35; wash 46 | wash `halo` |
| the next stop on today's walk, not yet in reach | the locked image, scale 1.35; hops (`useHop`), still under Reduce Motion | as locked. Size and the hop tell it apart |
| a stack, or one of today's stops | tag min-w 20, h 20, radius 10, border 2, top right | `gold`, count `paper` (`seal` with `sealInk` on a lit pin) |
| locked, off a walk (`opacityOf`) | same pin, fading with distance | opacity 1 to 500 m, down to 0.3 at 3 km, in tenths |
| locked, on the home map (`FADED_PIN`) | same pin, never lit, a tap does nothing | opacity 0.4 |

**Every image gets an explicit size.** The art's @2x and @3x are not two and
three times its @1x (48, 192, 432 px), so an image left to its intrinsic size
draws at a different size on every density.

**The badge sits in the corner** so the blue location dot is never under it.

**`seal` means openable now, and nothing else.** A seal-coloured pin you
cannot open is an invitation that refuses you (F11). Only a walk's stops are
ever drawn at full strength, and the home map's faded pins never light, so
every lit pin can be opened. Emerald is never in the locket art, so only the
halo and the tag say it. Locked near and locked
far draw the same locket, bar a fade with distance (2026-10-02:
full detail near you, a glow further out, so the map reads as where to go
next rather than a checklist), and earned and never gated the same open one
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
for the frame cost and are keyed on the group, its reach and its locket, so they repaint
exactly when their state changes and never otherwise.

**A new walk draws itself, like a loading bar filling.** Once the camera's
fit has landed (never under the flight), `RouteLine`'s `draw` traces the
preview's line from you over 1.2 s: one curve, at a speed even along the
route's distance (not its points), starting at a third of its speed and
finishing a little faster. Progress that accelerates feels fastest, and a
slow tail slowest (Harrison et al., UIST 2007). It moves the polyline's
`strokeEnd` (patched into react-native-maps), so no overlay is rebuilt per
frame. Each stop mounts when the tip is 50 ms short of it (`onReach`, at the
stop's nearest point on the line). Mounting, not animating, so the rule
above holds. While a re-plan is on its way the old line fades to 40%
(`dim`). Reduce Motion draws it whole. Only the preview draws: a finished
or past walk is already known.

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
65% after a primer. The planner opens at launch and never asks: without a yes
it plans from central Copenhagen, and its **Use my location** is the ask, a
press with a reason; then the walk is planned again from where you are.
`getForegroundPermissionsAsync` runs first so somebody who already said yes is
never asked twice, and a hard refusal (`canAskAgain === false`) swaps the button
for **Open Settings**, which is the only route back.

Position is then *watched*, not read once (`watchPositionAsync`, 5m interval,
foreground only). Walking into range has to change the map by itself.

## A link that can fail

Every link goes through `openLink` (`src/link.ts`): an in-app Safari sheet
with Close, so a source credit or the privacy page never throws a walker out
of the app mid-walk. It rejects when nothing can show the link — a managed
device. The watch link catches that in `MemorySheet` and says so. A control
that silently does nothing is the failure people blame on themselves.

## Accessibility

The unlock is a *hold*, which is the easiest gesture to make exclusionary, so
this is not a polish pass:

- The control has a role, a label, and a hint naming the gesture, and VoiceOver's
  plain activation opens it. That covers screen-reader users and not every motor
  impairment — the `ponytail:` marker in the file names the gap.
- Markers carry an `accessibilityLabel` with their state. The callout title says
  *where*; only the colour says whether you can read it, and colour is not
  available to everyone.
- Every state that colour distinguishes is also written or drawn: the locket's
  keyhole face (a shape, read out as "Locked"), "within reach", "Nearest locked memory".

## The unlock control

`src/LocketUnlock.tsx`, with its curves in `src/lockMotion.ts`. The one place
in this app allowed to be playful. Everything else is a quiet map; this is the
moment the product is *about*, so it gets the animation budget. It is the
memory's own locket opening (docs/10, "Lockets"). Spec, so it does not get
re-invented per screen:

- **Press and hold, not tap.** 900ms. A tap is a click; a hold is a key
  turning. It also makes an accidental unlock almost impossible, which matters
  because unlocking is irreversible.
- **The locket takes the key.** Over the hold a gold key slides into the
  keyhole, grinds to 25° and gives to 90°, the locket turning toward you to
  take it and back. The ornament (the compass rose, the guilloché) swings and
  settles; the bail presses home. One derived value (`motion`) turns the hold
  and the opening into every moving number, so nothing drifts out of sync.
- **A ring fills around it, and the fill is linear.** It is a promise about
  when you may let go, and an eased progress bar is a progress bar that lies.
  Everything that builds is layered over it. Releasing early springs it back,
  visibly, so the person understands they let go rather than that it failed.
- **Haptics carry the feel.** `Light` on press-in, `Rigid` as the key seats
  and as it gives, `Soft` and `Rigid` as the lid unlatches, `Medium` at the
  commit, and `notificationAsync(Success)` when the lid opens. `Success` is
  reserved: it is the one pattern in the app that means a thing was earned.
  Never on release-cancel, which would read as a reward for failing. One more
  `Light` fires in `App.tsx` the moment the reachable set goes empty to
  non-empty — walking into range is the moment the app is for. The
  transition, not the state: `withinReach` gets a new array identity every
  5 m, so the effect keys on a boolean and a ref.
- **It waits for the server, then opens.** A completed hold ends in a
  *checking* beat (the lid trembles on its latch, at least 420ms), and the lid
  opens only on a yes: a locket that swings open and then shuts on a refusal
  would be a lie. It replaced the burst played over the request (docs/10,
  "Lockets"). On a yes the lid swings past 90° on its hinge, sparkles pop, the
  inside glows with the place engraved, and the camera dives in. The story
  rises into `MemorySheet` from the dive (`onDiveStart`, `revealId`): the
  lede, the rest, the quote, then "Then and now" and the credit, each rising
  12 px over 360 ms, 90 ms after the last. App holds the opening locket on
  screen (`opening`) until the dive ends, because an opened memory leaves the
  ring's list.
- **Transform and opacity only, on the UI thread.** Reanimated worklets; the
  Svg art never re-renders, only the views holding it move. Reduce Motion
  drops the tilt, sway, sparkles, shine and zoom and cross-fades instead.
- **It lives on the map, low, and says where.** `src/UnlockHere.tsx` puts a
  180pt locket just above the bottom row, where a thumb reaches, and under it
  the place and its year or source, so the hold says what it opens. More than
  one in reach adds ‹ › and "2 of 3" beside the words, never beside the
  locket, so a thumb aiming for an arrow cannot start the hold. Each memory
  gets a fresh locket (`key`), so ‹ › never carries a half-turned key over. No
  caption, cost or error: a stop of the walk costs nothing. It needs no ×
  because walking away takes it away (rule 12). The parent must not clip it:
  the dive scales it past its bounds.
- **A refusal springs back.** The key backs out, the ring empties, and
  `notificationAsync(Warning)` fires; a screen reader is told the reason,
  since nothing draws it.
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
people. As built, the `activate` accessibility action runs the hold in 300ms,
which covers VoiceOver and not every motor impairment. A "tap to unlock"
setting is the next rung if asked for.

**The button never decides anything.** It asks
`POST /v1/memories/{id}/unlock` and the server re-measures, so a
completed hold can still come back refused when GPS has drifted. The spring
back says so, and VoiceOver hears "Not quite there. Take a few more steps."
rather than meeting a control that looks broken.

## Flows

Documented flows live in `docs/08-ux-flows.md`. Build toward those, and when a
flow changes, change that file in the same commit.

Writing is F5 (file a memory), F20 (report or block) and F21 (be somebody).
Sign-in is F22, the first flow, and it is Google and Apple only — see
`src/SignIn.tsx` for why, and for why neither button works in Expo Go.

The paywall is F35 (`src/Paywall.tsx`). One sheet at a time: it opens from Settings,
the walked-out planner's **More walks**, or the finish card's quiet
**Another walk today ›**, never on top of a sheet and never by itself. Yearly
first and solid, monthly outlined. No price is ever written in the app; the
store's `priceString` and `pricePerMonthString` are. Without a RevenueCat key
it says "Subscriptions aren't available right now.", never a button that
cannot work, and **Not now** is always there (rule 1).
