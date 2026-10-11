/** The Collector: you pick a class, and its look grows through eight stages as
 *  your lockets (memories opened) climb. Nothing is spent and nothing is sold,
 *  so the pick can live on this phone (docs/10, "The Collector"). Pure, so
 *  node can test it: the art and the phone's copy are CollectorLook.tsx. */

/** Lockets that open each stage, the same for every class: a new look on walks
 *  one, two and three, then weeks and months apart on the free walk. */
export const STAGES = [0, 3, 8, 15, 30, 60, 120, 250];

export type ClassId = 'wayfinder' | 'pilgrim' | 'skywatcher' | 'chronicler';

export type CollectorClass = { id: ClassId; name: string; ranks: string[] };

export const CLASSES: CollectorClass[] = [
  {
    id: 'wayfinder',
    name: 'Wayfinder',
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
    name: 'Pilgrim',
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
    name: 'Skywatcher',
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
    name: 'Chronicler',
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

/** The class by id; anything else, or nothing chosen, is the Wayfinder. */
export function classOf(id: string | null | undefined): CollectorClass {
  return CLASSES.find((c) => c.id === id) ?? CLASSES[0];
}

/** The stage shown: the highest ever reached, so a hidden memory never takes
 *  a rank back (Ingress never takes a medal back). */
export function stageNow(reached: number | undefined, lockets: number): number {
  return Math.max(reached ?? 0, stageOf(lockets));
}
