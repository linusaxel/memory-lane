/** Which locked pins the person can open from where they are standing.
 *
 * This decides what the map *shows*, never what anybody may *read* - the server
 * re-measures before it hands over a summary. That is what makes it safe for
 * this to be a client-side judgement, and why it can be a pure function with no
 * network in it.
 */

import type { Coordinates, LocatedMemory } from './api.ts';
import type { MemoryGroup } from './cluster.ts';
import { metersBetween } from './region.ts';

/** Where you stand relative to a coordinate, from nothing-to-earn to earned.
 *  `plain` and `stamped` are both unlocked; only the local store knows which
 *  one was walked for. The pin only draws `unlockable`; the title, banner and
 *  walk hint use all five. */
export type Reach = 'plain' | 'stamped' | 'warm' | 'locked' | 'unlockable';

/** Only used if a memory somehow arrives without the server's radius. */
export const FALLBACK_RADIUS_M = 20;

/** How much past the gate still reads as "nearly". Three radii is a few
 *  minutes' walk at the 150m gate, which is the distance at which turning
 *  around is still a decision rather than a trek. */
export const WARM_MULTIPLIER = 3;

/** To the closest one, not to the group's point. The group's point is a rounded
 *  coordinate, and at anything looser than street precision it can sit
 *  kilometres from every memory filed under it. */
function metersToNearest(position: Coordinates, memories: LocatedMemory[]): number {
  let best = Infinity;
  for (const memory of memories) {
    const away = metersBetween(
      position.lat,
      position.lng,
      memory.place.coordinates.lat,
      memory.place.coordinates.lng,
    );
    if (away < best) best = away;
  }
  return best;
}

/** `earned` is what this device has already unlocked. Without it `stamped` and
 *  `plain` are the same string: /v1/memories/nearby never takes a position, so
 *  it reports both as unlocked and only the local store can tell them apart. */
export function reachOf(
  group: MemoryGroup,
  position: Coordinates | null,
  earned: ReadonlySet<number>,
): Reach {
  const locked = group.memories.filter((memory) => memory.locked);
  // A group is unlocked only when nothing in it is locked. One locked memory
  // under a marker still means that marker hides something.
  if (locked.length === 0) {
    return group.memories.some((memory) => earned.has(memory.id)) ? 'stamped' : 'plain';
  }

  if (!position) return 'locked';

  const radius = locked[0].unlock_radius_meters ?? FALLBACK_RADIUS_M;
  const away = metersToNearest(position, locked);
  if (away <= radius) return 'unlockable';
  return away <= radius * WARM_MULTIPLIER ? 'warm' : 'locked';
}

/** Past this, a locked pin draws soft: about twelve minutes on
 *  foot, the distance a pin is still worth setting out for. */
export const NEAR_WALK_M = 1000;

/** Whether a pin is too far to matter yet. Only a locked one, and never
 *  without a position: with nothing to measure from, nothing is far. */
export function isFar(group: MemoryGroup, position: Coordinates | null): boolean {
  const locked = group.memories.filter((memory) => memory.locked);
  if (!position || locked.length === 0) return false;
  return metersToNearest(position, locked) > NEAR_WALK_M;
}

/** How much of the walk is behind you, 0 to 1, for the ring on the sheet.
 *
 *  Full at the radius, because that is where the thing opens. Empty at three
 *  radii, reusing WARM_MULTIPLIER rather than inventing a second idea of
 *  "nearly" - it is already the distance at which a pin stops being too far
 *  and starts being worth walking to, and the two should agree. */
export function approachOf(meters: number | null, radius: number): number {
  if (meters == null || radius <= 0) return 0;
  const far = radius * WARM_MULTIPLIER;
  if (meters >= far) return 0;
  if (meters <= radius) return 1;
  return (far - meters) / (far - radius);
}
