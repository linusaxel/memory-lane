/** Group memories that share a map point.
 *
 * By coordinate, not place id: one venue spans several place rows and several
 * venues share one coordinate, so the coordinate is what the eye sees. See F6
 * in docs/08-ux-flows.md for why 60% of this corpus needs it.
 */

import type { LocatedMemory } from './api.ts';

export type MemoryGroup = {
  /** Stable across renders: derived from the rounded coordinate. */
  key: string;
  lat: number;
  lng: number;
  memories: LocatedMemory[];
};

/** ~11m at the equator: tighter than the 50m the model calls "exact". */
const PRECISION = 4;

function roundTo(value: number, places: number): number {
  const factor = 10 ** places;
  return Math.round(value * factor) / factor;
}

export function groupByLocation(memories: LocatedMemory[]): MemoryGroup[] {
  const groups = new Map<string, MemoryGroup>();

  for (const memory of memories) {
    const lat = roundTo(memory.place.coordinates.lat, PRECISION);
    const lng = roundTo(memory.place.coordinates.lng, PRECISION);
    const key = `${lat},${lng}`;

    const existing = groups.get(key);
    if (existing) {
      existing.memories.push(memory);
    } else {
      groups.set(key, { key, lat, lng, memories: [memory] });
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
