/** Every colour and typeface in the app. Never write a hex or a font name
 *  anywhere else. Why these ones: docs/09-visual-design.md.
 *
 *  `DynamicColorIOS` is why this is one file and not eleven - the platform
 *  resolves the pair at draw time, so `StyleSheet.create` at module scope keeps
 *  working and appearance changes repaint with no hook and no context. It is
 *  iOS-only: Android takes the light value until somebody does the theme-context
 *  refactor. A real gap, logged in mobile/UI.md.
 */

import {
  DynamicColorIOS,
  Platform,
  type PressableStateCallbackType,
  type StyleProp,
  type ViewStyle,
} from 'react-native';

/** Light and dark, resolved by the platform. Android gets the light value. */
const dual = (light: string, dark: string) =>
  Platform.OS === 'ios' ? DynamicColorIOS({ light, dark }) : light;

export const color = {
  /** Warm paper. Not #fff, and not a zinc - it sits close to the muted Apple
   *  map underneath so the sheets feel cut from the same stock. */
  paper: dual('#F7F4EE', '#161412'),
  /** One step up for surfaces that need to lift off the paper. */
  paperRaised: dual('#FFFDF9', '#201D19'),
  ink: dual('#1C1917', '#F2EDE4'),
  inkSoft: dual('#4A443D', '#BDB5A8'),
  /** Labels and captions, and so the colour the 9-11px label voice is set in.
   *  Both values moved for contrast: #8A837A was 3.4:1 on paper, and #8A8276
   *  was 4.8:1 on paper but only 4.4:1 on paperRaised, which is where inputs
   *  and the audio row put it. 4.7:1 and 4.8:1 now, on both grounds.
   *  tests/test_palette.py holds every pair to 4.5:1 in both themes. */
  inkFaint: dual('#746D65', '#908979'),
  /** Hairlines and dividers. Editorial layouts rule; they do not shadow. */
  rule: dual('#E0D9CC', '#332E27'),

  /** A memory, and the way to it: the walk's line, the next stop, the one
   *  primary button, a link. Old gold, dark enough to be text on paper; the
   *  lockets carry the bright metal. docs/09-visual-design.md. */
  gold: dual('#86661A', '#D9B45E'),
  /** The quiet button's fill: ink, washed thin, so it sits on glass or paper
   *  alike (docs/09 part 13). */
  wash: dual('rgba(28,25,23,0.07)', 'rgba(242,237,228,0.12)'),
  /** A subscriber's thing, offered to a free walker: gold, washed thin. */
  goldTint: dual('rgba(134,102,26,0.14)', 'rgba(217,180,94,0.18)'),

  /** Openable now, and nothing else: the in-reach halo, the reach circle, the
   *  unlock ring. Emerald, because gold beside gold is no signal. A fill: text
   *  and marks on it are sealInk, and emerald text on paper is sealDeep. */
  seal: dual('#1F6B4F', '#3FA57E'),
  /** Anything drawn on seal: a lit pin's tag, the pill's words. */
  sealInk: dual('#F7F4EE', '#0B1F17'),
  /** The ring filling during a hold. */
  sealSoft: dual('#D5EBDF', '#173528'),
  /** Seal as text or a thin mark on paper. */
  sealDeep: dual('#16573F', '#7FD1AE'),

  /** The rich purple detail: your level, your streak, your row on the board. Things you earned, never a memory or an action. */
  purple: dual('#5B2A6E', '#C59BD8'),

  /** Out of reach: a far thing, faded. Dark enough to hold against the
   *  parchment map, and lighter in the dark where a dark mark vanishes. */
  faded: dual('#776E64', '#9A9086'),

  /** The wash behind a reachable pin, so it is findable before its shape is.
   *  Deliberately not a pair: it is a translucent seal over a map, and one
   *  alpha reads about the same over either. It lives here rather than inline
   *  so a palette change reaches it. */
  halo: 'rgba(63,165,126,0.35)',

  /** The slide track's knob: white in both themes, as iOS draws it. */
  knob: '#FFFFFF',

  /** `lift`'s shadow, and the scrim over an uploading photo. */
  shadow: '#000',
  scrim: 'rgba(0,0,0,0.35)',
};

/** The lockets' metal, for the unlock's Svg (LocketUnlock.tsx). One set in
 *  both themes: it is gold, not a surface. */
export const metal = {
  hi: '#FFF1C1',
  light: '#F2D58A',
  mid: '#D4AF5A',
  deep: '#A8822E',
  dark: '#6E5216',
  engrave: '#8A6A22',
  well: '#3B2C0C',
  inner: '#E8C77A',
  rim: '#C9A24A',
  /** The night locket's enamel. */
  night: '#211D18',
  garnet: '#8F1D1D',
  garnetHi: '#D9524A',
  /** The inside of an open locket, and the glow it gives off. */
  glow: '#FFFDF9',
  /** The compass's N. */
  north: '#8F2F1B',
};

/** Real colours, for the few props that cannot take a DynamicColorIOS value:
 *  map overlays, Svg fills, the splash. Pick with `useColorScheme()`. Where a
 *  name is also in `color`, the values are the same pair. */
export const solid = (dark: boolean) => ({
  paper: dark ? '#161412' : '#F7F4EE',
  ink: dark ? '#F2EDE4' : '#1C1917',
  rule: dark ? '#332E27' : '#E0D9CC',
  gold: dark ? '#D9B45E' : '#86661A',
  purple: dark ? '#C59BD8' : '#5B2A6E',
  seal: dark ? '#3FA57E' : '#1F6B4F',
  /** The darker edge Apple Maps draws round a route. */
  goldCasing: dark ? '#6E5216' : '#5E470F',
  /** The preview's line: gold washed out, so the lockets on it pop. */
  line: dark ? '#8A7238' : '#E3CF98',
  lineCasing: dark ? '#5E4C22' : '#C9AE68',
  /** The reach circle: the seal, washed over the map. */
  reachStroke: dark ? 'rgba(63,165,126,0.75)' : 'rgba(31,107,79,0.7)',
  reachFill: dark ? 'rgba(63,165,126,0.12)' : 'rgba(31,107,79,0.12)',
  /** mobile/assets/icon.svg and icon-dark.svg. */
  tile: dark ? '#5e2a18' : '#a8350f',
  road: dark ? '#f2ede4' : '#f7f4ee',
  sun: dark ? '#f5c542' : '#f2b53a',
  /** The glass over the map, warmed: paper in light, a dark gold in dark,
   *  thin enough that the map still shows through. A tint, so a real colour. */
  frost: dark ? 'rgba(53,42,20,0.35)' : 'rgba(241,228,194,0.45)',
  /** The same warmth on a glass card, thicker: a card carries prose, which
   *  must hold its contrast over a busy map. */
  frostCard: dark ? 'rgba(32,29,25,0.72)' : 'rgba(255,253,249,0.72)',
});

/** One family, SF Pro Rounded: the system's own, so it sits with the map's
 *  labels, and rounded, so it is friendly. Android has no rounded cut and
 *  falls back to Roboto, which is the map's there. Each token is a style you
 *  spread (`...font.display`), so a family or weight changes here alone. */
export const font = {
  display: { fontFamily: 'ui-rounded', fontWeight: '700' },
  displaySemi: { fontFamily: 'ui-rounded', fontWeight: '600' },
  prose: { fontFamily: 'ui-rounded', fontWeight: '400' },
  ui: { fontFamily: 'ui-rounded', fontWeight: '400' },
  uiMedium: { fontFamily: 'ui-rounded', fontWeight: '500' },
  uiBold: { fontFamily: 'ui-rounded', fontWeight: '600' },
} as const;

/** The only corners: a field, a card over the map, and a capsule for anything
 *  you press. Circles are half their side and need no token. */
export const radius = { field: 14, card: 28, pill: 999 };

/** The shadow for paper that floats over the map. The hold ring's seal glow
 *  is the only other (UI.md, "Spacing, radii and the two shadows"). */
export const lift = {
  shadowColor: color.shadow,
  shadowOffset: { width: 0, height: 4 },
  shadowRadius: 16,
  shadowOpacity: 0.12,
  elevation: 4,
};

/** A card over the map: the unlock card, Plan's, the peek. Where it sits and
 *  its padding are the caller's. */
export const floating = {
  backgroundColor: color.paperRaised,
  borderRadius: radius.card,
  ...lift,
};

/** A glass control over the map: Journal, the steps pill, the walk bar. */
export const pill = {
  minHeight: 44,
  paddingHorizontal: 16,
  borderRadius: radius.pill,
  flexDirection: 'row' as const,
  alignItems: 'center' as const,
  justifyContent: 'center' as const,
  gap: 8,
};

/** The number a screen is about: the distance to a pin, a streak, a stat. The
 *  peek's distance is the small one, under the place it belongs to. */
export const figure = { ...font.display, fontSize: 52, color: color.ink, letterSpacing: -1 };
export const figureSmall = {
  ...font.display,
  fontSize: 36,
  lineHeight: 42,
  color: color.ink,
  letterSpacing: -0.5,
};

/** The app's label voice, wherever a screen names a thing rather than says
 *  something. */
export const label = {
  ...font.uiBold,
  fontSize: 13,
  color: color.inkFaint,
};

/** A memory's own type, read and written alike: Add a memory's fields are the
 *  open sheet's text with nothing in it yet, so the two cannot drift. Three
 *  sizes and nothing else (docs/10, "Reading and writing are one page"). */
export const story = {
  title: { ...font.display, fontSize: 28, lineHeight: 34, color: color.ink },
  body: { ...font.prose, fontSize: 17, lineHeight: 26, color: color.ink },
  meta: label,
};

/** The text inside a button. Pair with `color.paper` on gold, `color.ink`
 *  on the quiet and outlined ones. */
export const buttonText = {
  ...font.uiBold,
  fontSize: 17,
};
export const buttonTextSmall = { ...font.uiBold, fontSize: 15 };

/** The app's buttons: three flat capsules, two sizes. Spread one and add only where
 *  it sits (margin, alignSelf); the text is `buttonText`. An action inside the
 *  page rather than ending it (Leave note, Edit this memory) spreads `small`
 *  after the capsule, with `buttonTextSmall` and `hitSlop={4}` to reach 44pt.
 *  A link to somewhere else (Terms, a credit) stays a link. */
const buttonBox = {
  borderWidth: 1.5,
  borderColor: 'transparent',
  borderRadius: radius.pill,
  minHeight: 52,
  paddingVertical: 12,
  paddingHorizontal: 24,
  alignItems: 'center' as const,
  justifyContent: 'center' as const,
};
export const button = {
  /** The one thing to do. Text in paper. */
  solid: { ...buttonBox, backgroundColor: color.gold },
  /** The way back, next to a solid one. Text in ink. */
  quiet: { ...buttonBox, backgroundColor: color.wash },
  /** An action standing on its own. Text in ink. */
  outline: { ...buttonBox, borderColor: color.rule },
  small: { minHeight: 36, paddingVertical: 6, paddingHorizontal: 16 },
};

/** A text field. The display-name input renders twice - You and Submit - and
 *  they must not drift. */
export const input = {
  borderWidth: 1,
  borderColor: color.rule,
  borderRadius: radius.field,
  paddingHorizontal: 14,
  paddingVertical: 12,
  ...font.prose,
  fontSize: 17,
  color: color.ink,
  backgroundColor: color.paperRaised,
};

/** How a pressed thing gives: a little smaller, a little fainter. Glass
 *  scales on its own (src/Glass.tsx). */
export const sunk: ViewStyle = { opacity: 0.85, transform: [{ scale: 0.97 }] };

/** Every Pressable in the app gives a little while it is held.
 *
 *  It is one helper rather than a `pressed &&` in twenty-eight StyleSheets for
 *  the same reason `label` is one object: the value drifts the moment it is
 *  copied. Use it as `style={dim(styles.thing)}`.
 *
 *  Two things deliberately do not use it. A marker never changes outside its
 *  four states - `tracksViewChanges` is off and animating a marker's children
 *  flickers in react-native-maps. And the unlock ring's fill *is* its press
 *  feedback; dimming it would fight the one thing it exists to show.
 */
export const dim =
  (base?: StyleProp<ViewStyle>) =>
  ({ pressed }: PressableStateCallbackType): StyleProp<ViewStyle> => [base, pressed && sunk];
