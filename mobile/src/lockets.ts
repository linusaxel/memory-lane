/** The lockets a memory can be drawn as, on its pin and in its unlock. Any
 *  author picks any of them. Mirrors the lockets table (db/schema.sql).
 *  docs/10-decisions.md, "Lockets". */

import type { ImageSourcePropType } from 'react-native';

import { GoldCeltic } from './lockets/designs/GoldCeltic.tsx';
import { GoldDeco } from './lockets/designs/GoldDeco.tsx';
import { GoldEye } from './lockets/designs/GoldEye.tsx';
import { GoldHeart } from './lockets/designs/GoldHeart.tsx';
import { GoldHunter } from './lockets/designs/GoldHunter.tsx';
import { GoldMonogram } from './lockets/designs/GoldMonogram.tsx';
import { GoldMoon } from './lockets/designs/GoldMoon.tsx';
import { GoldNight } from './lockets/designs/GoldNight.tsx';
import { GoldOval } from './lockets/designs/GoldOval.tsx';
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
  | 'sweetheart';

type Locket = {
  id: LocketId;
  name: string;
  /** With its keyhole: still locked. */
  locked: ImageSourcePropType;
  opened: ImageSourcePropType;
  /** How it is drawn and how it opens (lockets/designs). */
  design: LocketDesign;
};

export const LOCKETS: Locket[] = [
  {
    id: 'hunter-compass',
    name: 'Hunter compass',
    locked: require('../assets/lockets/pin-hunter-compass-keyhole.png'),
    opened: require('../assets/lockets/pin-hunter-compass.png'),
    design: GoldHunter,
  },
  {
    id: 'guilloche-oval',
    name: 'Guilloché oval',
    locked: require('../assets/lockets/pin-guilloche-oval-keyhole.png'),
    opened: require('../assets/lockets/pin-guilloche-oval.png'),
    design: GoldOval,
  },
  {
    id: 'deco-sunburst',
    name: 'Deco sunburst',
    locked: require('../assets/lockets/pin-deco-sunburst-keyhole.png'),
    opened: require('../assets/lockets/pin-deco-sunburst.png'),
    design: GoldDeco,
  },
  {
    id: 'monogram-cushion',
    name: 'Monogram cushion',
    locked: require('../assets/lockets/pin-monogram-cushion-keyhole.png'),
    opened: require('../assets/lockets/pin-monogram-cushion.png'),
    design: GoldMonogram,
  },
  {
    id: 'gold-line-night',
    name: 'Gold line, night',
    locked: require('../assets/lockets/pin-gold-line-night-keyhole.png'),
    opened: require('../assets/lockets/pin-gold-line-night.png'),
    design: GoldNight,
  },
  {
    id: 'victorian-garnet',
    name: 'Victorian garnet',
    locked: require('../assets/lockets/pin-victorian-garnet-keyhole.png'),
    opened: require('../assets/lockets/pin-victorian-garnet.png'),
    design: GoldVictorian,
  },
  {
    id: 'celtic-knot',
    name: 'Celtic knot',
    // ponytail: no keyhole face drawn yet, so locked shows the plain one.
    locked: require('../assets/lockets/pin-celtic-knot.png'),
    opened: require('../assets/lockets/pin-celtic-knot.png'),
    design: GoldCeltic,
  },
  {
    id: 'moon-phase',
    name: 'Moon phase',
    // ponytail: no keyhole face drawn yet, so locked shows the plain one.
    locked: require('../assets/lockets/pin-moon-phase.png'),
    opened: require('../assets/lockets/pin-moon-phase.png'),
    design: GoldMoon,
  },
  {
    id: 'lovers-eye',
    name: "Lover's eye",
    // ponytail: no keyhole face drawn yet, so locked shows the plain one.
    locked: require('../assets/lockets/pin-lovers-eye.png'),
    opened: require('../assets/lockets/pin-lovers-eye.png'),
    design: GoldEye,
  },
  {
    id: 'sweetheart',
    name: 'Sweetheart',
    // ponytail: no keyhole face drawn yet, so locked shows the plain one.
    locked: require('../assets/lockets/pin-sweetheart.png'),
    opened: require('../assets/lockets/pin-sweetheart.png'),
    design: GoldHeart,
  },
];

export const LOCKET_DEFAULT: LocketId = 'hunter-compass';

/** An unknown id (a newer server's) draws as the default. */
export const locketOf = (id?: string | null): Locket =>
  LOCKETS.find((l) => l.id === id) ?? LOCKETS[0];
