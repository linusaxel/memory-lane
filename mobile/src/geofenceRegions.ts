/** Which locked memories are worth a background geofence, and the region each
 *  one becomes. Pure and native-free on purpose - see geofence.ts, which wraps
 *  this in the actual `expo-location`/`expo-task-manager` calls and is not
 *  unit-testable the same way those modules cannot be loaded outside the app.
 */

import type { Coordinates, LocatedMemory } from './api.ts';
import { FALLBACK_RADIUS_M } from './reach.ts';

/** iOS refuses to monitor more than 20 regions per app; there is no reason to
 *  ask Android for more than that either. */
const MAX_REGIONS = 20;

/** iOS does not reliably fire a region smaller than about 100 m, and the gate
 *  is far smaller than that. The notification says "you are near"; the last
 *  metres are the map's job. */
const MIN_RADIUS_M = 100;

export type Region = {
  identifier: string;
  latitude: number;
  longitude: number;
  radius: number;
  notifyOnEnter: true;
  notifyOnExit: false;
};

/** Locked: an open memory is nothing to walk to. */
export function memoriesToWatch(memories: LocatedMemory[]): LocatedMemory[] {
  return memories.filter((m) => m.locked).slice(0, MAX_REGIONS);
}

export function regionsFor(memories: LocatedMemory[]): Region[] {
  return memoriesToWatch(memories).map((m) => ({
    identifier: String(m.id),
    latitude: (m.place.coordinates as Coordinates).lat,
    longitude: (m.place.coordinates as Coordinates).lng,
    radius: Math.max(m.unlock_radius_meters ?? FALLBACK_RADIUS_M, MIN_RADIUS_M),
    notifyOnEnter: true,
    notifyOnExit: false,
  }));
}
