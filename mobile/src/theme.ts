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

  /** The one accent: stamp ink. Everything openable is this colour and nothing
   *  else is. */
  seal: dual('#C0462B', '#E2603F'),
  /** The ring filling during a hold. */
  sealSoft: dual('#F0D9CE', '#4A2418'),
  /** The padlock inside the ring, which sits on paper at rest and on sealSoft
   *  when full - so it has to hold against both. */
  sealDeep: dual('#8F2F1B', '#F2A88F'),

  /** Out of reach: the same padlock, faded. Dark enough to hold against the
   *  parchment map, and lighter in the dark where a dark pin vanishes. */
  faded: dual('#776E64', '#9A9086'),

  /** The wash behind a reachable pin, so it is findable before its shape is.
   *  Deliberately not a pair: it is a translucent seal over a map, and the
   *  seal's dark value is lighter, so one alpha reads about the same over
   *  either. It lives here rather than inline so a palette change reaches it. */
  halo: 'rgba(192,70,43,0.16)',
};

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
