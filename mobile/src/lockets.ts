/** The lockets a memory can be drawn as, on its pin and in its unlock. Any
 *  author picks any of them. Mirrors the lockets table (db/schema.sql).
 *  docs/10-decisions.md, "Lockets". */

import type { ImageSourcePropType } from 'react-native';

import { GoldDeco } from './lockets/designs/GoldDeco.tsx';
import { GoldHunter } from './lockets/designs/GoldHunter.tsx';
import { GoldMonogram } from './lockets/designs/GoldMonogram.tsx';
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
  | 'victorian-garnet';

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
];

export const LOCKET_DEFAULT: LocketId = 'hunter-compass';

/** An unknown id (a newer server's) draws as the default. */
export const locketOf = (id?: string | null): Locket =>
  LOCKETS.find((l) => l.id === id) ?? LOCKETS[0];
