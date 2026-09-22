/** What this device's daily walk looks like: cached locally, authoritative on
 *  the server.
 *
 * One key and not unlocked.ts's index-plus-item scheme: a route is capped at
 * a handful of stops and replaced wholesale once a day, never grown one entry
 * at a time, so there is nothing the sharded scheme would save here.
 */

import AsyncStorage from '@react-native-async-storage/async-storage';

import type { LocatedMemory } from './api.ts';

const KEY = 'memorylane.route.v1';

type StoredRoute = { route_date: string; memories: LocatedMemory[] };

/** The stored route, or null if there isn't one or it isn't today's.
 *
 *  `today` is the device's own local date, used only to decide whether the
 *  cache is worth painting before the network answers - a fresh fetch always
 *  follows and overwrites it with the server's own route_date, so a clock a
 *  few hours off at midnight costs one wrong instant paint, never a wrong
 *  route. */
export async function loadRoute(today: string): Promise<LocatedMemory[] | null> {
  try {
    const raw = await AsyncStorage.getItem(KEY);
    if (!raw) return null;
    const stored = JSON.parse(raw) as StoredRoute;
    return stored.route_date === today ? stored.memories : null;
  } catch {
    return null;
  }
}

export async function saveRoute(route: StoredRoute): Promise<void> {
  try {
    await AsyncStorage.setItem(KEY, JSON.stringify(route));
  } catch {
    // In memory for the rest of this launch, gone on the next one - the same
    // bargain unlocked.ts makes for every write.
  }
}
