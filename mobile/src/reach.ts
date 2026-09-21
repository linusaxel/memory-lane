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

/** The ink ladder, from nothing-to-earn to earned. `plain` and `stamped` are
 *  both unlocked; only the local store knows which one was walked for. */
export type Reach = 'plain' | 'stamped' | 'warm' | 'locked' | 'unlockable';

/** Only used if a memory somehow arrives without the server's radius. */
export const FALLBACK_RADIUS_M = 150;

/** How much past the gate still reads as "nearly". Three radii is a few
 *  minutes' walk at the 150m gate, which is the distance at which turning
 *  around is still a decision rather than a trek. */
export const WARM_MULTIPLIER = 3;

/**
 * Past this, "the nearest locked memory is 6,181 km away" is not a hint, it is
 * a fact about the corpus, and the empty-state card says it better. The pill
 * exists to start a walk; 30km is the outer edge of somewhere you might go
 * today.
 */
export const HINT_RANGE_M = 30_000;

/** Shut by a date rather than by distance, so no amount of walking opens it.
 *
 *  The distinction has to exist here and not only in the sheet, because three
 *  separate things ask "can this be opened from where I am standing": the pin's
 *  colour, the within-reach banner's count, and the walk hint. A sealed memory
 *  answered yes to all three - it is `locked`, and it was 128m away. The pin
 *  wore the seal colour, the banner counted it, and because `nearestLocked`
 *  returns null the moment anything is `unlockable`, one sealed memory could
 *  also suppress the hint pointing at a pin somebody genuinely could walk to.
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

/** The closest thing still shut, so a map of padlocks can answer "where do I
 *  go" and not only "you cannot read this". Null when something is already in
 *  reach, because then there is nothing to walk to. */
export function nearestLocked(
  groups: MemoryGroup[],
  position: Coordinates | null,
  earned: ReadonlySet<number>,
): { group: MemoryGroup; meters: number } | null {
  if (!position) return null;

  let best: { group: MemoryGroup; meters: number } | null = null;
  for (const group of groups) {
    const reach = reachOf(group, position, earned);
    if (reach === 'unlockable') return null;
    // Neither is somewhere to walk to, and a stamped pin counted as the nearest
    // lock would read "Nearest locked - 40 m" about something already read.
    if (reach === 'plain' || reach === 'stamped') continue;

    // Same rule as above: a date is not a distance, so a sealed memory is not
    // somewhere to walk to and must not be offered as one.
    const walkable = group.memories.filter((memory) => memory.locked && !isSealed(memory));
    if (walkable.length === 0) continue;

    const meters = metersToNearest(position, walkable);
    if (!best || meters < best.meters) best = { group, meters };
  }
  return best && best.meters <= HINT_RANGE_M ? best : null;
}
