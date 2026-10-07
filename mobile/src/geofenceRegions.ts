/** Which locked memories are worth a background geofence, and the region each
 *  one becomes. Pure and native-free on purpose - see geofence.ts, which wraps
 *  this in the actual `expo-location`/`expo-task-manager` calls and is not
 *  unit-testable the same way those modules cannot be loaded outside the app.
 */

import type { Coordinates, LocatedMemory } from './api.ts';
import { FALLBACK_RADIUS_M } from './reach.ts';
import { metersBetween } from './region.ts';

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

const away = (m: LocatedMemory, from: Coordinates) => {
  const at = m.place.coordinates as Coordinates;
  return metersBetween(from.lat, from.lng, at.lat, at.lng);
};

/** Locked: an open memory is nothing to walk to. The nearest to `from` first,
 *  when there is a `from`: the server lists nearby by story, not distance. */
export function memoriesToWatch(
  memories: LocatedMemory[],
  from: Coordinates | null = null,
): LocatedMemory[] {
  const locked = memories.filter((m) => m.locked);
  if (from) locked.sort((a, b) => away(a, from) - away(b, from));
  return locked.slice(0, MAX_REGIONS);
}

export function regionsFor(memories: LocatedMemory[], from: Coordinates | null = null): Region[] {
  return memoriesToWatch(memories, from).map((m) => ({
    identifier: String(m.id),
    latitude: (m.place.coordinates as Coordinates).lat,
    longitude: (m.place.coordinates as Coordinates).lng,
    radius: Math.max(m.unlock_radius_meters ?? FALLBACK_RADIUS_M, MIN_RADIUS_M),
    notifyOnEnter: true,
    notifyOnExit: false,
  }));
}

/** A boundary walked along fires Enter over and over, and a cluster of stops
 *  fires one each, so an alert is let through at most once a day per memory
 *  and once per half hour in all. */
const SAME_MEMORY_MS = 24 * 60 * 60 * 1000;
const ANY_MEMORY_MS = 30 * 60 * 1000;

export type Sent = { last: number; byId: Record<string, number> };

/** The record to store if memory `id` may notify now, or null if it may not. */
export function mayNotify(id: string, now: number, sent: Sent): Sent | null {
  if (now - sent.last < ANY_MEMORY_MS) return null;
  if (now - (sent.byId[id] ?? -Infinity) < SAME_MEMORY_MS) return null;
  const byId = Object.fromEntries(
    Object.entries(sent.byId).filter(([, at]) => now - at < SAME_MEMORY_MS),
  );
  return { last: now, byId: { ...byId, [id]: now } };
}

/** An unexpired grant from POST /v1/surprise: one memory open off a walk
 *  (docs/10-decisions.md#a-surprise-once-a-week). */
export type Surprise = { memoryId: number; place: string; expiresAt: string };

/** Only on a day the app was not opened: a surprise is for when you are not
 *  looking. The once-a-week rule is the server's. */
export const maySurprise = (lastOpened: string | null, today: string) => lastOpened !== today;

/** A surprise is for someone on foot: a bike is a kilometre past a 100 m
 *  region before the notification lands, and it would spend the week. iOS
 *  reports -1, and some fixes null, when the speed is unknown: let those by. */
const SURPRISE_MAX_SPEED = 2.5; // m/s, a brisk walk

export const walkingPace = (speed: number | null | undefined) =>
  speed == null || speed < 0 || speed <= SURPRISE_MAX_SPEED;

export const liveSurprise = (surprise: Surprise | null, now: number): Surprise | null =>
  surprise && Date.parse(surprise.expiresAt) > now ? surprise : null;
