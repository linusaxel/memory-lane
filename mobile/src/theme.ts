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
  /** Warm cream, and dusk-black in the dark (docs/10-decisions.md, "Dusk"). */
  paper: dual('#F6EEDF', '#1C1A20'),
  /** One step up for surfaces that need to lift off the paper. */
  paperRaised: dual('#FCF7EE', '#26232B'),
  ink: dual('#2E2A31', '#F1E9DC'),
  inkSoft: dual('#4D4852', '#C9C2CC'),
  /** Labels and captions. tests/test_palette.py holds every pair to 4.5:1
   *  in both themes, on paper and on paperRaised. */
  inkFaint: dual('#68626D', '#9C96A2'),
  /** Hairlines and dividers. Editorial layouts rule; they do not shadow. */
  rule: dual('#E3D9C8', '#38343E'),
  /** The quiet button's fill, and a close button's. */
  quiet: dual('#EEE5D5', '#2E2B34'),
  /** A quiet button's edge: none on cream, a cream hairline in the dark. */
  quietEdge: dual('rgba(0,0,0,0)', 'rgba(246,222,184,0.3)'),

  /** A memory, and the way to it: links, text buttons, the walk's line. */
  gold: dual('#7A5A2E', '#D9B98A'),
  /** A gold hairline: glass over the map, quiet buttons in the dark. */
  goldLine: dual('rgba(122,90,46,0.45)', 'rgba(217,185,138,0.5)'),

  /** Go: Plan a walk, Start walk, Next, the slide track. Text on it is onGo. */
  goBg: dual('#443E46', '#4C454F'),
  goRim: dual('rgba(246,222,184,0.5)', 'rgba(246,222,184,0.45)'),
  onGo: dual('#FBF6EC', '#FBF6EC'),
  /** A raised button's ledge: the darker 4pt under go. */
  goLedge: dual('#2E2A31', '#2A262D'),

  /** Openable now, and nothing else: a lit pin, the diamond in the rule. A
   *  fill and a text colour both; marks drawn on it are sealInk. */
  seal: dual('#A8403F', '#F28A82'),
  sealInk: dual('#FBF6EC', '#2A1213'),
  sealSoft: dual('#F6DCD8', '#3D2224'),
  /** The glow behind an in-reach locket. Never a ring. */
  glow: dual('rgba(168,64,63,0.5)', 'rgba(242,138,130,0.5)'),

  /** Velvet, and words on it: the Collector's colours, cloth, so one set in
   *  both themes (docs/10, "Game menus"). The ground is velvet.mid. */
  velvetGround: dual('#443E46', '#443E46'),
  onVelvet: dual('#F6F1E7', '#F6F1E7'),
  onVelvetSoft: dual('#E4DFE8', '#E4DFE8'),
  onVelvetGold: dual('#F6DEB8', '#F6DEB8'),

  /** What you earned: lockets, and the bar to your next rank.
   *  Never a memory or an action. */
  plum: dual('#6E6890', '#B8B3D1'),
  /** The empty part of the rank bar. */
  track: dual('#E6E3EE', '#38343E'),

  /** Delete account, and nothing else gold-free and final. */
  danger: dual('#9B2C2C', '#F09A9A'),
  heart: dual('#A3294E', '#F29BB4'),

  /** Out of reach: a far thing, faded. */
  faded: dual('#68626D', '#9C96A2'),

  /** The wash behind a reachable pin, so it is findable before its shape is.
   *  One alpha reads about the same over either map. */
  halo: 'rgba(242,138,130,0.35)',

  /** The hairline round a glass control, so it holds an edge on the map. */
  edge: dual('rgba(46,42,49,0.14)', 'rgba(246,222,184,0.3)'),

  /** `lift`'s shadow, and the scrim over an uploading photo. */
  shadow: '#000',
  scrim: 'rgba(0,0,0,0.35)',
};

/** Foil, flat cream (docs/10, "Dusk"): Seal it here, Subscribe, Done.
 *  One set in both themes. */
export const foil = {
  colors: ['#F6DEB8', '#EDD2A6', '#E3C796'] as const,
  highlight: 'rgba(246,222,184,0.6)',
  ring: 'rgba(46,42,49,0.35)',
  text: '#2E2A31',
};

/** The lockets' metal, for the unlock's Svg (lockets/). One set in both
 *  themes: it is gold, not a surface. */
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
  /** What is engraved inside, and the night locket's. */
  ink: '#1C1917',
  faded: '#776E64',
  nightText: '#F2EDE4',
  nightFaded: '#9A9086',
  /** The compass's needle tip and the sweetheart's small heart. */
  red: '#C0462B',
};

/** Velvet, flat charcoal-plum: the paywall's and the Collector's cloth. One
 *  set in both themes. */
export const velvet = { hi: '#4C454F', mid: '#443E46', deep: '#3B363D' };

/** Real colours, for the few props that cannot take a DynamicColorIOS value:
 *  map overlays, Svg fills, the splash. Pick with `useColorScheme()`. Where a
 *  name is also in `color`, the values are the same pair. */
export const solid = (dark: boolean) => ({
  paper: dark ? '#1C1A20' : '#F6EEDF',
  ink: dark ? '#F1E9DC' : '#2E2A31',
  rule: dark ? '#38343E' : '#E3D9C8',
  gold: dark ? '#D9B98A' : '#7A5A2E',
  plum: dark ? '#B8B3D1' : '#6E6890',
  track: dark ? '#38343E' : '#E6E3EE',
  seal: dark ? '#F28A82' : '#A8403F',
  /** color.glow, for Svg, which cannot take a dynamic colour. */
  glow: dark ? 'rgba(242,138,130,0.5)' : 'rgba(168,64,63,0.5)',
  /** The darker edge Apple Maps draws round a route. */
  goldCasing: dark ? '#6E5216' : '#5E470F',
  /** The preview's line: gold washed out, so the lockets on it pop. */
  line: dark ? '#8A7238' : '#E3CF98',
  lineCasing: dark ? '#5E4C22' : '#C9AE68',
  /** The reach circle: the seal, washed over the map. */
  reachStroke: dark ? 'rgba(242,138,130,0.75)' : 'rgba(168,64,63,0.7)',
  reachFill: dark ? 'rgba(242,138,130,0.12)' : 'rgba(168,64,63,0.12)',
  /** The one tinted control over the map, Plan a walk: charcoal enamel glass,
   *  dense, because a light tint on the cream map measured 1.01:1
   *  (docs/09 part 15). A tint, so a real colour. */
  goGlass: dark ? 'rgba(76,69,79,0.94)' : 'rgba(68,62,70,0.94)',
  /** The same warmth on a glass card, thicker: a card carries prose, which
   *  must hold its contrast over a busy map. */
  frostCard: dark ? 'rgba(38,35,43,0.86)' : 'rgba(252,247,238,0.86)',
});

/** Three families. Gloock for titles, place names and big figures; Newsreader
 *  for a story's body and quotes; SF Pro Rounded for everything you press or
 *  read as UI (Roboto on Android). The two bundled faces have one weight
 *  each, so their tokens set none: a weight iOS cannot find falls back to the
 *  system face. App.tsx loads them before the splash goes. Each token is a
 *  style you spread (`...font.display`), so a family changes here alone. */
export const font = {
  title: { fontFamily: 'Gloock_400Regular' },
  story: { fontFamily: 'Newsreader_400Regular' },
  storyItalic: { fontFamily: 'Newsreader_400Regular_Italic' },
  storyBold: { fontFamily: 'Newsreader_600SemiBold' },
  display: { fontFamily: 'ui-rounded', fontWeight: '700' },
  displaySemi: { fontFamily: 'ui-rounded', fontWeight: '600' },
  prose: { fontFamily: 'ui-rounded', fontWeight: '400' },
  ui: { fontFamily: 'ui-rounded', fontWeight: '400' },
  uiMedium: { fontFamily: 'ui-rounded', fontWeight: '500' },
  uiBold: { fontFamily: 'ui-rounded', fontWeight: '600' },
} as const;

/** The only corners: a field, a card over the map, and a capsule for anything
 *  you press. Circles are half their side and need no token. */
export const radius = { field: 14, card: 24, pill: 999 };

/** A screen's or sheet's own title: Journal, Settings. */
export const screenTitle = { ...font.title, fontSize: 34, lineHeight: 40, color: color.ink };

/** The shadow for paper that floats over the map. The hold ring's seal glow
 *  is the only other (UI.md, "Spacing, radii and the two shadows"). */
export const lift = {
  shadowColor: color.shadow,
  shadowOffset: { width: 0, height: 4 },
  shadowRadius: 16,
  shadowOpacity: 0.12,
  elevation: 4,
};

/** A glass control's edge and shadow: the HIG Maps "thin stroke or light drop
 *  shadow", since glass drops its own shadow over a light map. */
export const glassEdge = { borderWidth: 1, borderColor: color.edge };
export const glassLift = {
  shadowColor: color.shadow,
  shadowOffset: { width: 0, height: 3 },
  shadowRadius: 10,
  shadowOpacity: 0.18,
};

/** The ink outline round the chrome over the map, the Collector's bar, the
 *  Journal orb and the dock, as the icons are drawn. An overlay inside the
 *  glass, since GlassView draws no border of its own. */
export const contour = {
  position: 'absolute' as const,
  top: 0,
  right: 0,
  bottom: 0,
  left: 0,
  borderRadius: radius.card,
  borderWidth: 2,
  borderColor: color.ink,
};

/** A card over the map: the unlock card, Plan's, the peek. Where it sits and
 *  its padding are the caller's. */
export const floating = {
  backgroundColor: color.paperRaised,
  borderRadius: radius.card,
  ...lift,
};

/** A glass control over the map: Journal, the walk bar. */
export const pill = {
  minHeight: 44,
  paddingHorizontal: 16,
  borderRadius: radius.pill,
  flexDirection: 'row' as const,
  alignItems: 'center' as const,
  justifyContent: 'center' as const,
  gap: 8,
};

/** The number a screen is about: the distance to a pin, a stat. The
 *  peek's distance is the small one, under the place it belongs to. */
export const figure = { ...font.title, fontSize: 52, lineHeight: 56, color: color.ink };
export const figureSmall = { ...font.title, fontSize: 36, lineHeight: 42, color: color.ink };

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
  title: { ...font.title, fontSize: 34, lineHeight: 38, color: color.ink },
  body: { ...font.story, fontSize: 20, lineHeight: 31, color: color.ink },
  meta: label,
};

/** The text inside a button. Pair with `color.paper` on gold, `color.ink`
 *  on the quiet and outlined ones. */
export const buttonText = {
  ...font.uiBold,
  fontSize: 17,
};
export const buttonTextSmall = { ...font.uiBold, fontSize: 15 };

/** A capsule for an action inside a page (Sign out, Choose photo): the quiet
 *  button's look, for a Pressable that lays out its own children. Anything
 *  that starts, keeps or ends something is `Button` (src/Button.tsx). An
 *  in-page action spreads `small` after it, with `buttonTextSmall` and
 *  `hitSlop={4}` to reach 44pt. A link to somewhere else stays a link. */
export const button = {
  quiet: {
    borderWidth: 1,
    borderColor: color.quietEdge,
    borderRadius: radius.pill,
    minHeight: 52,
    paddingVertical: 12,
    paddingHorizontal: 24,
    alignItems: 'center' as const,
    justifyContent: 'center' as const,
    backgroundColor: color.quiet,
  },
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
