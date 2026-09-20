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

## 2. Glass chrome — **kept, but heavily tuned**

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
(rule 7 in UI.md). Solid is correct there.

## 3. Depth — **kept, cheaply**

Soft large-radius shadows read as floating; tight dark ones read as stickers.
Every floating element moved from roughly `radius 8–10 / opacity 0.2 / y 2–3` to
`radius 14–18 / opacity 0.1–0.22 / y 5–8`. No new dependency, no new component,
about a dozen changed numbers.

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
