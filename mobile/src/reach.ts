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
export const FALLBACK_RADIUS_M = 150;

/** How much past the gate still reads as "nearly". Three radii is a few
 *  minutes' walk at the 150m gate, which is the distance at which turning
 *  around is still a decision rather than a trek. */
export const WARM_MULTIPLIER = 3;

/** Shut by a date rather than by distance, so no amount of walking opens it.
 *
 *  The distinction has to exist here and not only in the sheet, because the
 *  pin's colour and the "at a stop" pill both ask "can this be opened from
 *  where I am standing". A sealed memory is `locked`, and can be 128m away.
 *
 *  See F23 in docs/08-ux-flows.md. */
export function isSealed(memory: LocatedMemory): boolean {
  return memory.opens_at != null;
}

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

  // Distance only has an opinion about the ones distance can open. A group with
  // nothing but sealed memories under it stays `locked`: shut, and honest about
  // it, rather than amber for a walk that would achieve nothing.
  // ponytail: a seal could earn its own mark on the map instead of borrowing
  // the out-of-reach one. Grey is true today and costs no new visual language.
  const walkable = locked.filter((memory) => !isSealed(memory));
  if (walkable.length === 0 || !position) return 'locked';

  const radius = walkable[0].unlock_radius_meters ?? FALLBACK_RADIUS_M;
  const away = metersToNearest(position, walkable);
  if (away <= radius) return 'unlockable';
  return away <= radius * WARM_MULTIPLIER ? 'warm' : 'locked';
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
