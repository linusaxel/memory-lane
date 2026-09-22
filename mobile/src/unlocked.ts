/** What this device remembers between launches.
 *
 * Memories it has earned, mostly. The server re-locks you the moment you walk
 * away, which is correct of the server and wrong of the product: re-locking
 * something somebody stood in the rain for punishes them for leaving. So the
 * unlocked copy lives here, and the map merges it over whatever the API returns.
 *
 * Stored one memory per key, not as a single growing blob: recording one more
 * unlock used to mean rewriting everything this device had ever earned, an
 * O(n) disk write that got slower the longer the collection got. INDEX_KEY
 * holds only the ids, cheap to rewrite, and each memory lives under its own
 * ITEM_PREFIX key - a normal unlock or edit touches exactly one item key and,
 * usually, nothing else.
 */

import AsyncStorage from '@react-native-async-storage/async-storage';

import type { LocatedMemory } from './api.ts';

/** Pre-migration layout: everything ever earned, as one JSON object under one
 *  key. Read once, the first launch after this update, then dropped - see
 *  migrateFromBlob. */
const BLOB_KEY = 'memorylane.unlocked.v1';
const INDEX_KEY = 'memorylane.unlocked.index.v1';
const ITEM_PREFIX = 'memorylane.unlocked.item.';
const PRIMER_KEY = 'memorylane.primer-dismissed.v1';

/** Recorded locally because the server's copy carries the date but the local
 *  one is what renders offline. */
export type UnlockedMemory = LocatedMemory & { unlocked_at: number };

export type Unlocked = Record<number, UnlockedMemory>;

/** Newest first: what you just earned is what you want to see. */
export function inUnlockOrder(unlocked: Unlocked): UnlockedMemory[] {
  return Object.values(unlocked).sort((a, b) => (b.unlocked_at ?? 0) - (a.unlocked_at ?? 0));
}

async function readIndex(): Promise<number[]> {
  try {
    const raw = await AsyncStorage.getItem(INDEX_KEY);
    return raw ? (JSON.parse(raw) as number[]) : [];
  } catch {
    return [];
  }
}

async function writeIndex(ids: number[]): Promise<void> {
  try {
    await AsyncStorage.setItem(INDEX_KEY, JSON.stringify(ids));
  } catch {
    // Same bargain as every write below: in memory now, gone next launch.
  }
}

async function readItems(ids: number[]): Promise<Unlocked> {
  if (ids.length === 0) return {};
  const pairs = await AsyncStorage.multiGet(ids.map((id) => ITEM_PREFIX + id));
  const out: Unlocked = {};
  for (const [key, raw] of pairs) {
    if (!raw) continue;
    try {
      out[Number(key.slice(ITEM_PREFIX.length))] = JSON.parse(raw) as UnlockedMemory;
    } catch {
      // One corrupt item is dropped, not fatal to the rest of the collection.
    }
  }
  return out;
}

/** One-time move off BLOB_KEY: every entry gets its own item key plus a fresh
 *  index, then the blob is removed. Nothing reads BLOB_KEY again once this
 *  succeeds - a failure partway leaves it in place, so the next launch just
 *  tries the migration again. */
async function migrateFromBlob(): Promise<Unlocked> {
  let raw: string | null;
  try {
    raw = await AsyncStorage.getItem(BLOB_KEY);
  } catch {
    return {};
  }
  if (!raw) return {};

  let blob: Unlocked;
  try {
    blob = JSON.parse(raw) as Unlocked;
  } catch {
    return {};
  }

  const ids = Object.keys(blob).map(Number);
  try {
    await AsyncStorage.multiSet(ids.map((id) => [ITEM_PREFIX + id, JSON.stringify(blob[id])]));
    await writeIndex(ids);
    await AsyncStorage.removeItem(BLOB_KEY);
  } catch {
    // Left mid-migration on purpose; see above.
  }
  return blob;
}

export async function loadUnlocked(): Promise<Unlocked> {
  try {
    const raw = await AsyncStorage.getItem(INDEX_KEY);
    if (raw !== null) return await readItems(JSON.parse(raw) as number[]);
  } catch {
    // A cold start with unreadable storage is an empty map, not a crash.
    return {};
  }
  return migrateFromBlob();
}

/** Returns the new map even if the write fails - losing the unlock you just
 *  earned because the disk is full is worse than losing it on next launch. */
export async function rememberUnlocked(
  current: Unlocked,
  memory: LocatedMemory,
): Promise<Unlocked> {
  const item: UnlockedMemory = { ...memory, unlocked_at: Date.now() };
  const next = { ...current, [memory.id]: item };
  try {
    await AsyncStorage.setItem(ITEM_PREFIX + memory.id, JSON.stringify(item));
    // The index only needs a rewrite when this id is new to it - an unlock
    // already on the index is just a bigger item write, not a bigger one.
    if (!(memory.id in current)) await writeIndex([...(await readIndex()), memory.id]);
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

/** Refresh a memory already in the collection - an edit, typically - without
 *  disturbing when it was earned. `rememberUnlocked` resets `unlocked_at` to
 *  now on every call, which is correct for a fresh unlock and wrong here: it
 *  would bump an edited memory to the top of the Unlocked tab as if it had
 *  just been earned again. Never touches the index - the id was already on it
 *  the moment it entered `current`. */
export async function updateUnlocked(
  current: Unlocked,
  memory: LocatedMemory,
): Promise<Unlocked> {
  const existing = current[memory.id];
  const item: UnlockedMemory = { ...memory, unlocked_at: existing?.unlocked_at ?? Date.now() };
  const next = { ...current, [memory.id]: item };
  try {
    await AsyncStorage.setItem(ITEM_PREFIX + memory.id, JSON.stringify(item));
    if (!existing) await writeIndex([...(await readIndex()), memory.id]);
  } catch {
    // Same bargain as rememberUnlocked: in memory now, gone next launch.
  }
  return next;
}

/** Drop one entry, for after its author deletes it. */
export async function forgetUnlocked(current: Unlocked, id: number): Promise<Unlocked> {
  const next = { ...current };
  delete next[id];
  try {
    await AsyncStorage.removeItem(ITEM_PREFIX + id);
    await writeIndex((await readIndex()).filter((existing) => existing !== id));
  } catch {
    // Same bargain as rememberUnlocked.
  }
  return next;
}

/** Fold the server's copy of the collection into this device's.
 *
 * Every memory here lives under its own key, so this can run at launch
 * alongside loadUnlocked without the two racing to overwrite each other the
 * way two competing writes of one blob would - they touch disjoint keys, or
 * write the same id to the same value.
 *
 * Local wins on conflict: it has an unlocked_at from the moment it was earned,
 * and the server's row may have been written by a retry. Neither copy is ever
 * dropped - the point of this is that nothing you walked to disappears.
 */
export async function mergeUnlocked(fromServer: LocatedMemory[]): Promise<Unlocked> {
  const current = await loadUnlocked();
  const merged: Unlocked = { ...current };
  const newIds: number[] = [];
  const writes: [string, string][] = [];

  for (const memory of fromServer) {
    if (merged[memory.id]) continue;
    const item: UnlockedMemory = { ...memory, unlocked_at: Date.now() };
    merged[memory.id] = item;
    newIds.push(memory.id);
    writes.push([ITEM_PREFIX + memory.id, JSON.stringify(item)]);
  }

  if (writes.length > 0) {
    try {
      await AsyncStorage.multiSet(writes);
      await writeIndex([...(await readIndex()), ...newIds]);
    } catch {
      // Same bargain as rememberUnlocked: in memory now, gone next launch.
    }
  }
  return merged;
}
