/** Which locked memories are worth a background geofence, and the region each
 *  one becomes. Pure and native-free on purpose - see geofence.ts, which wraps
 *  this in the actual `expo-location`/`expo-task-manager` calls and is not
 *  unit-testable the same way those modules cannot be loaded outside the app.
 */

import type { Coordinates, LocatedMemory } from './api.ts';
import { FALLBACK_RADIUS_M, isSealed } from './reach.ts';

/** iOS refuses to monitor more than 20 regions per app; there is no reason to
 *  ask Android for more than that either. */
const MAX_REGIONS = 20;

export type Region = {
  identifier: string;
  latitude: number;
  longitude: number;
  radius: number;
  notifyOnEnter: true;
  notifyOnExit: false;
};

/** Locked and not sealed - a time lock does not open by walking there, so
 *  there is nothing a notification should invite anyone to do about it. */
export function memoriesToWatch(memories: LocatedMemory[]): LocatedMemory[] {
  return memories.filter((m) => m.locked && !isSealed(m)).slice(0, MAX_REGIONS);
}

export function regionsFor(memories: LocatedMemory[]): Region[] {
  return memoriesToWatch(memories).map((m) => ({
    identifier: String(m.id),
    latitude: (m.place.coordinates as Coordinates).lat,
    longitude: (m.place.coordinates as Coordinates).lng,
    radius: m.unlock_radius_meters ?? FALLBACK_RADIUS_M,
    notifyOnEnter: true,
    notifyOnExit: false,
  }));
}
