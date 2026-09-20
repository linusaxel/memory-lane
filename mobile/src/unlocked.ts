/** What this device remembers between launches.
 *
 * Memories it has earned, mostly. The server re-locks you the moment you walk
 * away, which is correct of the server and wrong of the product: re-locking
 * something somebody stood in the rain for punishes them for leaving. So the
 * unlocked copy lives here, and the map merges it over whatever the API returns.
 */

import AsyncStorage from '@react-native-async-storage/async-storage';

import type { LocatedMemory } from './api.ts';

const KEY = 'memorylane.unlocked.v1';
const PRIMER_KEY = 'memorylane.primer-dismissed.v1';

/** Recorded locally because the server's copy carries the date but the local
 *  one is what renders offline. */
export type UnlockedMemory = LocatedMemory & { unlocked_at: number };

export type Unlocked = Record<number, UnlockedMemory>;

/** Newest first: what you just earned is what you want to see. */
export function inUnlockOrder(unlocked: Unlocked): UnlockedMemory[] {
  return Object.values(unlocked).sort((a, b) => (b.unlocked_at ?? 0) - (a.unlocked_at ?? 0));
}

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
  const next = { ...current, [memory.id]: { ...memory, unlocked_at: Date.now() } };
  try {
    await AsyncStorage.setItem(KEY, JSON.stringify(next));
  } catch {
    // Ignored on purpose; see above.
  }
  return next;
}

/** Whether they have already waved the location primer away.
 *
 * Re-asking on every launch is how an app teaches people to dismiss without
 * reading, and the second ask is worth less than the first. "Turn on location"
 * stays on the map for whenever they change their mind.
 */
export async function primerWasDismissed(): Promise<boolean> {
  try {
    return (await AsyncStorage.getItem(PRIMER_KEY)) === '1';
  } catch {
    return false;
  }
}

export async function rememberPrimerDismissed(): Promise<void> {
  try {
    await AsyncStorage.setItem(PRIMER_KEY, '1');
  } catch {
    // Being asked once more is a smaller harm than a crash on a full disk.
  }
}

/** Fold the server's copy of the collection into this device's.
 *
 * Read-modify-write against storage rather than against React state, because
 * this runs at launch alongside loadUnlocked and the two would otherwise race
 * to overwrite each other.
 *
 * Local wins on conflict: it has an unlocked_at from the moment it was earned,
 * and the server's row may have been written by a retry. Neither copy is ever
 * dropped - the point of this is that nothing you walked to disappears.
 */
export async function mergeUnlocked(fromServer: LocatedMemory[]): Promise<Unlocked> {
  const current = await loadUnlocked();
  const merged: Unlocked = { ...current };

  for (const memory of fromServer) {
    if (!merged[memory.id]) merged[memory.id] = { ...memory, unlocked_at: Date.now() };
  }

  try {
    await AsyncStorage.setItem(KEY, JSON.stringify(merged));
  } catch {
    // Same bargain as rememberUnlocked: in memory now, gone next launch.
  }
  return merged;
}
