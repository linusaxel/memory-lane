/** The decisions. One file, because there were none before.
 *
 * The research verdict on why generated interfaces look generic is not that
 * they pick a bad style - it is that they pick no style: the statistical
 * default everywhere, which is Tailwind's zinc ramp, the system sans, and a
 * floating white card. This app had all three. Everything here is a choice that
 * could have gone another way, which is the only thing that separates a
 * designed screen from an averaged one.
 *
 * The direction comes from the product, not from a trend. This is an archive of
 * anecdotes pinned to coordinates - things people said happened somewhere. Its
 * real-world neighbours are the field guide, the historical plaque and the
 * passport stamp, not the SaaS dashboard. So: paper rather than white, ink
 * rather than grey, a serif for the storytelling and a mono for the
 * instrument readings.
 *
 * ## Dark mode
 *
 * Every colour is a pair, resolved by the system rather than by us. An app you
 * use outdoors, at night, walking to a comedy club, cannot be light-only.
 *
 * `DynamicColorIOS` is why this is one file and not eleven. It returns a colour
 * the platform resolves at draw time, so `StyleSheet.create` at module scope
 * keeps working, every component keeps importing a plain `color.ink`, and a
 * change of appearance repaints without a re-render or a context. The cost is
 * that it is iOS-only: Android takes the light value until somebody does the
 * theme-context refactor, and that is a real gap rather than a shrug - it is
 * just not worth eleven files and a hook while the app is iOS-first.
 *
 * Dark is not the light palette inverted. Paper becomes a warm near-black
 * rather than grey, the seal lightens so it still reads as the one thing you
 * can act on, and `faded` goes *lighter* - a locked pin has to survive a dark
 * map, where the light-mode value disappeared.
 */

import { DynamicColorIOS, Platform } from 'react-native';

/** Light and dark, resolved by the platform. Android gets the light value. */
const dual = (light: string, dark: string) =>
  Platform.OS === 'ios' ? DynamicColorIOS({ light, dark }) : light;

export const color = {
  /** Warm paper. Not #fff, and not a zinc. It also sits close to the muted
   *  Apple map underneath, so the sheets feel cut from the same sheet. */
  paper: dual('#F7F4EE', '#161412'),
  /** One step up for surfaces that need to lift off the paper. */
  paperRaised: dual('#FFFDF9', '#201D19'),
  ink: dual('#1C1917', '#F2EDE4'),
  inkSoft: dual('#4A443D', '#BDB5A8'),
  inkFaint: dual('#8A837A', '#8A8276'),
  /** Hairlines and dividers. Editorial layouts rule; they do not shadow. */
  rule: dual('#E0D9CC', '#332E27'),

  /** The one accent: stamp ink. Everything openable is this colour and nothing
   *  else is. Deliberately not amber-500 - that is the default the research
   *  names. It lightens in the dark so it still reads as the one thing to act
   *  on rather than as a dried bloodstain. */
  seal: dual('#C0462B', '#E2603F'),
  /** The ring filling during a hold. */
  sealSoft: dual('#F0D9CE', '#4A2418'),
  /** The padlock inside the ring, which sits on paper at rest and on sealSoft
   *  when full - so it has to hold against both. */
  sealDeep: dual('#8F2F1B', '#F2A88F'),

  /** Out of reach: the same padlock, faded, as if the stamp never landed.
   *  Dark enough to hold its own against the parchment map - the first attempt
   *  was #A9A199 and the pins disappeared into the streets. It goes the other
   *  way in the dark, where the map is near-black and a dark pin vanishes. */
  faded: dual('#776E64', '#9A9086'),
};

/** Two families and no more. Fraunces is an old-style serif with its wonk left
 *  in - it has an opinion, which is the requirement. IBM Plex Mono is the
 *  apparatus: distances, counts, labels. Numbers in a mono read as measurements
 *  rather than as decoration. */
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
