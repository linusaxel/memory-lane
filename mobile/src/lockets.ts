/** The lockets a memory can be drawn as, on its pin and in its unlock. Any
 *  author picks any of them. Mirrors the lockets table (db/schema.sql).
 *  docs/10-decisions.md, "Lockets". */

import type { ImageSourcePropType } from 'react-native';

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
};

export const LOCKETS: Locket[] = [
  {
    id: 'hunter-compass',
    name: 'Hunter compass',
    locked: require('../assets/lockets/pin-hunter-compass-keyhole.png'),
    opened: require('../assets/lockets/pin-hunter-compass.png'),
  },
  {
    id: 'guilloche-oval',
    name: 'Guilloché oval',
    locked: require('../assets/lockets/pin-guilloche-oval-keyhole.png'),
    opened: require('../assets/lockets/pin-guilloche-oval.png'),
  },
  {
    id: 'deco-sunburst',
    name: 'Deco sunburst',
    locked: require('../assets/lockets/pin-deco-sunburst-keyhole.png'),
    opened: require('../assets/lockets/pin-deco-sunburst.png'),
  },
  {
    id: 'monogram-cushion',
    name: 'Monogram cushion',
    locked: require('../assets/lockets/pin-monogram-cushion-keyhole.png'),
    opened: require('../assets/lockets/pin-monogram-cushion.png'),
  },
  {
    id: 'gold-line-night',
    name: 'Gold line, night',
    locked: require('../assets/lockets/pin-gold-line-night-keyhole.png'),
    opened: require('../assets/lockets/pin-gold-line-night.png'),
  },
  {
    id: 'victorian-garnet',
    name: 'Victorian garnet',
    locked: require('../assets/lockets/pin-victorian-garnet-keyhole.png'),
    opened: require('../assets/lockets/pin-victorian-garnet.png'),
  },
];

export const LOCKET_DEFAULT: LocketId = 'hunter-compass';

/** An unknown id (a newer server's) draws as the default. */
export const locketOf = (id?: string | null): Locket =>
  LOCKETS.find((l) => l.id === id) ?? LOCKETS[0];
