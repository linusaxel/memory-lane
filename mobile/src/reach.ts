/** Which locked pins the person can open from where they are standing.
 *
 * This decides what the map *shows*, never what anybody may *read* - the server
 * re-measures before it hands over a summary. That is what makes it safe for
 * this to be a client-side judgement, and why it can be a pure function with no
 * network in it.
 */

import type { Coordinates } from './api.ts';
import type { MemoryGroup } from './cluster.ts';
import { metersBetween } from './region.ts';

export type Reach = 'open' | 'locked' | 'unlockable';

/** Only used if a memory somehow arrives without the server's radius. */
export const FALLBACK_RADIUS_M = 150;

/**
 * Past this, "the nearest locked memory is 6,181 km away" is not a hint, it is
 * a fact about the corpus, and the empty-state card says it better. The pill
 * exists to start a walk; 30km is the outer edge of somewhere you might go
 * today.
 */
export const HINT_RANGE_M = 30_000;

export function reachOf(group: MemoryGroup, position: Coordinates | null): Reach {
  const locked = group.memories.filter((memory) => memory.locked);
  // A group is open only when nothing in it is locked. One locked memory under
  // a marker still means that marker hides something.
  if (locked.length === 0) return 'open';
  if (!position) return 'locked';

  const away = metersBetween(position.lat, position.lng, group.lat, group.lng);
  return away <= (locked[0].unlock_radius_meters ?? FALLBACK_RADIUS_M) ? 'unlockable' : 'locked';
}

/** The closest thing still shut, so a map of padlocks can answer "where do I
 *  go" and not only "you cannot read this". Null when something is already in
 *  reach, because then there is nothing to walk to. */
export function nearestLocked(
  groups: MemoryGroup[],
  position: Coordinates | null,
): { group: MemoryGroup; meters: number } | null {
  if (!position) return null;

  let best: { group: MemoryGroup; meters: number } | null = null;
  for (const group of groups) {
    const reach = reachOf(group, position);
    if (reach === 'unlockable') return null;
    if (reach === 'open') continue;

    const meters = metersBetween(position.lat, position.lng, group.lat, group.lng);
    if (!best || meters < best.meters) best = { group, meters };
  }
  return best && best.meters <= HINT_RANGE_M ? best : null;
}
