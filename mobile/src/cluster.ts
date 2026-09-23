/** Group memories that share a map point.
 *
 * By coordinate, not place id: one venue spans several place rows and several
 * venues share one coordinate, so the coordinate is what the eye sees. See F6
 * in docs/08-ux-flows.md for why 60% of this corpus needs it.
 */

import type { LocatedMemory } from './api.ts';
import { metersBetween } from './region.ts';

export type MemoryGroup = {
  /** Stable across renders: derived from the rounded coordinate. */
  key: string;
  lat: number;
  lng: number;
  /** How far the furthest memory sits from the point they are drawn on. Zero at
   *  a genuine shared coordinate; kilometres once the grid loosens with the
   *  zoom. What tells a stack apart from a cluster. */
  spanMeters: number;
  memories: LocatedMemory[];
};

/** ~11m at the equator: tighter than the 50m the model calls "exact". */
const PRECISION = 4;

/** Past this, a group is a cluster of separate places rather than one point
 *  several memories share, and tapping it should zoom rather than open. */
export const CLUSTER_SPAN_M = 200;

function roundTo(value: number, places: number): number {
  const factor = 10 ** places;
  return Math.round(value * factor) / factor;
}

/**
 * How coarse the grid should be for a viewport this tall. Quantized on purpose:
 * `region` changes on every gesture, ahead of the fetch debounce, so a
 * precision derived from the raw delta would regroup every frame. Four values
 * means the memo holds until you cross a band.
 *
 * Street zoom keeps the 11m grid, because at that scale two venues forty metres
 * apart are two pins and the sheet pages through what genuinely shares a point.
 */
export function precisionFor(latitudeDelta: number): 1 | 2 | 3 | 4 {
  if (latitudeDelta < 0.05) return 4; // ~11m: the same doorway
  if (latitudeDelta < 0.5) return 3; //  ~110m: the same block
  if (latitudeDelta < 5) return 2; //   ~1.1km: the same neighbourhood
  return 1; //                          ~11km: the same city
}

export function groupByLocation(
  memories: LocatedMemory[],
  precision: number = PRECISION,
): MemoryGroup[] {
  const groups = new Map<string, MemoryGroup>();

  for (const memory of memories) {
    const lat = roundTo(memory.place.coordinates.lat, precision);
    const lng = roundTo(memory.place.coordinates.lng, precision);
    const key = `${lat},${lng}`;

    const existing = groups.get(key);
    if (existing) {
      existing.memories.push(memory);
    } else {
      groups.set(key, { key, lat, lng, spanMeters: 0, memories: [memory] });
    }
  }

  for (const group of groups.values()) {
    for (const memory of group.memories) {
      const away = metersBetween(
        group.lat,
        group.lng,
        memory.place.coordinates.lat,
        memory.place.coordinates.lng,
      );
      if (away > group.spanMeters) group.spanMeters = away;
    }
  }

  // Densest last so their markers paint on top of the single ones they overlap.
  return [...groups.values()].sort((a, b) => a.memories.length - b.memories.length);
}

/** What the marker says. A bare pin cannot show what it hides. */
export function groupLabel(group: MemoryGroup): string {
  if (group.memories.length === 1) return group.memories[0].place.name;
  const names = new Set(group.memories.map((m) => m.place.name));
  return names.size === 1
    ? `${group.memories[0].place.name} (${group.memories.length})`
    : `${names.size} places here`;
}
