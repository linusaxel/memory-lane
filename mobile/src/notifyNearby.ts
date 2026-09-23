/** Whether this device has opted into the proximity notification (geofence.ts).
 *  Off until chosen - background location is the one permission this app asks
 *  for beyond what showing the map needs, so it is never assumed. */

import AsyncStorage from '@react-native-async-storage/async-storage';

const KEY = 'memorylane.notifyNearby.v1';

export async function loadNotifyNearby(): Promise<boolean> {
  try {
    return (await AsyncStorage.getItem(KEY)) === 'true';
  } catch {
    return false;
  }
}

export async function saveNotifyNearby(on: boolean): Promise<void> {
  try {
    await AsyncStorage.setItem(KEY, on ? 'true' : 'false');
  } catch {
    // Local convenience only - worst case it asks again next launch.
  }
}
