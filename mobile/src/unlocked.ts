/** Memories this device has earned.
 *
 * The server re-locks you the moment you walk away, which is correct of the
 * server and wrong of the product: re-locking something somebody stood in the
 * rain for punishes them for leaving. So the unlocked copy lives on the device,
 * and the map merges it over whatever the API returns.
 */

import AsyncStorage from '@react-native-async-storage/async-storage';

import type { LocatedMemory } from './api.ts';

const KEY = 'memorylane.unlocked.v1';

export type Unlocked = Record<number, LocatedMemory>;

export async function loadUnlocked(): Promise<Unlocked> {
  try {
    const raw = await AsyncStorage.getItem(KEY);
    return raw ? (JSON.parse(raw) as Unlocked) : {};
  } catch {
    // A cold start with unreadable storage is an empty map, not a crash.
    return {};
  }
}

/** Returns the new map even if the write fails - losing the unlock you just
 *  earned because the disk is full is worse than losing it on next launch. */
export async function rememberUnlocked(
  current: Unlocked,
  memory: LocatedMemory,
): Promise<Unlocked> {
  const next = { ...current, [memory.id]: memory };
  try {
    await AsyncStorage.setItem(KEY, JSON.stringify(next));
  } catch {
    // Ignored on purpose; see above.
  }
  return next;
}
