/** The Collector: you pick a class, and its look grows through eight stages as
 *  your lockets (memories opened) and the memories you file climb. Nothing is spent and nothing is sold,
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

/** Memories you filed, still public, that each stage also needs: the
 *  Collector grows by leaving memories as well as opening them. */
export const FILED = [0, 1, 2, 3, 5, 8, 12, 20];

/** The stage reached, 0 to 7: the lower of what the lockets and the filed
 *  memories each open. */
export function stageOf(lockets: number, filed: number): number {
  const by = (scale: number[], n: number) => scale.filter((at) => at <= n).length - 1;
  return Math.min(by(STAGES, lockets), by(FILED, filed));
}

/** What the stage after this one still wants, or null at the top. */
export function wants(
  stage: number,
  lockets: number,
  filed: number,
): { lockets: number; filed: number } | null {
  if (stage + 1 >= STAGES.length) return null;
  return {
    lockets: Math.max(0, STAGES[stage + 1] - lockets),
    filed: Math.max(0, FILED[stage + 1] - filed),
  };
}

/** "36 more lockets and 1 memory of yours", leaving out a count already met;
 *  "" when both are. */
export function wantsWords(want: { lockets: number; filed: number }): string {
  const parts = [];
  if (want.lockets > 0)
    parts.push(`${want.lockets} more ${want.lockets === 1 ? 'locket' : 'lockets'}`);
  if (want.filed > 0)
    parts.push(`${want.filed} ${want.filed === 1 ? 'memory' : 'memories'} of yours`);
  return parts.join(' and ');
}

/** The class by id; anything else, or nothing chosen, is the Wayfinder. */
export function classOf(id: string | null | undefined): CollectorClass {
  return CLASSES.find((c) => c.id === id) ?? CLASSES[0];
}

/** The stage shown: the highest ever reached, so a hidden memory never takes
 *  a rank back (Ingress never takes a medal back). */
export function stageNow(reached: number | undefined, lockets: number, filed: number): number {
  return Math.max(reached ?? 0, stageOf(lockets, filed));
}

/** How far from this stage to the next, 0 to 1: the scale further behind
 *  decides it. Full at the top, and empty while a kept rank sits above the
 *  counts. */
export function rankInto(stage: number, lockets: number, filed: number): number {
  if (stage + 1 >= STAGES.length) return 1;
  const into = (scale: number[], n: number) =>
    Math.min(1, Math.max(0, (n - scale[stage]) / (scale[stage + 1] - scale[stage])));
  return Math.min(into(STAGES, lockets), into(FILED, filed));
}
