/** The Collector: you pick a class, and its look grows through eight stages as
 *  your lockets (memories opened) climb. Nothing is spent and nothing is sold,
 *  so the pick can live on this phone. Not wired in yet: the art is to come. */

/** Lockets that open each stage, the same for every class. */
export const STAGES = [0, 5, 15, 30, 60, 120, 300, 1000];

export type CollectorClass = { id: string; ranks: string[] };

export const CLASSES: CollectorClass[] = [
  {
    id: 'wayfinder',
    ranks: [
      'Stray',
      'Trailwalker',
      'Lamplit',
      'Wayfinder',
      'Pathkeeper',
      'Lantern Warden',
      'Elder of Roads',
      'The Old Way',
    ],
  },
  {
    id: 'pilgrim',
    ranks: [
      'Threadbare',
      'Mender',
      'Wayfarer',
      'Pilgrim',
      'Quilter',
      'Seasoned Pilgrim',
      'Keeper of Patches',
      'The Quilt of Ways',
    ],
  },
  {
    id: 'skywatcher',
    ranks: [
      'Wisp',
      'Mist',
      'Fair-weather',
      'Skywatcher',
      'Rainbringer',
      'Sunbreak',
      'Stormcaller',
      'The High Sky',
    ],
  },
  {
    id: 'chronicler',
    ranks: [
      'Novice',
      'Reader',
      'Notetaker',
      'Chronicler',
      'Archivist',
      'Loremaster',
      'Keeper of Records',
      'The Living Library',
    ],
  },
];

/** The stage this many lockets has reached, 0 to 7. */
export function stageOf(lockets: number): number {
  return STAGES.filter((at) => at <= lockets).length - 1;
}

/** Lockets to the next stage, or null at the top. */
export function toNext(lockets: number): number | null {
  const next = STAGES.find((at) => at > lockets);
  return next === undefined ? null : next - lockets;
}
