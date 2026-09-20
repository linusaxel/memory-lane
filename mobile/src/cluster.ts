/** Group memories that share a map point.
 *
 * Not a nicety. The extraction model emits a city centroid whenever it does not
 * know an address, so 111 of 186 placed memories sit on 34 coordinates - one
 * point in Times Square carries fourteen unrelated venues. Drawn one marker per
 * memory, that is a single dot that hands you an arbitrary one of the fourteen
 * when tapped, and thirteen memories the map never admits exist.
 *
 * Grouping is by rounded coordinate rather than by place id, because the same
 * venue also appears under several place rows and several venues appear under
 * one coordinate. The coordinate is what the eye sees, so it is what the tap
 * target should follow.
 */

import type { LocatedMemory } from './api.ts';

export type MemoryGroup = {
  /** Stable across renders: derived from the rounded coordinate. */
  key: string;
  lat: number;
  lng: number;
  memories: LocatedMemory[];
};

/**
 * 4 decimal places is ~11m at the equator - tighter than the 50m the model
 * calls "exact", so genuinely distinct addresses stay separate while repeated
 * emissions of one centroid collapse.
 */
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

/** What the marker says. A bare pin cannot show that it hides thirteen others. */
export function groupLabel(group: MemoryGroup): string {
  if (group.memories.length === 1) return group.memories[0].place.name;
  const names = new Set(group.memories.map((m) => m.place.name));
  return names.size === 1
    ? `${group.memories[0].place.name} (${group.memories.length})`
    : `${names.size} places here`;
}
