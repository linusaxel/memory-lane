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

**And then the rest of it went too** — see part 5. Glassmorphism turns up on
every list of tells for a generated interface, and having fought it to 82% white
to keep it readable, what was left was a translucent white pill: the cost of the
dependency without the effect. `Glass.tsx` is deleted. The two findings above
survive it, because the next person will reach for `expo-blur` anyway.

## 3. Depth — **kept only where something really floats**

Soft large-radius shadows read as floating; tight dark ones read as stickers.
That still holds for the two things that genuinely hover over the map — the
"Near me" button and the location primer.

Everywhere else the shadows came off in part 5. Stacked floating cards are the
card-grid tell, and editorial layouts have always used rules and weight instead.

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
  stamp red (`TODO.md`'s founder-brainstorm "warm accent, not a reskin";
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
the only distribution channel the product has, and TODO.md already calls
screenshot-native cards core rather than polish. The card is also where the
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
