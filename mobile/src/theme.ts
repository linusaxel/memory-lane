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
 */

export const color = {
  /** Warm paper. Not #fff, and not a zinc. It also sits close to the muted
   *  Apple map underneath, so the sheets feel cut from the same sheet. */
  paper: '#F7F4EE',
  /** One step up for surfaces that need to lift off the paper. */
  paperRaised: '#FFFDF9',
  ink: '#1C1917',
  inkSoft: '#4A443D',
  inkFaint: '#8A837A',
  /** Hairlines and dividers. Editorial layouts rule; they do not shadow. */
  rule: '#E0D9CC',

  /** The one accent: stamp ink. Everything openable is this colour and nothing
   *  else is. Deliberately not amber-500 - that is the default the research
   *  names. */
  seal: '#C0462B',
  sealSoft: '#F0D9CE',
  sealDeep: '#8F2F1B',

  /** Out of reach: the same padlock, faded, as if the stamp never landed. Dark
   *  enough to hold its own against the parchment map - the first attempt was
   *  #A9A199 and the pins disappeared into the streets. */
  faded: '#776E64',
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
