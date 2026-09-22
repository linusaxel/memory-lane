/** Which memory ids this device has hearted, so the button starts filled on
 *  relaunch.
 *
 *  One AsyncStorage key holding a small Set, like route.ts and unlike
 *  unlocked.ts's sharded scheme - hearting only needs to remember membership,
 *  not cache a full memory object per id. A local convenience only: the
 *  server's memory_hearts row is the durable fact, and re-hearting is a
 *  harmless no-op either way, so losing this on reinstall costs nothing but
 *  a reset button state.
 */

import AsyncStorage from '@react-native-async-storage/async-storage';

const KEY = 'memorylane.hearted.v1';

export async function loadHearted(): Promise<Set<number>> {
  try {
    const raw = await AsyncStorage.getItem(KEY);
    return raw ? new Set(JSON.parse(raw) as number[]) : new Set();
  } catch {
    return new Set();
  }
}

export async function rememberHearted(current: Set<number>, id: number): Promise<Set<number>> {
  const next = new Set(current).add(id);
  try {
    await AsyncStorage.setItem(KEY, JSON.stringify([...next]));
  } catch {
    // In memory for the rest of this launch, gone on the next one - the same
    // bargain unlocked.ts and route.ts make for every write.
  }
  return next;
}
