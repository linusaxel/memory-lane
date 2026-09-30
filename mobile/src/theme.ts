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

  /** A memory, and the way to it: every pin, the next stop, the preview's
   *  line, the one primary button. The warm red no base map uses, so it never
   *  reads as water or park. docs/09-visual-design.md part 8. */
  ember: dual('#A8350F', '#F2703F'),
  /** The quiet button's fill: ember, barely. */
  emberSoft: dual('#F6E2D8', '#3A2219'),

  /** Openable now, and nothing else: the in-reach pin, the reach circle, the
   *  unlock ring. Bright gold, because ember beside the old ochre was one
   *  colour to a protanope. It is a fill, never text: text and marks on it are
   *  sealInk, and gold text on paper is sealDeep. */
  seal: dual('#F2B53A', '#F5C542'),
  /** Anything drawn on seal: a pin's edge and eye, the pill's words. */
  sealInk: dual('#2B1D05', '#1F1605'),
  /** The ring filling during a hold. */
  sealSoft: dual('#FCEBC2', '#3E3112'),
  /** Seal as text or a thin mark on paper, and the padlock inside the ring. */
  sealDeep: dual('#7A4F00', '#F7D074'),

  /** Out of reach: the same padlock, faded. Dark enough to hold against the
   *  parchment map, and lighter in the dark where a dark pin vanishes. */
  faded: dual('#776E64', '#9A9086'),

  /** The wash behind a reachable pin, so it is findable before its shape is.
   *  Deliberately not a pair: it is a translucent seal over a map, and the
   *  seal's dark value is lighter, so one alpha reads about the same over
   *  either. It lives here rather than inline so a palette change reaches it. */
  halo: 'rgba(242,181,58,0.3)',

  /** `lift`'s shadow, and the scrim over an uploading photo. */
  shadow: '#000',
  scrim: 'rgba(0,0,0,0.35)',
};

/** Real colours, for the few props that cannot take a DynamicColorIOS value:
 *  map overlays, Svg fills, the splash. Pick with `useColorScheme()`. Where a
 *  name is also in `color`, the values are the same pair. */
export const solid = (dark: boolean) => ({
  paper: dark ? '#161412' : '#F7F4EE',
  ink: dark ? '#F2EDE4' : '#1C1917',
  rule: dark ? '#332E27' : '#E0D9CC',
  ember: dark ? '#F2703F' : '#A8350F',
  /** The darker edge Apple Maps draws round a route. */
  emberCasing: dark ? '#8A2E0C' : '#6E2208',
  /** The preview's line: ember washed out, so the ember pins on it pop. */
  line: dark ? '#8C4128' : '#EDA38A',
  lineCasing: dark ? '#5E2A18' : '#D98266',
  /** The reach circle: the seal, washed over the map. */
  reachStroke: dark ? 'rgba(245,197,66,0.75)' : 'rgba(176,120,10,0.7)',
  reachFill: dark ? 'rgba(245,197,66,0.12)' : 'rgba(242,181,58,0.14)',
  /** mobile/assets/icon.svg and icon-dark.svg. */
  tile: dark ? '#0a2b2c' : '#106a6d',
  road: dark ? '#e9f1ee' : '#f2ede4',
  sun: '#f2a65a',
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

/** The text inside a button. Pair with `color.paper` on ember, `color.ink`
 *  on the quiet and outlined ones. */
export const buttonText = {
  ...font.uiBold,
  fontSize: 17,
};
export const buttonTextSmall = { ...font.uiBold, fontSize: 15 };

/** The app's buttons: three capsules, two sizes. Spread one and add only where
 *  it sits (margin, alignSelf); the text is `buttonText`. An action inside the
 *  page rather than ending it (Leave note, Edit this memory) spreads `small`
 *  after the capsule, with `buttonTextSmall` and `hitSlop={4}` to reach 44pt.
 *  A link to somewhere else (Terms, a credit) stays a link. */
const buttonBox = {
  borderWidth: 1.5,
  borderColor: 'transparent',
  borderRadius: radius.pill,
  minHeight: 52,
  paddingVertical: 14,
  paddingHorizontal: 24,
  alignItems: 'center' as const,
  justifyContent: 'center' as const,
};
export const button = {
  /** The one thing to do. Text in paper. */
  solid: { ...buttonBox, backgroundColor: color.ember },
  /** The way back, next to a solid one. Text in ink. */
  quiet: { ...buttonBox, backgroundColor: color.emberSoft },
  /** An action standing on its own. Text in ink. */
  outline: { ...buttonBox, borderColor: color.rule },
  small: { minHeight: 36, paddingVertical: 7, paddingHorizontal: 16 },
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
  ({ pressed }: PressableStateCallbackType): StyleProp<ViewStyle> => [
    base,
    pressed && { opacity: 0.85, transform: [{ scale: 0.97 }] },
  ];
