/** What this device's daily walk looks like: cached locally, authoritative on
 *  the server.
 *
 * One key and not unlocked.ts's index-plus-item scheme: a route is capped at
 * a handful of stops and replaced wholesale once a day, never grown one entry
 * at a time, so there is nothing the sharded scheme would save here.
 */

import AsyncStorage from '@react-native-async-storage/async-storage';

import type { Coordinates, LocatedMemory, WalkAsk, WalkedRoute } from './api.ts';

const KEY = 'memorylane.route.v1';

/** `start` is where this device stood when it asked for today's route: where a
 *  loop comes back to. It is kept here and never sent anywhere again - the
 *  server stores no location (docs/10-decisions.md § Routes). Optional
 *  because a route cached before loops existed has none. `end` is where a
 *  one-way walk finishes, when one was tapped: kept the same way. */
export type StoredRoute = {
  route_date: string;
  memories: LocatedMemory[];
  loop?: boolean;
  start?: Coordinates;
  end?: Coordinates;
  legs?: Coordinates[][] | null;
};

/** The stored route, or null if there isn't one or it isn't today's.
 *
 *  `today` is the device's own local date, used only to decide whether the
 *  cache is worth painting before the network answers - a fresh fetch always
 *  follows and overwrites it with the server's own route_date, so a clock a
 *  few hours off at midnight costs one wrong instant paint, never a wrong
 *  route. */
export async function loadRoute(today: string): Promise<StoredRoute | null> {
  try {
    const raw = await AsyncStorage.getItem(KEY);
    if (!raw) return null;
    const stored = JSON.parse(raw) as StoredRoute;
    return stored.route_date === today ? stored : null;
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

/** "End walk": nothing cached to paint on the next launch. */
export async function clearRoute(): Promise<void> {
  await AsyncStorage.removeItem(KEY).catch(() => {});
}

const WALKED_KEY = 'memorylane.walked.v1';

/** The last list of walks the server gave, so the journal reads on the train
 *  (F16). Replaced wholesale on every successful fetch. */
export async function loadWalked(): Promise<WalkedRoute[]> {
  try {
    const raw = await AsyncStorage.getItem(WALKED_KEY);
    return raw ? (JSON.parse(raw) as WalkedRoute[]) : [];
  } catch {
    return [];
  }
}

export async function saveWalked(walks: WalkedRoute[]): Promise<void> {
  try {
    await AsyncStorage.setItem(WALKED_KEY, JSON.stringify(walks));
  } catch {
    // Same bargain as saveRoute.
  }
}

const CHOICES_KEY = 'memorylane.walk-choices.v1';

/** A subscriber's Customize, themes and an era: kept on this phone, and sent
 *  with every plan. Not the loop or the end, which are asked for per walk. */
export type WalkChoices = Pick<WalkAsk, 'themes' | 'from' | 'until'>;

/** The eras a walk can lean towards, split where the dated memories fall
 *  about evenly; `until` is exclusive. */
export const ERAS: { label: string; from: number | null; until: number | null }[] = [
  { label: 'Any time', from: null, until: null },
  { label: 'Before 1800', from: null, until: 1800 },
  { label: '1800–1945', from: 1800, until: 1945 },
  { label: 'Since 1945', from: 1945, until: null },
];

export async function loadChoices(): Promise<WalkChoices | null> {
  try {
    const raw = await AsyncStorage.getItem(CHOICES_KEY);
    if (!raw) return null;
    const kept = JSON.parse(raw) as WalkChoices;
    // A range kept from before the eras, which no chip shows, is let go.
    return ERAS.some((e) => e.from === kept.from && e.until === kept.until)
      ? kept
      : { ...kept, from: null, until: null };
  } catch {
    return null;
  }
}

export async function saveChoices(choices: WalkChoices): Promise<void> {
  await AsyncStorage.setItem(CHOICES_KEY, JSON.stringify(choices)).catch(() => {});
}
