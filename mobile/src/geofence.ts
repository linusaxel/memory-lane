/** Notify when a locked, walkable memory comes into range - the proximity half
 *  of docs/10-decisions.md#a-streak-and-a-proximity-notification-after-all.
 *  The streak half (F27) needed nothing new; this half
 *  needs background location, which is why it is opt-in and off by default -
 *  Settings.tsx's toggle is the only thing that starts it.
 *
 *  Region selection lives in geofenceRegions.ts, which has no native imports
 *  and so can be unit-tested; this file is the wrapper around actual
 *  `expo-location`/`expo-task-manager`/`expo-notifications` calls, which
 *  cannot run outside the app.
 *
 *  A background task cannot read React state, and on iOS/Android it can run
 *  after the app itself was killed, which starts the JS bundle fresh with no
 *  memory of what was on screen. So the place name for each watched region is
 *  written to AsyncStorage alongside the geofence call, and the task handler
 *  below reads it back by the region's identifier rather than closing over
 *  anything.
 */

import AsyncStorage from '@react-native-async-storage/async-storage';
import * as Location from 'expo-location';
import * as Notifications from 'expo-notifications';
import * as TaskManager from 'expo-task-manager';

import type { LocatedMemory } from './api.ts';
import { memoriesToWatch, regionsFor } from './geofenceRegions.ts';

export const GEOFENCE_TASK = 'memory-lane-proximity';

const NAMES_KEY = 'memorylane.geofenceNames.v1';

type GeofenceTaskData = {
  eventType: Location.GeofencingEventType;
  region: Location.LocationRegion;
};

TaskManager.defineTask<GeofenceTaskData>(GEOFENCE_TASK, async ({ data, error }) => {
  if (error || !data) return;
  if (data.eventType !== Location.GeofencingEventType.Enter) return;

  const id = data.region.identifier;
  let name = 'a place';
  try {
    const raw = await AsyncStorage.getItem(NAMES_KEY);
    const names = raw ? (JSON.parse(raw) as Record<string, string>) : {};
    name = (id && names[id]) || name;
  } catch {
    // No name to show - the notification still says something true.
  }

  await Notifications.scheduleNotificationAsync({
    content: {
      title: 'A memory is nearby',
      body: `Something happened near ${name}. Walk over and read it.`,
    },
    trigger: null,
  });
});

/** Starts (or restarts, replacing the region list) watching the given
 *  memories. Requests background location and notification permission if
 *  they are not already granted; returns false without asking for anything
 *  if there is nothing to watch or foreground permission was never granted -
 *  background permission means nothing without it. */
export async function startWatching(memories: LocatedMemory[]): Promise<boolean> {
  const watched = memoriesToWatch(memories);
  if (watched.length === 0) {
    await stopWatching();
    return false;
  }

  const foreground = await Location.getForegroundPermissionsAsync();
  if (foreground.status !== 'granted') return false;

  const background = await Location.requestBackgroundPermissionsAsync();
  if (background.status !== 'granted') return false;

  await Notifications.requestPermissionsAsync();

  try {
    await AsyncStorage.setItem(
      NAMES_KEY,
      JSON.stringify(Object.fromEntries(watched.map((m) => [String(m.id), m.place.name]))),
    );
  } catch {
    // The geofence still fires; the notification just falls back to "a place".
  }

  await Location.startGeofencingAsync(GEOFENCE_TASK, regionsFor(memories));
  return true;
}

export async function stopWatching(): Promise<void> {
  const started = await Location.hasStartedGeofencingAsync(GEOFENCE_TASK).catch(() => false);
  if (started) await Location.stopGeofencingAsync(GEOFENCE_TASK);
}
