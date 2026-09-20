/** This installation's name for itself.
 *
 * Not a user, not an account, not a person: a random UUID the app generates for
 * itself the first time it needs one, and the only thing tying a collection to
 * a phone. The server never issues it, so it can never hand an identifier to a
 * client that did not already have one.
 *
 * It lives in the keychain rather than AsyncStorage, which is the entire point:
 * AsyncStorage goes when the app's data is cleared, and a collection that
 * evaporates with a cache clear is not a collection. The keychain is also the
 * only store here that can outlive a reinstall, though iOS makes no promise
 * about that and this does not depend on it.
 *
 * ponytail: if SecureStore is unavailable the id falls back to AsyncStorage, so
 * unlocking still works and still syncs - it just becomes as fragile as it was
 * before this existed. Failing the unlock instead would trade a durability
 * problem for a broken button.
 */

import AsyncStorage from '@react-native-async-storage/async-storage';
import * as Crypto from 'expo-crypto';
import * as SecureStore from 'expo-secure-store';

const KEY = 'memorylane.device-id.v1';

let cached: string | null = null;

async function readStored(): Promise<string | null> {
  try {
    const secure = await SecureStore.getItemAsync(KEY);
    if (secure) return secure;
  } catch {
    // Simulators, some managed devices, and a locked keychain all land here.
  }
  try {
    return await AsyncStorage.getItem(KEY);
  } catch {
    return null;
  }
}

async function write(id: string): Promise<void> {
  try {
    await SecureStore.setItemAsync(KEY, id);
    return;
  } catch {
    // Fall through to the weaker store rather than losing the id entirely.
  }
  try {
    await AsyncStorage.setItem(KEY, id);
  } catch {
    // In-memory only for this launch. Unlocks still work; they just will not
    // be recognised as this device's next time.
  }
}

export async function deviceId(): Promise<string> {
  if (cached) return cached;

  const stored = await readStored();
  if (stored) {
    cached = stored;
    return stored;
  }

  const fresh = Crypto.randomUUID();
  cached = fresh;
  await write(fresh);
  return fresh;
}
