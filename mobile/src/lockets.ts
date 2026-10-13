/** The lockets a memory can be drawn as, on its pin and in its unlock. Any
 *  author picks any of them. Mirrors the lockets table (db/schema.sql).
 *  docs/10-decisions.md, "Lockets". */

import type { ImageSourcePropType } from 'react-native';

import { GoldBulla } from './lockets/designs/GoldBulla.tsx';
import { GoldCeltic } from './lockets/designs/GoldCeltic.tsx';
import { GoldDeco } from './lockets/designs/GoldDeco.tsx';
import { GoldDragonfly } from './lockets/designs/GoldDragonfly.tsx';
import { GoldEye } from './lockets/designs/GoldEye.tsx';
import { GoldFrost } from './lockets/designs/GoldFrost.tsx';
import { GoldHeart } from './lockets/designs/GoldHeart.tsx';
import { GoldHunter } from './lockets/designs/GoldHunter.tsx';
import { GoldMokume } from './lockets/designs/GoldMokume.tsx';
import { GoldMonogram } from './lockets/designs/GoldMonogram.tsx';
import { GoldMoon } from './lockets/designs/GoldMoon.tsx';
import { GoldNight } from './lockets/designs/GoldNight.tsx';
import { GoldOval } from './lockets/designs/GoldOval.tsx';
import { GoldQuatre } from './lockets/designs/GoldQuatre.tsx';
import { GoldRoseEgg } from './lockets/designs/GoldRoseEgg.tsx';
import { GoldVictorian } from './lockets/designs/GoldVictorian.tsx';
import type { LocketDesign } from './lockets/types.ts';

export type LocketId =
  | 'hunter-compass'
  | 'guilloche-oval'
  | 'deco-sunburst'
  | 'monogram-cushion'
  | 'gold-line-night'
  | 'victorian-garnet'
  | 'celtic-knot'
  | 'moon-phase'
  | 'lovers-eye'
  | 'sweetheart'
  | 'quatre-couleur'
  | 'rose-egg'
  | 'dragonfly'
  | 'white-gold-frost'
  | 'etruscan-bulla'
  | 'mokume-river';

type Locket = {
  id: LocketId;
  name: string;
  /** The pin: full gold while locked, faded once opened (MemoryMarker). */
  pin: ImageSourcePropType;
  /** How it is drawn and how it opens (lockets/designs). */
  design: LocketDesign;
};

export const LOCKETS: Locket[] = [
  {
    id: 'hunter-compass',
    name: 'Hunter compass',
    pin: require('../assets/lockets/pin-hunter-compass.png'),
    design: GoldHunter,
  },
  {
    id: 'guilloche-oval',
    name: 'Guilloché oval',
    pin: require('../assets/lockets/pin-guilloche-oval.png'),
    design: GoldOval,
  },
  {
    id: 'deco-sunburst',
    name: 'Deco sunburst',
    pin: require('../assets/lockets/pin-deco-sunburst.png'),
    design: GoldDeco,
  },
  {
    id: 'monogram-cushion',
    name: 'Monogram cushion',
    pin: require('../assets/lockets/pin-monogram-cushion.png'),
    design: GoldMonogram,
  },
  {
    id: 'gold-line-night',
    name: 'Gold line, night',
    pin: require('../assets/lockets/pin-gold-line-night.png'),
    design: GoldNight,
  },
  {
    id: 'victorian-garnet',
    name: 'Victorian garnet',
    pin: require('../assets/lockets/pin-victorian-garnet.png'),
    design: GoldVictorian,
  },
  {
    id: 'celtic-knot',
    name: 'Celtic knot',
    pin: require('../assets/lockets/pin-celtic-knot.png'),
    design: GoldCeltic,
  },
  {
    id: 'moon-phase',
    name: 'Moon phase',
    pin: require('../assets/lockets/pin-moon-phase.png'),
    design: GoldMoon,
  },
  {
    id: 'lovers-eye',
    name: "Lover's eye",
    pin: require('../assets/lockets/pin-lovers-eye.png'),
    design: GoldEye,
  },
  {
    id: 'sweetheart',
    name: 'Sweetheart',
    pin: require('../assets/lockets/pin-sweetheart.png'),
    design: GoldHeart,
  },
  {
    id: 'quatre-couleur',
    name: 'Quatre-couleur garland',
    pin: require('../assets/lockets/pin-quatre-couleur.png'),
    design: GoldQuatre,
  },
  {
    id: 'rose-egg',
    name: 'Rose-gold egg',
    pin: require('../assets/lockets/pin-rose-egg.png'),
    design: GoldRoseEgg,
  },
  {
    id: 'dragonfly',
    name: 'Green-gold dragonfly',
    pin: require('../assets/lockets/pin-dragonfly.png'),
    design: GoldDragonfly,
  },
  {
    id: 'white-gold-frost',
    name: 'White-gold frost',
    pin: require('../assets/lockets/pin-white-gold-frost.png'),
    design: GoldFrost,
  },
  {
    id: 'etruscan-bulla',
    name: 'Etruscan bulla',
    pin: require('../assets/lockets/pin-etruscan-bulla.png'),
    design: GoldBulla,
  },
  {
    id: 'mokume-river',
    name: 'Mokume-gane river',
    pin: require('../assets/lockets/pin-mokume-river.png'),
    design: GoldMokume,
  },
];

export const LOCKET_DEFAULT: LocketId = 'hunter-compass';

/** An unknown id (a newer server's) draws as the default. */
export const locketOf = (id?: string | null): Locket =>
  LOCKETS.find((l) => l.id === id) ?? LOCKETS[0];
