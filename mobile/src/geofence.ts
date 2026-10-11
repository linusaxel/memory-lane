/** Notify when a locked, walkable memory comes into range - the proximity half
 *  of docs/10-decisions.md#a-streak-and-a-proximity-notification-after-all.
 *  It needs background location, which is why it is opt-in and off by default -
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
import { AppState } from 'react-native';

import { fetchNearby, grantSurprise, type Coordinates, type LocatedMemory } from './api.ts';
import { deviceId } from './device.ts';
import {
  liveSurprise,
  mayNotify,
  maySurprise,
  memoriesToWatch,
  regionsFor,
  type Sent,
  type Surprise,
  walkingPace,
} from './geofenceRegions.ts';
import { loadUnlocked } from './unlocked.ts';

export const GEOFENCE_TASK = 'memory-lane-proximity';
/** Off a walk, the regions follow you: every ~500 m moved re-registers the
 *  locked memories nearest where you are now, so a surprise can find someone
 *  whose own streets are read, not only where the app was last open. */
const MOVED_TASK = 'memory-lane-moved';
const MOVED_METERS = 500;
const AROUND_KM = 2;

const NAMES_KEY = 'memorylane.geofenceNames.v1';
const SENT_KEY = 'memorylane.geofenceSent.v1';
const MODE_KEY = 'memorylane.geofenceMode.v1';
const OPENED_KEY = 'memorylane.lastOpened.v1';
const SURPRISE_KEY = 'memorylane.surprise.v1';

/** On a walk the watch is its stops; off one, the locked memories around you,
 *  any of which may be this week's surprise (docs/10, "A surprise, once a
 *  week"). Stored, because the task can run with the app killed. */
export type WatchMode = 'walk' | 'surprise';

const localDay = (d = new Date()) => `${d.getFullYear()}-${d.getMonth() + 1}-${d.getDate()}`;

/** The app was opened today, so no surprise today. */
export function noteOpened(): void {
  AsyncStorage.setItem(OPENED_KEY, localDay()).catch(() => {});
}

export async function loadSurprise(): Promise<Surprise | null> {
  try {
    const raw = await AsyncStorage.getItem(SURPRISE_KEY);
    return liveSurprise(raw ? (JSON.parse(raw) as Surprise) : null, Date.now());
  } catch {
    return null;
  }
}

type GeofenceTaskData = {
  eventType: Location.GeofencingEventType;
  region: Location.LocationRegion;
};

/** One event at a time: entering a cluster fires several at once, and each has
 *  to see what the one before it stored. */
let queue = Promise.resolve();

TaskManager.defineTask<GeofenceTaskData>(GEOFENCE_TASK, ({ data, error }) => {
  if (error || !data) return Promise.resolve();
  if (data.eventType !== Location.GeofencingEventType.Enter) return Promise.resolve();
  queue = queue.then(() => onEnter(data.region.identifier ?? '')).catch(() => {});
  return queue;
});

TaskManager.defineTask<{ locations: Location.LocationObject[] }>(MOVED_TASK, ({ data, error }) => {
  const fix = data?.locations?.at(-1);
  if (error || !fix) return Promise.resolve();
  queue = queue.then(() => onMoved(fix)).catch(() => {});
  return queue;
});

async function onMoved(fix: Location.LocationObject) {
  // Open, the app's own watch already follows `nearby`.
  if (AppState.currentState === 'active') return;
  if ((await AsyncStorage.getItem(MODE_KEY).catch(() => null)) !== 'surprise') return;
  const at = { lat: fix.coords.latitude, lng: fix.coords.longitude };
  const [around, opened] = await Promise.all([
    fetchNearby(at, AROUND_KM, await deviceId()),
    loadUnlocked(),
  ]);
  await startWatching(
    around.filter((m) => !(m.id in opened)),
    'surprise',
    at,
  );
}

async function onEnter(id: string) {
  const mode = await AsyncStorage.getItem(MODE_KEY).catch(() => null);
  if (mode === 'surprise') return onSurprise(id);
  let sent: Sent = { last: 0, byId: {} };
  try {
    const raw = await AsyncStorage.getItem(SENT_KEY);
    if (raw) sent = JSON.parse(raw) as Sent;
  } catch {
    // Nothing stored reads as nothing sent.
  }
  const next = mayNotify(id, Date.now(), sent);
  if (!next) return;
  await AsyncStorage.setItem(SENT_KEY, JSON.stringify(next)).catch(() => {});

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
      data: { memoryId: Number(id) },
    },
    trigger: null,
  });
}

/** Off a walk: ask the server for this week's surprise, and say so only if it
 *  grants one. Silent otherwise, which is most of the time. */
async function onSurprise(id: string) {
  const lastOpened = await AsyncStorage.getItem(OPENED_KEY).catch(() => null);
  if (!maySurprise(lastOpened, localDay()) || (await loadSurprise())) return;
  const fix = await Location.getLastKnownPositionAsync().catch(() => null);
  if (!fix || !walkingPace(fix.coords.speed)) return;
  const at = { lat: fix.coords.latitude, lng: fix.coords.longitude };
  const granted = await grantSurprise(Number(id), at, await deviceId());
  if (!granted) return;
  const surprise: Surprise = {
    memoryId: granted.memory_id,
    place: granted.place,
    expiresAt: granted.expires_at,
  };
  await AsyncStorage.setItem(SURPRISE_KEY, JSON.stringify(surprise)).catch(() => {});
  await Notifications.scheduleNotificationAsync({
    content: {
      title: 'A story is open nearby',
      body: `Something happened at ${granted.place}. Walk over in the next 30 minutes to read it.`,
      data: { memoryId: granted.memory_id },
    },
    trigger: null,
  });
}

/** One change to the watch at a time: App's effect calls again before the
 *  last call is done, and two stops of one task race to "Task … not found". */
let watching: Promise<unknown> = Promise.resolve();
function inTurn<T>(run: () => Promise<T>): Promise<T> {
  const next = watching.then(run);
  watching = next.catch(() => {});
  return next;
}

/** Starts (or restarts, replacing the region list) watching the given
 *  memories. Requests background location and notification permission if
 *  they are not already granted; returns false without asking for anything
 *  if there is nothing to watch or foreground permission was never granted -
 *  background permission means nothing without it. */
export function startWatching(
  memories: LocatedMemory[],
  mode: WatchMode = 'walk',
  from: Coordinates | null = null,
): Promise<boolean> {
  return inTurn(() => watch(memories, mode, from));
}

export function stopWatching(): Promise<void> {
  return inTurn(unwatch);
}

async function watch(
  memories: LocatedMemory[],
  mode: WatchMode,
  from: Coordinates | null,
): Promise<boolean> {
  const watched = memoriesToWatch(memories, from);
  if (watched.length === 0) {
    await unwatch();
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

  await AsyncStorage.setItem(MODE_KEY, mode).catch(() => {});
  await Location.startGeofencingAsync(GEOFENCE_TASK, regionsFor(memories, from));
  if (mode === 'surprise') await followMoves();
  else await stopFollowing();
  return true;
}

// ponytail: coarse background updates stand in for iOS's significant-change
// service, which expo-location does not expose; swap it in if battery shows.
async function followMoves() {
  if (await Location.hasStartedLocationUpdatesAsync(MOVED_TASK).catch(() => false)) return;
  await Location.startLocationUpdatesAsync(MOVED_TASK, {
    accuracy: Location.Accuracy.Low,
    distanceInterval: MOVED_METERS,
    deferredUpdatesDistance: MOVED_METERS,
    pausesUpdatesAutomatically: true,
    showsBackgroundLocationIndicator: false,
  });
}

async function stopFollowing() {
  if (await Location.hasStartedLocationUpdatesAsync(MOVED_TASK).catch(() => false))
    await Location.stopLocationUpdatesAsync(MOVED_TASK);
}

async function unwatch(): Promise<void> {
  const started = await Location.hasStartedGeofencingAsync(GEOFENCE_TASK).catch(() => false);
  if (started) await Location.stopGeofencingAsync(GEOFENCE_TASK);
  await stopFollowing();
}
