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

  /** The one accent: stamp ink - a warm ochre, not the stamp red this was
   *  before 2026-09-23 (docs/10-decisions.md#warm-accent-not-a-reskin). Everything
   *  openable is this colour and nothing else is. */
  seal: dual('#8A5A17', '#D9A54B'),
  /** The ring filling during a hold. */
  sealSoft: dual('#F0E4C8', '#3D3018'),
  /** The padlock inside the ring, which sits on paper at rest and on sealSoft
   *  when full - so it has to hold against both. */
  sealDeep: dual('#5C3A0E', '#F0C878'),

  /** Walk here next: the one stop that hops, and the preview's line. Never
   *  openable - in reach, the pin turns seal. */
  route: dual('#1A64D6', '#5AA2FF'),

  /** A memory on the map: every pin at rest, and the dot of a walk's stop in
   *  the journal. The logo's teal, lifted in the dark so paper holds on it.
   *  Never openable (seal) and never next (route). */
  brand: dual('#106A6D', '#2E8F92'),

  /** Out of reach: the same padlock, faded. Dark enough to hold against the
   *  parchment map, and lighter in the dark where a dark pin vanishes. */
  faded: dual('#776E64', '#9A9086'),

  /** The wash behind a reachable pin, so it is findable before its shape is.
   *  Deliberately not a pair: it is a translucent seal over a map, and the
   *  seal's dark value is lighter, so one alpha reads about the same over
   *  either. It lives here rather than inline so a palette change reaches it. */
  halo: 'rgba(138,90,23,0.16)',

  /** The two shadows UI.md allows, and the scrim over an uploading photo. */
  shadow: '#000',
  scrim: 'rgba(0,0,0,0.35)',
};

/** Real colours, for the few props that cannot take a DynamicColorIOS value:
 *  map overlays, Svg fills, the splash. Pick with `useColorScheme()`. Where a
 *  name is also in `color`, the values are the same pair. */
export const solid = (dark: boolean) => ({
  paper: dark ? '#161412' : '#F7F4EE',
  route: dark ? '#5AA2FF' : '#1A64D6',
  /** The darker edge Apple Maps draws round a route. */
  routeCasing: dark ? '#1B4F99' : '#0E3F8C',
  /** The reach circle: the seal, washed over the map. */
  reachStroke: dark ? 'rgba(217,165,75,0.7)' : 'rgba(138,90,23,0.55)',
  reachFill: dark ? 'rgba(217,165,75,0.12)' : 'rgba(138,90,23,0.07)',
  /** mobile/assets/icon.svg and icon-dark.svg. */
  tile: dark ? '#0a2b2c' : '#106a6d',
  road: dark ? '#e9f1ee' : '#f2ede4',
  sun: '#f2a65a',
});

/** Two families and no more. Fraunces tells the stories, IBM Plex Mono is the
 *  apparatus - distances, counts, labels. */
export const font = {
  display: 'Fraunces_700Bold',
  displaySemi: 'Fraunces_600SemiBold',
  prose: 'Fraunces_400Regular',
  mono: 'IBMPlexMono_400Regular',
  monoMedium: 'IBMPlexMono_500Medium',
  monoBold: 'IBMPlexMono_600SemiBold',
};

/** Uppercase mono with tracking. The app's label voice, used everywhere a
 *  screen names a thing rather than says something. */
export const label = {
  fontFamily: font.monoBold,
  fontSize: 11,
  letterSpacing: 1.1,
  textTransform: 'uppercase' as const,
  color: color.inkFaint,
};

/** The text inside a button, filled or outlined. One step up from `label` in
 *  size and tracking, because it is the thing being pressed. Pair with
 *  `color: color.paper` on ink, `color.ink` on an outline. */
export const buttonText = {
  fontFamily: font.monoBold,
  fontSize: 12,
  letterSpacing: 1.2,
  textTransform: 'uppercase' as const,
};

/** The app's buttons: three boxes, one size. Spread one and add only where
 *  it sits (margin, alignSelf); the text is always `buttonText`. */
const buttonBox = {
  borderWidth: 1,
  borderRadius: 4,
  paddingVertical: 15,
  paddingHorizontal: 22,
  alignItems: 'center' as const,
  justifyContent: 'center' as const,
};
export const button = {
  /** The one thing to do. Text in paper. */
  solid: { ...buttonBox, backgroundColor: color.ink, borderColor: color.ink },
  /** The way back, next to a solid one. Text in ink. */
  quiet: { ...buttonBox, borderColor: color.rule },
  /** An action standing on its own. Text in ink. */
  outline: { ...buttonBox, borderColor: color.ink },
};

/** A text field. The display-name input renders twice - You and Submit - and
 *  they must not drift. */
export const input = {
  borderWidth: 1,
  borderColor: color.rule,
  borderRadius: 4,
  paddingHorizontal: 14,
  paddingVertical: 12,
  fontFamily: font.prose,
  fontSize: 17,
  color: color.ink,
  backgroundColor: color.paperRaised,
};

/** Every Pressable in the app dims while it is held.
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
    pressed && { opacity: 0.55 },
  ];
