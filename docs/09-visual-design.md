# Visual design: what was researched, what was kept

Notes from making the app look like something rather than a default. Written
down because the next agent will otherwise re-run the same searches and land on
the same trend listicles, and because two of these findings are *rejections* —
the useful half.

Tokens and component rules live in [`mobile/UI.md`](../mobile/UI.md). This file
is the reasoning behind them.

## 1. The map was competing with the app — **kept, biggest win**

The default Apple Maps style draws the Statue of Liberty, a photograph of
Barclays Center, green parks and coloured route shields. Every one of those is
more colourful than a grey padlock, so the app's only content lost to the
backdrop.

`mapType="mutedStandard"` is Apple's own answer: a map type that exists
specifically to make overlaid markers pop. Paired with
`showsPointsOfInterests={false}` (note the plural — the singular spelling type-
checks as an error, which is a useful accident) the map becomes a quiet
parchment and the pins become the subject.

Android has no muted type. `customMapStyle` takes a Google style array, and is
**Google-provider only** — which is also why iOS cannot share it. The
equivalent lives in `mobile/src/mapStyle.ts`, and every rule in it removes
something rather than adding a colour.

This was one prop and it changed more than everything else combined. Do the
cheap structural thing before the expensive decorative one.

## 2. Glass chrome — **tried, tuned, then removed**

iOS 26's design language ("Liquid Glass") puts controls on floating translucent
layers so the content leads. Over a map this is not decoration: a solid white
bar hides the street you are standing on.

`expo-blur`'s `BlurView` is native on iOS and a translucent view on Android,
which is the right fallback — identical layout, missing texture.

Two things the trend write-ups do not tell you, both found on screen:

- **Transparent is not frosted.** The first attempt — 55% white, blur intensity
  70 — was unreadable over a street map. NN/g's criticism of Liquid Glass is
  precisely this: text over blur loses contrast. It sits at 82% now, which keeps
  a suggestion of the map moving underneath and nothing more. The trend is
  "glass"; the requirement is still 4.5:1.
- **A parent's `overflow: hidden` does not clip the native blur on iOS.** The
  rounded background painted correctly while the blur stayed a rectangle, so a
  pill rendered as a square with rounded paint under it. `Glass` takes an
  explicit `radius` and puts it on both layers.

**Glass only where something is behind it.** The tab bar got the treatment and
then lost it: it sits *in* the layout, not over the map, so there was nothing to
blur, and making it an overlay would have covered the Apple Maps attribution
(rule 7 in UI.md).

*(2026-09-27: native Liquid Glass came back for the map controls only - part
8. It is the system material, not a translucent white pill, so neither
finding below is what killed it.)*

**And then the rest of it went too** — see part 5. Glassmorphism turns up on
every list of tells for a generated interface, and having fought it to 82% white
to keep it readable, what was left was a translucent white pill: the cost of the
dependency without the effect. `Glass.tsx` is deleted. The two findings above
survive it, because the next person will reach for `expo-blur` anyway.

## 3. Depth — **kept only where something really floats**

Soft large-radius shadows read as floating; tight dark ones read as stickers.
That still holds for the two things that genuinely hover over the map — the
"Turn on location" button and the location primer.

Everywhere else the shadows came off in part 5. Stacked floating cards are the
card-grid tell, and editorial layouts have always used rules and weight instead.

## 3a. No line while walking; the next pin hops — **decided 2026-09-24**

While walking there is no line. The next unearned stop is `route` blue and
hops, and when it is earned the one after it takes over: the pin says where
to go, so no line has to. Only the preview draws the loop.

The preview's line is drawn the way Apple Maps draws a route: `route` blue
over a darker blue edge, *under* the street names. Apple's own route (ETA
bubbles, turn icons) is Maps.app's, not API; what MapKit gives anyone else
is `MKPolylineRenderer`, which `<Polyline>` already is. What made ours look
pasted on was the level: react-native-maps adds overlays with `addOverlay:`,
which is `MKOverlayLevelAboveLabels`. `mobile/patches/` moves polylines to
`MKOverlayLevelAboveRoads` (a native rebuild picks it up).

It was ink over a paper casing before that, and before that it marched dots
by ticking `lineDashPhase`, and it restarted and stuttered. That is not fixable where it
was: on iOS react-native-maps answers *any* Polyline prop change with
`removeOverlay` + `addOverlay` (`AIRMapPolyline.m`, `update`), so every tick
re-rendered the line from scratch. It was also 70% `inkSoft`, which on
parchment is just grey.

Two ways to get a line that moves smoothly, and why neither was taken:

- **MapLibre**, `line-gradient` + `line-trim-offset`, the way Mapbox animates
  routes. Native and smooth, but it reverses "stay on react-native-maps" below:
  a dev build, no Expo Go, and a tile source.
- **A Skia or SVG layer over the map**, animated on the UI thread. Smooth while
  the map is still, but it has to re-project on every pan and zoom, so it trails
  the map while you move it.

Motion stays where it means something: the ring and the next pin's hop. Neither the line nor the hop is `seal`: seal
means openable.

## 4. What was rejected

- **Neomorphism / soft-UI / skeuomorphic textures.** Recurring in every 2026
  trend list. They work by making everything look slightly pressed, which is
  actively wrong for an app whose single most important control is a thing you
  press. The hold ring earns its tactility by moving.
- **A dark map theme.** Tempting and easy. But the content is a padlock the
  colour of the state it is in, and amber-on-dark and grey-on-dark are much
  closer together than they are on parchment. Legibility of the one signal beats
  looking moody. Worth revisiting only with a proper dark scheme for both
  states, not as a map-only switch.
- **`react-navigation` for the tab bar.** Three destinations, no stack, no
  params, no deep links. The router would be larger than the thing it routes.

## Sources

- [react-native-maps MapView docs](https://github.com/react-native-maps/react-native-maps/blob/master/docs/mapview.md) — `mutedStandard`, `showsPointsOfInterests`, `customMapStyle` being Google-only
- [expo-blur / BlurView](https://docs.expo.dev/versions/latest/sdk/blur-view/) — native on iOS, translucent fallback on Android
- [Liquid Glass Is Cracked, and Usability Suffers in iOS 26 — NN/g](https://www.nngroup.com/articles/liquid-glass/) — the contrast criticism that set the 82% figure
- [Liquid Glass UI 2026: Apple's New Design Language](https://medium.com/@expertappdevs/liquid-glass-2026-apples-new-design-language-6a709e49ca8b) — controls float above content, content leads
- [react-native-maps Polyline docs](https://github.com/react-native-maps/react-native-maps/blob/master/docs/polyline.md) — `lineDashPhase` iOS only, `strokeColors` MapKit only
- [Mapbox: animate a line](https://docs.mapbox.com/mapbox-gl-js/example/animate-a-line/) and [`line-trim-offset`](https://github.com/mapbox/mapbox-gl-js/pull/11570) — how a native map animates a route
- [Customizing the map style with cloud-based maps styling](https://github.com/react-native-maps/react-native-maps/discussions/4368) — Map IDs as the newer Google approach, not used here

---

# Which map provider

Researched 2026-09-20, decided with the user. Recorded so it is not re-run: the
answer turned out to be "nothing to do", which is exactly the kind of conclusion
that gets re-litigated because it leaves no artefact.

## The finding that reframed it

**The app has no map cost or licensing problem. The embed does.**

Google's Maps SDK for Android and Apple's MapKit are both free with unlimited
usage. Google's late-2025 move to subscription tiers ($100–$1,200/month) hit
Dynamic Maps and the web SKUs, not the mobile SDKs. So `mobile/` costs nothing
at any scale, with no key at all on iOS.

`api/embed.py` is the one with a real problem, and it is licensing rather than
money: it serves OSM's public tiles, which the OSMF policy forbids for this and
which they can block without notice.

## The app — **decided: stay on react-native-maps**

| | Cost | Dev build? | |
|---|---|---|---|
| **react-native-maps** | $0 | No — runs in Expo Go | **Chosen** |
| expo-maps | $0 | **Yes** | Expo's official direction, same two providers, no functional gain |
| MapLibre RN | $0 + tiles | **Yes** | Only buys identical styling on both platforms |

`expo-maps` is worth knowing about: it is where Expo is heading, and
react-native-maps did have real breakage on SDK 55 (this project is on 57 and
fine). Migrating costs the Expo Go workflow — no more `openurl` and a reload —
and buys nothing the app does not already have. Revisit **only** if a future
Expo SDK breaks react-native-maps, which is the event that would change the
maths.

MapLibre earns a look the day one identical map style on both platforms becomes
a requirement. It is not one now: `mutedStandard` and the Android style array
already land in the same place.

## The embed — **decided: leave it, and gate shipping on it**

Not Stadia, not Protomaps, not yet. Three reasons:

1. The embed has no users. Paying for tiles or building a tileset solves a
   problem nobody has.
2. Tiles are not its blocker. There is no public API host for the iframe to
   point at, so fixing tiles first is fixing step four of four.
3. `TILE_URL` is one constant, deliberately, so the switch is a one-line change
   on the day it matters.

What that day looks like, whichever comes first — someone wants to embed it, or
it goes on a public host:

| | Cost | Work |
|---|---|---|
| **Stadia Maps** | Free tier, then $20/mo per 1M credits | One URL and a key |
| **Protomaps / PMTiles** | ~$3/mo on Cloudflare R2 at real volume | Build and refresh the tileset yourself |
| MapTiler | Free 5GB, up to $295/mo | Like Stadia, pricier at the top |

Protomaps is the better fit on principle — a single file on static storage, no
vendor, no per-load billing, the same self-sufficiency that keeps geocoding out
of this pipeline. Stadia is the faster correction. Pick on the day, based on
whether the embed has traffic worth owning.

`TODO.md` 2.0 carries this as a blocker on deploying the embed publicly, and
`api/embed.py` says it at the constant.

## Sources

- [Google Maps Platform core services pricing](https://developers.google.com/maps/billing-and-pricing/pricing) and [subscriptions](https://developers.google.com/maps/billing-and-pricing/subscriptions) — mobile SDKs free and unlimited; the tiers apply to Dynamic Maps and web SKUs
- [Introducing expo-maps](https://expo.dev/blog/introducing-expo-maps-a-modern-maps-api-for-expo-developers) and [Expo Maps docs](https://docs.expo.dev/versions/latest/sdk/maps/) — Apple Maps on iOS, Google on Android, development build required
- [react-native-maps not compatible with Expo SDK 55](https://github.com/expo/expo/issues/43288) — the breakage that would force the question
- [MapLibre React Native — Expo setup](https://maplibre.org/maplibre-react-native/docs/setup/expo/) — config plugin, custom native code
- [OSMF Tile Usage Policy](https://operations.osmfoundation.org/policies/tiles/) — why the embed cannot ship as it stands
- [Stadia Maps pricing](https://stadiamaps.com/pricing/) · [MapTiler pricing](https://www.maptiler.com/cloud/pricing/) · [PMTiles](https://docs.protomaps.com/pmtiles/) and [a real hosting bill](https://blog.pinballmap.com/2024/11/05/protomaps-tile-hosting/)

---

# 5. "Too AI-y, too clean, no personality"

The user's words, and correct. This is the round that matters, so the reasoning
is worth more than the palette.

## The finding

> The AI-generated look is not a single visual style — it is the absence of
> decisions.

A designed interface is full of small choices that could have gone another way.
A generated one applies the safe default everywhere, because the safe default is
statistically what the model has seen most. Tailwind's `indigo-500` and Inter
"win" for the same reason: they are the literal centre of the training corpus.

Measured against the community "anti-slop" lists, this app was guilty on five
counts, and I had personally added two of them that same afternoon:

| Tell | Where it was |
|---|---|
| Tailwind's zinc ramp | every colour in the app — `#18181b`, `#71717a`, `#f4f4f5` |
| The system sans everywhere | every string |
| Glassmorphism | the banner and the reach pill, added in part 2 |
| Floating white cards with soft shadows | banner, primer, pills, sheet |
| `amber-500` as the accent | the entire unlock mechanic |

Notably, none of that was *bad*. It was fine, and it was nobody's decision.

## The direction, derived from the product

The fix is not a different trend — that is the same mistake with a new default.
It is to have a reason.

This app is an archive of anecdotes pinned to coordinates: things people said
happened somewhere, which you have to physically go and stand in to read. Its
real-world neighbours are the **field guide**, the **historical plaque** and the
**passport stamp**. Not the SaaS dashboard, which is what it looked like.

So:

- **Paper, not white.** `#F7F4EE`, which also happens to sit close to the muted
  Apple map underneath, so the sheets read as cut from the same stock.
- **Ink, not grey.** Warm near-blacks and sepias.
- **A serif carries the prose**, because these are stories somebody told.
  Fraunces — an old-style serif with its wonk left in, so it has an opinion,
  which is the entire requirement.
- **A mono carries the apparatus.** Distances, counts, labels, tab names. A
  number in a mono reads as a *measurement*; the same number in the body face
  reads as more prose. This is what makes the app feel like an instrument.
- **One accent: stamp ink** `#8A5A17` - a warm ochre, moved 2026-09-23 from a
  stamp red (`docs/10-decisions.md`, "Warm accent, not a reskin";
  `mobile/UI.md` has the contrast re-measurement). Everything openable wears
  it and nothing else does. Deliberately not `amber-500`.
- **Rules and weight, not shadows and cards.** Editorial layouts have always
  done hierarchy this way, and it is the shortest route out of the card tell.
  Shadows survive only on the two things that actually hover over a map.

A knock-on: freeing the accent freed the watch button from YouTube red, which
only made sense back when the map pins were red too. It is ink now.

## What this cost

Two Google Fonts packages and `expo-font`, a `src/theme.ts`, and about an hour
of restyling. `src/theme.ts` is arguably overdue on its own — UI.md previously
admitted consistency was held together "by convention and reviewing eyes".

## The rule to keep

Every value in `theme.ts` should be one somebody chose. If a future change
reaches for a Tailwind hex or the system font, that is the tell coming back.
(The system font half is superseded: see "One font, the map's" in
`docs/10-decisions.md`.)

## Sources

- [Why AI Design Looks Generic](https://superdesign.dev/blog/why-ai-design-looks-generic) — "the absence of decisions"
- [The Purple Gradient Problem](https://dev.to/james_anderson_h/the-purple-gradient-problem-why-ai-ui-all-looks-alike-and-how-to-fix-it-3j65) — why the defaults are the statistical centre
- [SaaS UI Looks AI-Generated? 7 Fixes](https://www.saasui.design/blog/saas-ui-looks-ai-generated) — the tells, including the banned-pattern list that glassmorphism is on
- [Expo: Fonts](https://docs.expo.dev/develop/user-interface/fonts/) and [expo/google-fonts](https://github.com/expo/google-fonts) — how the two families load

---

# 6. The web surfaces never got the memo

Part 5 rewrote the app and stopped at the app. `api/card.py` and `api/embed.py`
render HTML for the same product and were never touched, so the one artefact
that leaves the phone is still on the palette part 5 threw out.

## The finding

`api/card.py` ships this, verbatim:

```css
:root{--bg:#fff;--fg:#18181b;--muted:#71717a;--rule:#e4e4e7;--accent:#dc2626}
```

That is Tailwind's zinc ramp and `red-600`, set in `system-ui` — four of the
five counts part 5 pleaded guilty to, on the surface with the widest audience.
`api/embed.py` is `system-ui` with no palette at all. It also puts a coloured
left border on the contrast note, which is on every list of tells for a
generated card.

This matters more than an internal screen would. Geo-gated content cannot be
shared by linking to it — you had to be there — so a screenshot of this card is
the only distribution channel the product has, and `docs/10-decisions.md`
already calls screenshot-native cards core rather than polish. The card is also where the
attribution lives, which is why it is rendered server-side in the first place.

## The mapping

The markup does not change. Only the five variables and the two faces do.

| Card variable | Becomes | Why not the obvious one |
|---|---|---|
| `--bg` | `paper` `#F7F4EE` / `#161412` | |
| `--fg` | `ink` `#1C1917` / `#F2EDE4` | |
| `--muted` | `faded` `#776E64` / `#9A9086` | **not `inkFaint`** — the card sets 13–14px in this colour and `inkFaint` is 3.4:1 on paper. See "Contrast, measured" in `mobile/UI.md` |
| `--rule` | `rule` `#E0D9CC` / `#332E27` | |
| `--accent` | `seal` `#8A5A17` / `#D9A54B` | and on a link only, never on a border-left |

Set `.place` in Fraunces 700 at 30/36 and `.summary` in Fraunces 400 at 19/31 —
the same hero size the app's sheet uses, because it is the same sentence. The
`.layer`, `.when` and `.credit` lines take IBM Plex Mono.

Both faces are on Google Fonts, so one stylesheet link covers it. Keep a real
fallback stack: this markup gets rendered by link-preview bots that fetch no
fonts at all, and a card that collapses to Times is worse than one that was
never restyled.

Replace the contrast note's left border with a hairline above it in `rule`,
which is how the rest of the product separates things.

## Done, and what holds it in place

`CARD_CSS` carries the five variables and both faces; the embed took the
typography and kept `Canvas` and `color-scheme: light dark`, because it lives in
other people's pages and adapting to the host is right for a widget — the card
inside its panel is what carries the palette.

Two things were worth learning in the doing.

**The card's own test forbade the font link.** `test_card.py` asserted
`"<link" not in html` under the banner "must render with no asset pipeline",
which is the right rule expressed as a proxy that had since become too strict. It
now permits exactly one stylesheet and only from `fonts.googleapis.com`, and
still fails on a script or a second link. The stacks behind the two faces are
real, because a link-preview bot fetches no fonts at all and a card that
collapses to Times is worse than one that was never restyled.

**The palette is copied by hand and now has a guard.** There is no build step
between `mobile/src/theme.ts` and Python, and eleven values do not justify
building one. `tests/test_palette.py` reads the hexes straight out of `theme.ts`
and fails if the card drifts from them — and, in the same pass, holds every
text-on-ground pair to 4.5:1 in both themes. It caught a second contrast failure
nobody had measured: `inkFaint` cleared AA on `paper` in the dark and missed it
on `paperRaised`, which is where the inputs sit.

# 7. Teal fights the map — **shipped 2026-09-27, with a gold seal (part 8)**

The founder: teal works with neither the buttons nor the route line, and the
scheme should be rethought from nothing, the logo ignored.

## The finding

**The base map already owns blue, green and grey.** Water is blue and parks
are green on Apple's muted map, and Copenhagen is lakes and harbour. The user
dot is system blue. Teal sits between water and park, so a teal pin reads as
map, and the `route` blue line is drawn over the lakes' own blue. Contrast is
not the problem (teal is 5.3:1 on the land); hue is. Cartography's rule is a
muted ground and one saturated accent for what matters, about 10% of the
screen.

**The hue no map uses is warm red.** Aviation draws the active route in
magenta for the same reason; Komoot's highlights are red dots, Strava's line
is orange. Okabe-Ito, the colour-blind-safe set, pairs vermilion `#D55E00`
with orange `#E69F00` as distinguishable under every common deficiency, which
is close to a red accent beside today's ochre `seal`.

**Progress reads grey behind, colour ahead.** Mapbox's navigation SDK greys or
hides the route line you have walked; fleet apps draw done legs grey, the
current one lit, the rest in the route colour. Steppers mark done, current and
upcoming, and done is always the quiet one.

## The scheme

One accent replaces both `brand` and `route`. Blue is left to the map and to
you.

| Token | Hex light / dark | Means |
|---|---|---|
| `ember` (new) | `#B83A12` / `#F2703F` | **a memory, and the way to it.** Every pin at rest, the solid primary button ("Plan a walk"), the route line ahead of you, the next stop (bigger, hops), a later stop's number tag. 5.2:1 on paper, 4.8:1 on the dark map |
| `seal` | unchanged | **open it now.** The pin in reach, as today |
| `faded` | unchanged | **behind you.** A stop already opened, the legs already walked |
| `ink` | unchanged | text, quiet and outline buttons |
| system blue | the OS's | **you.** The location dot, and nothing of ours |

On a walk that reads grey, gold, red: behind you, under you, ahead of you.
Next and later differ by size and the hop, not a hue, so a walk carries two
colours and a grey, not four colours.

## Open before shipping

- Off-route pins during a walk: `ember` would compete with the stops. Smaller,
  or at reduced opacity, but not `faded`, which now means done.
- `ember` and `seal` are both warm. Size, the halo and the marker's `title`
  carry "openable" too, but look at both on a real map, and under a
  deuteranopia filter, before committing.
- `tests/test_palette.py` holds text pairs to 4.5:1; `ember` with `paper` text
  on the button clears it in light (5.2) and needs `ink` text in dark.
- The logo stays teal until someone redraws it.

## Sources

- [Mapbox Navigation SDK, route line (traveled colour)](https://docs.mapbox.com/android/navigation/guides/ui-components/route-line/)
- [Mapon, route colours: grey done, green current, blue remaining](https://help.mapon.com/en/articles/376803-what-do-the-route-colours-mean-on-the-tasks-and-routes-map)
- [Apple, What's new in MapKit (muted emphasis for overlays)](https://developer.apple.com/videos/play/wwdc2022/10035/?time=1229)
- [Cartography Guide, contrast](https://amyleew.gitbooks.io/cartography-guide/content/design-best-pratices/design-principles/contrast.html)
- [Esri, accessibility essentials for mapping](https://www.esri.com/arcgis-blog/products/instant-apps/mapping/accessibility-essentials-for-gis-and-mapping)
- [AOPA, follow the magenta line](https://www.aopa.org/news-and-media/all-news/2012/august/flight-training-magazine/follow-the-magenta-line)
- [Okabe-Ito hex codes](https://scifig.ai/blog/okabe-ito-color-palette-hex-codes)
- [Stepper states: done, current, upcoming](https://www.stellae.design/en/components/stepper)

---

# 8. Friendly, not sharp — **shipped 2026-09-27**

The founder: not fun, not friendly, colours that do not match, buttons too
sharp. A screenshot agreed: 4px black rectangles with spaced uppercase mono,
and teal pins, a blue line, an ochre ring and black buttons on one screen.
Part 5 was right that the look needed decisions; the decisions it made read as
an instrument, and "cream paper, serif, uppercase mono" is itself on the lists
of editorial tells now.

## What the research said

- **Shape.** iOS 26 buttons are capsules by default and nested corners are
  concentric (parent radius minus padding); one or two prominent buttons per
  view, told apart by style rather than size. Airbnb, Duolingo, Headspace and
  Komoot run 12px to full capsule on buttons and 16-28 on cards; none of them
  uses 4. The curvature preference is real but modest (meta-analysis g = .39,
  weaker in East Asian samples), and round marks read warm where angular ones
  read competent and hard.
- **Colour.** Pleasure tracks brightness far more than hue, and black rates
  as the most "overbearing" colour: the case against a black primary button.
  One saturated accent over a muted map is the cartography rule.
- **Ember beside the old ochre failed colour blindness.** Simulated
  protanopia put `#B83A12` and `#8A5A17` 4.9 ΔE apart at a 1.03 luminance
  ratio: one colour. Warm-on-warm works only if the two differ in lightness,
  so `seal` became a bright gold (35+ ΔE from ember under both deuteranopia and
  protanopia). Gold is too light for text or a paper edge, hence `sealInk` on
  it and `sealDeep` for gold words on paper.
- **Glass** belongs to the navigation layer floating over content, never on
  content and never on glass; tint only the one prominent control. Apple Maps
  is Apple's own example. The system handles Reduce Transparency and Increase
  Contrast.
- **Type.** 17pt semibold sentence-case button labels (HIG Headline), an 11pt
  floor. Friendly apps run on one warm UI family. Fraunces has a SOFT axis
  that rounds its terminals toward Cooper and Recoleta.

## What shipped

`ember` for a memory and the way there, gold `seal` for openable, `faded` for
done, and blue left to the map. Capsule buttons (52pt, ember or a soft ember
tint), 28 on cards over the map, 14 on fields. Soft Fraunces for stories,
Figtree for everything you read to use the app. `src/Glass.tsx` on the map
controls, paper and one shadow without it. Presses give a little (scale 0.97)
instead of dimming. The hop was already hand-tuned squash and stretch, and
stayed.

## Cutting the soft Fraunces

Superseded 2026-09-27: the app is set in SF Pro Rounded and the Fraunces files
are gone ("One font, the map's" in `docs/10-decisions.md`). The recipe stays in
case a serif comes back.

`@expo-google-fonts/fraunces` ships only weights, and React Native cannot set
a variation axis, so the three statics in `mobile/assets/fonts/` are cut from
the Google Fonts variable file with fonttools, with unique names so iOS does
not merge them:

```python
from fontTools.ttLib import TTFont
from fontTools.varLib.instancer import instantiateVariableFont
# Fraunces[SOFT,WONK,opsz,wght].ttf from github.com/google/fonts/ofl/fraunces
instantiateVariableFont(TTFont(src), dict(wght=700, opsz=36, SOFT=100, WONK=1))  # Bold
# SemiBold: wght=600, opsz=36, WONK=1.  Regular: wght=400, opsz=18, WONK=0.
# Then set name IDs 1, 4 and 6 to FrauncesSoft-<Weight> before saving.
```

## Not done, and when

- Static-image markers: when the pin count makes the map stutter.
- A signature object (Airbnb's 3D icons, Duolingo's lip): once this has been
  lived with.
- Springs on every press: if the instant scale feels cheap on a device.

## Sources

- [WWDC25 356, Get to know the new design system](https://developer.apple.com/videos/play/wwdc2025/356/) — capsule, fixed and concentric shapes
- [WWDC25 219, Meet Liquid Glass](https://developer.apple.com/videos/play/wwdc2025/219/) — navigation layer only, tint only what matters
- [HIG, Buttons](https://developer.apple.com/design/human-interface-guidelines/buttons) and [Typography](https://developer.apple.com/design/human-interface-guidelines/typography)
- [expo-glass-effect](https://docs.expo.dev/versions/latest/sdk/glass-effect/) — the opacity trap
- [Google, Expressive design research](https://design.google/library/expressive-material-design-google-research) — 46 studies, "playful" and "friendly" scores (Google's own, not peer-reviewed)
- [Chuquichambi et al. 2022](https://nyaspubs.onlinelibrary.wiley.com/doi/10.1111/nyas.14919) — curvature preference meta-analysis
- [Jiang et al. 2016](https://www.semanticscholar.org/paper/Does-Your-Company-Have-the-Right-Logo-How-and-Why-Jiang-Gorn/9cb1bc27782f497d1f0c5d201576cb8d96756aff) — round reads warm, angular reads hard
- [Valdez & Mehrabian 1994](https://www.semanticscholar.org/paper/Effects-of-color-on-emotions.-Valdez-Mehrabian/d15bdf485f3a64abb59e4d0d1d1b18a9fc652bf9) — brightness drives pleasure, black is overbearing
- [Duolingo illustration guidelines](https://design.duolingo.com/illustration) — "pointy shapes are off-brand"
- [It's Nice That on Airbnb 2025](https://www.itsnicethat.com/articles/airbnb-app-redesign-140525) — "fun, alive, and simple", more curved edges
- [Google Design, Fraunces](https://design.google/library/a-new-take-on-old-style-typeface) — the SOFT and WONK axes
- [NN/g, Liquid Glass](https://www.nngroup.com/articles/liquid-glass/) — glass over busy content loses contrast

---

# 9. Steps as currency, and the iOS 26 facelift — **researched 2026-10-01, first part shipped**

Once three a day opened from anywhere and the rest cost 1,000 steps (docs/10,
*Three free a day, then steps where you stand*), the pill at the top said
"4,000 steps / 0 free today" and nothing about what that bought. A person
short of steps still got a gold pin and a holdable ring, and only after the
900 ms hold learned they could not pay: seal said openable and was wrong (F11).
Three parallel passes: the step-currency apps, the iOS 26 / Expo 57 stack, and
an audit of our own screens against `mobile/UI.md`.

## What the step apps do

- **Pikmin Bloom** publishes a fixed cost on every seedling (100 to 10,000
  steps) and petals spent on a Big Flower you have to walk to, at a flat
  published price. The closest analogue to paying where you stand. Niantic's
  line: it should "fit in rather than compete for attention".
- **Pokémon GO** puts the km cost on every egg before you commit, and shows
  progress outside the app (widget, "nearly hatched" pushes).
- **Sweatcoin** converts automatically at a published rate and keeps what did
  not convert: nothing is lost for not opening the app.
- **WeWard** makes you tap "Validate my steps" before midnight or lose them.
  A daily ritual, and a chore with loss aversion attached. **Rejected.**
- **Duolingo** replaced Hearts with Energy because running out was "especially
  frustrating for beginners"; slack (streak freezes) raised retention. A
  refusal should be kind and point somewhere.
- **Game-economy practice**: earned currency should visibly arrive, the exact
  amount, never more than was earned.
- **Apple**: Activity rings are for Move, Exercise and Stand only; never draw
  a look-alike. Haptics consistent, paired with a visual, success for success.

## The stack, as of Expo 57

| | Verdict |
|---|---|
| `@expo/ui` (SwiftUI in RN, late beta) | **Adopted.** `Text` + `contentTransition('numericText')` is the system's own odometer for the balance. `GlassEffectContainer` and `glassEffectId` morphing are there for later |
| `expo-symbols` (beta) | **Adopt next** (TODO § Facelift F3): SF Symbols for the seven hand-drawn SVG glyphs, bounce on unlock. The pin stays SVG |
| `GlassContainer` in the installed `expo-glass-effect` | **Dropped** 2026-10-01: adopted in F2 round You and Add, and the founder disliked the merged shape. It also swallows taps in its gaps. Spacing 40 merged an 8pt gap; 12 did nothing visible |
| RN 0.86 `boxShadow`, `backgroundImage` gradients | Use where an SVG or image is only a shadow or gradient |
| Reanimated 4 | **Skipped.** Two native deps and a second animation model for what core `Animated` plus one SwiftUI `Text` already do |
| Live Activities | **Skipped.** A balance is not a bounded, time-limited event. A Lock Screen widget (`expo-widgets`) is sensible after launch (F8) |

## What shipped first: the wallet

- **The pill says the one thing to know.** Free ones left: "2 free today",
  the balance under it. None free and enough: "4,210 steps / Opens 4". Short:
  a small ember ring filling toward the price and "600 to go / 400 steps". A
  ring and not a bar so it is the same object as the hold, one ring meaning one
  thing; one ring and ember, never three nested ones, so it is not Activity's.
  `src/wallet.ts` decides, and is unit-tested.
- **The big line rolls** (SwiftUI `numericText`), so spending and earning are
  seen, and a sync that lands 100+ steps is felt (one Light tap). No
  tap-to-collect, no coins flying.
- **Short means not openable.** The pin stays ember, the "into range" tap does
  not fire, and the card on the map shows the full, faded Approach ring with
  "600 steps to go · about 6 min walking" (100 steps a minute) and **Skip the
  steps**, which is the paywall. The server's 403 stays as the backstop.

## Not done, and when

TODO.md § Facelift, in order: glass by the HIG (F2), SF Symbols (F3), one of
each pill, card and figure (F4), paying along the hold (F5), the free open as
an earn (F6), the words in You (F7), a Lock Screen widget (F8).

## Sources

- [Pikmin Bloom, how to play](https://niantic.helpshift.com/hc/en/23-pikmin-bloom/faq/2854-how-to-play-pikmin-bloom/) and [Big Flowers](https://niantic.helpshift.com/hc/en/23-pikmin-bloom/faq/4878-use-the-flower-petals-to-make-a-big-flower-bloom/)
- [Pokémon GO, eggs](https://niantic.helpshift.com/hc/en/6-pokemon-go/faq/2358-incubators-hatching-pokemon-eggs/) and [widgets](https://niantic.helpshift.com/hc/en/6-pokemon-go/faq/3405-how-to-add-pokemon-go-widgets-to-your-device-home-screen/)
- [Sweatcoin, conversion](https://help.sweatco.in/hc/en-us/articles/360012673992)
- [WeWard, validating steps](https://faq.weward.fr/hc/en-us/articles/28122448171794)
- [Duolingo, Energy](https://blog.duolingo.com/duolingo-energy/) and [the streak](https://blog.duolingo.com/how-duolingo-streak-builds-habit/)
- [Game Economist Consulting, currency animations](https://www.gameeconomistconsulting.com/the-best-currency-animations-of-all-time/)
- [HIG, Activity rings](https://developer.apple.com/design/human-interface-guidelines/activity-rings) and [Playing haptics](https://developer.apple.com/design/human-interface-guidelines/playing-haptics)
- [Expo UI](https://docs.expo.dev/versions/latest/sdk/ui/), [modifiers](https://docs.expo.dev/versions/latest/sdk/ui/swift-ui/modifiers/), [expo-symbols](https://docs.expo.dev/versions/latest/sdk/symbols/), [expo-widgets](https://docs.expo.dev/versions/latest/sdk/widgets/)
- [WWDC25 219, Meet Liquid Glass](https://developer.apple.com/videos/play/wwdc2025/219/); [Adopting Liquid Glass](https://developer.apple.com/documentation/TechnologyOverviews/adopting-liquid-glass)
- [RN view style props](https://reactnative.dev/docs/view-style-props)

---

# 10. The walk, the heart and the credit — **researched 2026-10-01, not built**

The founder, on the simulator: the top "On a walk · 1 of 7" pill and the
bottom "7.9 km to go" pill don't say what they mean, and there's no recenter.
The heart jumps when "1 heart" appears. Nobody knows what "Open the source"
opens, and "From" belongs higher up. The research below is from primary sources
where a fetch worked. Where it didn't, the text says so. The TODO entries are
in TODO.md under *Facelift*, F9 to F12.

## One walk element

The common pattern is one element that says what's next and how far it is,
with progress as a secondary count. End is never what a plain tap on it does.

- **Google's Navigation SDK** has a header for the next step and a footer for
  ETA and distance left. End is a separate control in the footer.
- **Apple Maps walking** has one bottom card. A swipe up reveals a red End
  Route button. This is from the app, not from a document.
- **VoiceMap** shows the next spot with an "I am here" button, and ending the
  tour is its own small route-with-✕ control.
- **HIG, Live Activities:** show what people need at a glance, and make cancel
  an explicit control.

**For us:**
- Replace both pills with one bottom card.
- **Main line:** "Next: \<place\> · 300 m".
- **Second line:** "2 of 7 · 4.1 km left", or seven dots that fill as stops
  unlock.
- **Tap:** fits the route.
- **End:** a small ✕ on the card's trailing edge, with a confirm.
- **On arrival:** "You're at \<place\> · Open story".
- The same content becomes the Live Activity later.

## Recenter

- **Google's Navigation SDK:** "The recenter button appears when the user
  scrolls the map view, and disappears when the user taps to re-center the
  map."
- **`MKUserTrackingButton`:** cycles none → follow → follow with heading. The
  outline, filled and cone icons are from memory, not the fetched doc.
- **Placement:** Apple puts it in the top-right control stack, Google at the
  bottom right above the sheet.
- **react-native-maps:** `showsMyLocationButton` is Android-only, so iOS needs
  a custom button that calls `animateCamera`.

**For us:**
- One location-arrow button, at the bottom right above the walk card.
- **On a walk:** a pan breaks follow instead of being refused. The pinned
  camera in `App.tsx` turns scroll off today. The button shows until a tap
  recenters, which also retires `NextStopArrow`'s "can't drag to look"
  workaround.
- **Off a walk:** it shows whenever the map is off-centre.
- **Heading mode:** skip it until somebody asks for it.

## A heart that does not move

The cause is in `MemorySheet.tsx`. The count text is appended after the glyph
in a row whose sibling `creditText` has `flex: 1`. So the glyph moves left,
and a long credit can rewrap.

- **Bluesky** (React Native, `src/components/PostControls/index.tsx`): each
  control owns a fixed slot, and the glyph is pinned to its leading edge. The
  count is hidden at 0.
- `src/lib/custom-animations/CountWheel.tsx` rolls the number in by
  translateY with a fade over 400 ms. It only does this after a real tap and
  skips it under reduced motion. The label carries the count: "Like (1 like)".
- **X, Threads and Instagram:** the count is a bare number in a fixed slot.
- **Airbnb, Apple Music:** no count at all, only a filled or outline glyph
  and a bounce.
- **HIG:** a toggle shows its state through the glyph, and VoiceOver gets a
  `selected` state, not the state written into the label.

**For us:**
- Show a bare number, not "1 heart", placed *before* the glyph, so the glyph
  stays at the edge.
- Give the number a reserved `minWidth` of about two `tabular-nums` digits,
  with opacity 0 at zero hearts.
- Keep the existing bounce. Add a small roll or fade (about 250 ms, skipped
  under reduce motion).
- The label is "Heart", with `accessibilityState.selected` and the count as
  `accessibilityValue`.
- The owner's read-only variant matches.

## Say where the button goes, and credit at the top

- **NN/g on [information scent](https://www.nngroup.com/articles/information-scent/):**
  a link says where it takes you. "Source" is a researcher's word, and no
  consumer product found uses it as a button.
- **Name the host or the thing:**
  - YouTube: "Watch on YouTube".
  - [Europeana](https://leuven2012.europeana.eu/page/edm-mooc-advanced): "View at \<institution\>".
  - [Google Arts & Culture](https://support.google.com/culturalinstitute/partners/answer/4386229): "Visit \<collection\>'s website".
  - [Readwise](https://help.readwise.io/article/40-can-i-jump-to-a-highlight-directly-in-the-kindle-app): "View in Kindle".
- **Credit goes at the top:**
  - [Apple News](https://support.apple.com/guide/news-publisher/apd7c9ae979c/icloud)
    shows the publisher's logo on every article.
  - [NN/g, bylines](https://www.nngroup.com/articles/bylines-for-web-articles/)
    puts the byline under the headline.
  - The peek card already shows "From X" under the place name. Only the open
    card puts it at the bottom.
- **[AI Act Art 50(4)](https://artificialintelligenceact.eu/transparency-rules-article-50/):**
  the label must be there "at the latest at first exposure". Small print at
  the bottom is the example given of what fails.

**For us:**
- **Byline:** goes in the fixed heading under the place name: "Retold from
  **\<source\>**" or "Left by **\<name\>**", with the episode or book title on
  a faint second line. "Retold from" doubles as the AI label, but check it on
  screenshots first.
- **Pinned at the bottom:** only the heart and the action.
- **Screenshots:** a screenshot still keeps the place and the credit together,
  which is what UI.md rule 11 and docs/10 *Core, not polish* ask for.
- **Metadata:** the story stops ending on metadata (*The open story has a
  shape*).
- **Superseded:** rule 11 and the docs/10 entry get a new wording, with the
  old one marked Superseded. The server-rendered card takes the same order.

| Kind | Button |
|---|---|
| Video, with offset | Watch from 12:04 |
| Video, no offset | Watch on YouTube |
| Book | Read it in the book |
| Newspaper | Read the 1856 article |
| Archive | Read it at \<host\>, e.g. Historisk Atlas |
| Unknown | Read the original |
| Filed by a person | none |

This needs a `kind` on the content payload. `ContentRef` has no
`source_type`, and `pipeline/ingest.py` stores every text source as
`archive`, so a book and a newspaper can't be told apart yet. Also a bug:
`SourceLine.tsx` says "on YouTube" to VoiceOver for books too.

## Sources

- [Google Navigation SDK, controls](https://developers.google.com/maps/documentation/navigation/ios-sdk/controls)
- [HIG, Live Activities](https://developer.apple.com/design/human-interface-guidelines/live-activities), [Maps](https://developer.apple.com/design/human-interface-guidelines/maps), [Toggles](https://developer.apple.com/design/human-interface-guidelines/toggles), [Buttons](https://developer.apple.com/design/human-interface-guidelines/buttons)
- [MKUserTrackingButton](https://developer.apple.com/documentation/mapkit/mkusertrackingbutton)
- [Apple Maps walking directions](https://support.apple.com/guide/iphone/get-walking-directions-iph8eae299d1/ios)
- [VoiceMap 10](https://blog.voicemap.me/2023/05/voicemap-athens-new-version-10-the-best-audio-tour-app/), [stopping a tour](https://support.voicemap.me/can-i-stop-and-resume-my-tour/)
- [Citymapper Lock Screen navigation](https://content.citymapper.com/i/2553/citymapper-introduces-ios-lock-screen-navigation)
- Bluesky [PostControls](https://github.com/bluesky-social/social-app/blob/main/src/components/PostControls/index.tsx), [CountWheel](https://github.com/bluesky-social/social-app/blob/main/src/lib/custom-animations/CountWheel.tsx)
- [SwiftUI numericText](https://developer.apple.com/documentation/swiftui/contenttransition/numerictext(countsdown:))
- [ChatGPT search citations teardown](https://www.aiuxplayground.com/teardowns/chatgpt/citations)
