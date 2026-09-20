/** Every colour and typeface in the app. Never write a hex or a font name
 *  anywhere else. Why these ones: docs/09-visual-design.md.
 *
 *  `DynamicColorIOS` is why this is one file and not eleven - the platform
 *  resolves the pair at draw time, so `StyleSheet.create` at module scope keeps
 *  working and appearance changes repaint with no hook and no context. It is
 *  iOS-only: Android takes the light value until somebody does the theme-context
 *  refactor. A real gap, logged in mobile/UI.md.
 */

import { DynamicColorIOS, Platform } from 'react-native';

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
  inkFaint: dual('#8A837A', '#8A8276'),
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
