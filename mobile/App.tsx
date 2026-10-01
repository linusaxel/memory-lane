import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import {
  AppState,
  Dimensions,
  Linking,
  Platform,
  Pressable,
  StyleSheet,
  Text,
  View,
  useColorScheme,
} from 'react-native';
import MapView, { Circle, Marker } from 'react-native-maps';
import * as Haptics from 'expo-haptics';
import * as Location from 'expo-location';
import * as Notifications from 'expo-notifications';
import * as SplashScreen from 'expo-splash-screen';
import { StatusBar } from 'expo-status-bar';
import { SafeAreaProvider } from 'react-native-safe-area-context';

import {
  acceptRoute,
  blockUser,
  devSteps,
  endRoute,
  fetchMine,
  fetchNearby,
  fetchProfile,
  fetchTodaysRoute,
  fetchUnlocked,
  heartMemory,
  unheartMemory,
  outOfSteps,
  previewRoute,
  reportMemory,
  saveDisplayName,
  unlockMemory,
  walkHereRefusal,
  wasRefused,
  type Coordinates,
  type LocatedMemory,
  type Profile,
  type TodaysRoute,
  type WalkAsk,
} from './src/api.ts';
import { CLUSTER_SPAN_M, groupByLocation, type MemoryGroup, precisionFor } from './src/cluster.ts';
import { devLocation } from './src/devLocation.ts';
import { devOpenMemory, devOpenScreen } from './src/devOpen.ts';
import { startWatching, stopWatching } from './src/geofence.ts';
import { forgetHearted, loadHearted, rememberHearted } from './src/hearted.ts';
import { MUTED_ANDROID_STYLE } from './src/mapStyle.ts';
import { anyNew } from './src/seen.ts';
import { FALLBACK_RADIUS_M, reachOf } from './src/reach.ts';
import {
  around,
  endFloorKm,
  metersBetween,
  pathMeters,
  type Region,
  walkFloorKm,
} from './src/region.ts';
import { loadNotifyNearby, saveNotifyNearby } from './src/notifyNearby.ts';
import { clearRoute, loadRoute, saveRoute } from './src/route.ts';
import {
  forgetUnlocked,
  inUnlockOrder,
  loadUnlocked,
  mergeUnlocked,
  rememberUnlocked,
  updateUnlocked,
  type Unlocked,
} from './src/unlocked.ts';
import { deviceId } from './src/device.ts';
import Memories from './src/Memories.tsx';
import { EndPick, EndWalk, Preview, WALK_KM, WalkDone } from './src/Plan.tsx';
import Settings from './src/Settings.tsx';
import EditProfile from './src/EditProfile.tsx';
import Drawer from './src/Drawer.tsx';
import { SignInScreen, loadSignedIn, saveSignedIn } from './src/SignIn.tsx';
import { syncSteps } from './src/steps.ts';
import FirstPick from './src/FirstPick.tsx';
import HowItWorks from './src/HowItWorks.tsx';
import StepsPill from './src/StepsPill.tsx';
import CloseButton from './src/CloseButton.tsx';
import Glyph from './src/Glyph.tsx';
import { walletOf } from './src/wallet.ts';
import Submit from './src/Submit.tsx';
import { distance } from './src/format.ts';
import { GlassButton } from './src/Glass.tsx';
import UnlockHere from './src/UnlockHere.tsx';
import { buttonText, color, font, label, pill, radius, solid } from './src/theme.ts';
import type { Permission } from './src/types.ts';
import { useMapCamera } from './src/useMapCamera.ts';
import MapFilter, { type MapShows } from './src/MapFilter.tsx';
import MemoryMarker from './src/MemoryMarker.tsx';
import MemorySheet from './src/MemorySheet.tsx';
import Paywall from './src/Paywall.tsx';
import { identify } from './src/purchases.ts';
import RouteLine from './src/RouteLine.tsx';
import StartupLogo from './src/StartupLogo.tsx';

// Held until StartupLogo has painted its first frame, which is the splash
// image exactly, so the native splash and the JS animation hand off with no
// gap and no double-flash.
SplashScreen.preventAutoHideAsync().catch(() => {});

/**
 * Where to look, and to plan a walk from, when we have no location permission.
 * A blank grey map or a dead end is a store-review rejection, and reviewers
 * routinely tap Deny - so this points at central Copenhagen, the first city,
 * where the seeded content actually is.
 */
/** `again` rolls for a plan; api/models.py ROUTE_AGAIN_MAX leaves room above
 *  it for "Next walk" taps. */
const ROLLS = 1_000_000;

const planKey = (km: number, ask: WalkAsk) => `${km}|${ask.loop}|${ask.end?.lat},${ask.end?.lng}`;

/** How far the map looks before a walk: half the longest walk, which is as far
 *  out as any walk can reach (docs/10, "The search radius is half the length"). */
const MAP_RADIUS_KM = WALK_KM.max / 2;

const FALLBACK_REGION: Region = {
  latitude: 55.67886,
  longitude: 12.57586,
  latitudeDelta: 0.09,
  longitudeDelta: 0.09,
};

/**
 * Street scale, ~1.1km tall. The map does a different job once it knows where
 * you are: at the fallback's 10km a 150m unlock radius is four pixels and the
 * mechanic is invisible, which makes the app read as a map of things you cannot
 * have. Here the reach circle is about a quarter of the screen and "two blocks"
 * is a distance you can see.
 */
const LOCATED_DELTA = 0.01;

/** The native dot follows the simulator's GPS, not the override, so while the
 *  position is pinned the app draws its own. See src/devLocation.ts. */
const DEV_PINNED = devLocation() !== null;

/** A follow flight: quick, because the next one waits for it to land. */
const FOLLOW_MS = 250;

/** The walk from `from` through every stop not in `skip`, in order, and back to
 *  `home` on a loop. Between two consecutive stops it follows the street leg
 *  when there is one, and so do the first and last legs when `ends` has them;
 *  otherwise straight. The preview's line, the walk's line and the pill's
 *  distance are all this one path. */
function pathThrough(
  from: Coordinates | null,
  stops: LocatedMemory[],
  skip: Set<number>,
  legs: Coordinates[][] | null,
  home: Coordinates | null,
  ends?: { out: Coordinates[] | null; home: Coordinates[] | null },
): Coordinates[] {
  const left = stops.flatMap((memory, i) => (skip.has(memory.id) ? [] : [i]));
  if (left.length === 0) return [];
  const walk: Coordinates[] = [];
  left.forEach((i, k) => {
    const leg =
      k === 0
        ? from && i === 0
          ? ends?.out
          : undefined
        : left[k - 1] === i - 1
          ? legs?.[i - 1]
          : undefined;
    if (k === 0 && from && !leg) walk.push(from);
    walk.push(...(leg ?? [stops[i].place.coordinates]));
  });
  if (home) {
    const last = left[left.length - 1] === stops.length - 1;
    walk.push(...(last && ends?.home ? ends.home : [home]));
  }
  return walk;
}

const NONE = new Set<number>();

/** The map of what is locked, then plan the walk, preview it, walk it.
 *  `loading` is the moment before the device knows whether it already accepted
 *  today's walk. */
type Stage = 'loading' | 'map' | 'end' | 'preview' | 'walk';

/** Whether `me` filed this. Both sides have to be a real id: an extracted
 *  memory's author is null and a signed-out profile's user_id is undefined,
 *  and undefined === undefined would otherwise call every extracted memory
 *  yours before the profile has even loaded. */
function filedBy(memory: LocatedMemory, me: string | null | undefined): boolean {
  return !!me && memory.author?.id === me;
}

export default function App() {
  const [logoDone, setLogoDone] = useState(false);

  // Only for grouping pins at the zoom they are seen at.
  const [region, setRegion] = useState<Region>(FALLBACK_REGION);
  const [stage, setStage] = useState<Stage>('loading');
  const [walkKm, setWalkKm] = useState(WALK_KM.initial);
  const [walkAsk, setWalkAsk] = useState<WalkAsk>({ loop: true, end: null });
  // Where the previewed walk starts, and whether that is central
  // Copenhagen standing in for a position we could not have.
  const [planFrom, setPlanFrom] = useState<Coordinates | null>(null);
  const [planFallback, setPlanFallback] = useState(false);
  // Which of the walks as good this preview is: a fresh roll for every plan,
  // one up for "Next walk", and the accept sends the same.
  const [again, setAgain] = useState(0);
  // "Next walk" came back unchanged: that was the only walk that long.
  const [onlyWalk, setOnlyWalk] = useState(false);
  const [preview, setPreview] = useState<TodaysRoute | null>(null);
  // Every walk this card has shown since the last fresh plan, and which is on
  // screen: ‹ steps back through them, and › steps on again before asking.
  const [shown, setShown] = useState<{ again: number; km: number; walk: TodaysRoute }[]>([]);
  const [shownAt, setShownAt] = useState(0);
  // The length that came back empty, when the card moved to the nearest that doesn't.
  const [emptyAt, setEmptyAt] = useState<number | null>(null);
  // "Walk here": the memory every planned walk passes, and the length the
  // server said reaches it, once it has said so (0 until then).
  const [walkTo, setWalkTo] = useState<LocatedMemory | null>(null);
  const [walkToKm, setWalkToKm] = useState(0);
  // Its own length, from the floor, so it leaves "Plan a walk"'s alone.
  const [hereKm, setHereKm] = useState(WALK_KM.min);
  // "End walk" was tapped with stops still to reach: the are-you-sure card.
  const [confirmEnd, setConfirmEnd] = useState(false);
  // The locked memories around you, before any walk (F29).
  const [nearby, setNearby] = useState<LocatedMemory[]>([]);
  const [mapShows, setMapShows] = useState<MapShows>('all');
  const [planBusy, setPlanBusy] = useState(false);
  const [planError, setPlanError] = useState<string | null>(null);
  // What was tapped is a point, not a memory: the sheet pages through it.
  const [openAt, setOpenAt] = useState<LocatedMemory[]>([]);
  const [openIndex, setOpenIndex] = useState(0);
  const [position, setPosition] = useState<Coordinates | null>(null);
  const [permission, setPermission] = useState<Permission>('unknown');
  // Off until chosen (notifyNearby.ts). Drives geofence.ts's background watch
  // of today's route, not the map's own viewport list - see the effect below.
  const [notifyNearby, setNotifyNearbyState] = useState(false);
  const [unlocked, setUnlocked] = useState<Unlocked>({});
  // The heart button's filled state and the journal's Hearted filter. The
  // server's memory_hearts row is the durable fact; /v1/unlocks refills this.
  const [hearted, setHearted] = useState<Set<number>>(new Set());
  const [nameError, setNameError] = useState<string | null>(null);
  const [unlocking, setUnlocking] = useState(false);
  const [holding, setHolding] = useState(false);
  const [unlockError, setUnlockError] = useState<string | null>(null);
  const [revealId, setRevealId] = useState<number | null>(null);
  // Today's accepted walk. routeSize is the route's true size (can be short in
  // a sparse area); it is not `route.length`, because a stop the local cache
  // lost or the server pruned still counted toward "today" when it was made.
  const [route, setRoute] = useState<LocatedMemory[]>([]);
  const [routeSize, setRouteSize] = useState<number | null>(null);
  // Nothing server-side hangs off this. It only switches the pill from "here
  // is today's route" to "here is where to go next".
  const [routeStarted, setRouteStarted] = useState(false);
  // The last stop was just earned, in this session. A relaunch on a walked day
  // does not set it, so the closing card shows once per walk with nothing stored.
  const [walkDone, setWalkDone] = useState(false);
  // Where a loop route comes back to, or null for a one-way one.
  const [routeHome, setRouteHome] = useState<Coordinates | null>(null);
  // Where a one-way route finishes, when one was tapped; kept like routeHome.
  const [routeEnd, setRouteEnd] = useState<Coordinates | null>(null);
  // Street shapes between consecutive stops; null draws them straight.
  const [routeLegs, setRouteLegs] = useState<Coordinates[][] | null>(null);
  // Resolved once at launch. Held in state rather than awaited at each call
  // site because the submit form needs it synchronously to decide whether it
  // can open at all.
  const [device, setDevice] = useState<string | null>(null);
  const [displayName, setDisplayName] = useState('');
  const [profile, setProfile] = useState<Profile | null>(null);
  const wallet = profile && walletOf(profile);
  // Steps still to walk before standing on a pin opens it; 0 when it can.
  const short = wallet?.short ?? 0;
  // The gate (docs/10, *Sign-in comes first*). Null until the stored answer is
  // read, so a signed-in launch never flashes the sign-in screen.
  const [signedIn, setSignedIn] = useState<boolean | null>(null);
  const [submitOpen, setSubmitOpen] = useState(false);
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [profileOpen, setProfileOpen] = useState(false);
  const [paywallOpen, setPaywallOpen] = useState(false);
  const [howOpen, setHowOpen] = useState(false);
  // The store's customer is this account, so the webhook names a user the
  // server knows (src/purchases.ts).
  useEffect(() => {
    identify(profile?.user_id ?? null).catch(() => {});
  }, [profile?.user_id]);
  // Set to open Submit as an editor for this memory instead of a blank form.
  // Null means Submit is either closed or filing something new.
  const [editingMemory, setEditingMemory] = useState<LocatedMemory | null>(null);
  // Bumped after a post, a save or a delete so the journal's Filed section
  // refetches without being closed and opened again.
  const [mineVersion, setMineVersion] = useState(0);
  // Only the handful of values the palette cannot carry need this: the map's
  // own appearance, and theme.ts `solid` for its overlays.
  const scheme = useColorScheme();
  // The journal is the only other screen, over a map that stays mounted.
  const [journalOpen, setJournalOpen] = useState(false);
  // A heart or a note came back for something you filed, unseen yet.
  const [journalNew, setJournalNew] = useState(false);

  // Region reports go through the camera, not straight from the map: a move
  // replayed from onMapReady never reports itself and the map still announces
  // where it was born. See src/useMapCamera.ts.
  const { mapRef, flyTo, inFlight, onMapReady, onRegionChangeComplete } =
    useMapCamera(setRegion);
  const mounted = useRef(true);
  // Read by callbacks that must not be rebuilt every time the person moves.
  const positionRef = useRef<Coordinates | null>(null);
  const watcher = useRef<Location.LocationSubscription | null>(null);

  useEffect(() => {
    // Set back to true on every run, not just initialised once: a Fast Refresh
    // runs the cleanup and then the effect again, and without this every
    // `if (!mounted.current) return` below becomes a permanent no-op.
    mounted.current = true;
    return () => {
      mounted.current = false;
      watcher.current?.remove();
    };
  }, []);

  /** The one writer of position. GPS, the watcher and the dev override all
   *  funnel through here, so there is a single place that knows. */
  const setHere = useCallback((next: Coordinates) => {
    positionRef.current = next;
    if (mounted.current) setPosition(next);
  }, []);

  const remember = useCallback(
    (pos: Location.LocationObject) => {
      setHere({ lat: pos.coords.latitude, lng: pos.coords.longitude });
    },
    [setHere],
  );

  /** Walking into range has to change the map by itself. A position read once
   *  at launch means a pin only turns unlockable if you happen to press
   *  something while standing on it, which is the opposite of the mechanic. */
  const watchPosition = useCallback(async () => {
    if (watcher.current) return;
    try {
      watcher.current = await Location.watchPositionAsync(
        // The reach radius is 20m, so anything coarser than a few metres lets
        // the person walk out of the circle before it moves. Foreground only -
        // see rule 2 in UI.md.
        { accuracy: Location.Accuracy.BestForNavigation, distanceInterval: 5 },
        remember,
      );
    } catch {
      // Best effort. Without a watch the pins stop turning unlockable as you
      // walk, which is worse but not broken - and every caller fires this
      // without awaiting it, so a rejection here would surface as nothing but
      // a red box.
    }
  }, [remember]);

  const goToMyLocation = useCallback(async () => {
    const granted = await Location.requestForegroundPermissionsAsync();
    if (granted.status !== 'granted') {
      setPermission(granted.canAskAgain ? 'denied' : 'blocked');
      return false;
    }
    setPermission('granted');

    // Permission granted is not the same as having a fix. Indoors, in airplane
    // mode, or on a simulator with no location set, this rejects - and the
    // "Turn on location" button calls it straight from onPress, so an unhandled
    // rejection was the whole error handling.
    // EXPO_PUBLIC_DEV_LOCATION, under __DEV__ only. See src/devLocation.ts.
    let here = devLocation();
    if (!here) {
      try {
        const pos = await Location.getCurrentPositionAsync({});
        here = { lat: pos.coords.latitude, lng: pos.coords.longitude };
      } catch {
        return false;
      }
      // No watcher when the position is pinned - it would overwrite the
      // override on the first fix and make it look broken.
      watchPosition();
    }
    setHere(here);
    const next: Region = {
      latitude: here.lat,
      longitude: here.lng,
      latitudeDelta: LOCATED_DELTA,
      longitudeDelta: LOCATED_DELTA,
    };
    flyTo(next);
    return true;
  }, [flyTo, setHere, watchPosition]);

  useEffect(() => {
    (async () => {
      // Never the system dialog first. Someone who already said yes should not
      // be asked again, so check silently; everyone else is asked by the plan
      // page's button, which is a press with a reason.
      const existing = await Location.getForegroundPermissionsAsync().catch(() => null);
      if (!mounted.current) return;
      if (existing?.granted) {
        goToMyLocation().catch(() => false);
        return;
      }
      setPermission(existing && !existing.canAskAgain ? 'blocked' : 'denied');
    })();
  }, [goToMyLocation]);

  useEffect(() => {
    loadSignedIn().then((on) => {
      if (mounted.current) setSignedIn((known) => known || on);
    });
    loadUnlocked().then((stored) => {
      if (!mounted.current) return;
      setUnlocked(stored);
    });
    loadHearted().then((stored) => {
      if (mounted.current) setHearted(stored);
    });

    // The device's collection, from the server. The local copy loads first and
    // renders immediately - this is what makes it survive the local copy being
    // cleared, and it is allowed to be slow or to fail entirely.
    deviceId()
      .then(async (id) => {
        if (!mounted.current) return;
        setDevice(id);
        // Both are allowed to be slow or to fail entirely: the local copy has
        // already rendered, and nothing here blocks the map.
        fetchProfile(id)
          .then((who) => {
            if (!mounted.current) return;
            setProfile(who);
            setDisplayName(who.display_name ?? '');
            // Only ever lets somebody in here, never out: this device is
            // unlinked only by its own sign-out, which accountChanged handles,
            // and a dev build's skip has no provider to show.
            if (who.providers.length > 0) {
              setSignedIn(true);
              saveSignedIn(true);
            }
            return syncSteps(id, who);
          })
          .then((after) => after && mounted.current && setProfile(after))
          .catch(() => {});
        const earned = await fetchUnlocked(id);
        if (!mounted.current || earned.length === 0) return;
        setUnlocked(await mergeUnlocked(earned));
        // The server's word wins for every memory it sent: hearted or taken
        // back on another phone of the account, or before a reinstall.
        const sent = new Set(earned.map((memory) => memory.id));
        const local = [...(await loadHearted())].filter((id) => !sent.has(id));
        const theirs = earned.filter((memory) => memory.hearted).map((memory) => memory.id);
        if (mounted.current) setHearted(await rememberHearted(new Set(local), ...theirs));
      })
      .catch(() => {});
    loadNotifyNearby().then((on) => {
      if (mounted.current) setNotifyNearbyState(on);
    });
  }, []);

  // The whole proposed walk, from where it would start and back.
  const previewPath = useMemo(
    () =>
      preview && planFrom
        ? pathThrough(
            planFrom,
            preview.memories,
            NONE,
            preview.legs,
            preview.loop ? planFrom : walkAsk.end,
            { out: preview.out_leg, home: preview.home_leg },
          )
        : [],
    [preview, planFrom, walkAsk.end],
  );

  /** Make `walk` today's route, on screen and in the local cache. `start` is
   *  where it was planned from and `end` where a one-way one finishes - the
   *  server stores neither. */
  const takeRoute = useCallback(
    (walk: TodaysRoute, start: Coordinates | null, end: Coordinates | null) => {
      setRoute(walk.memories);
      setRouteSize(walk.size);
      setRouteLegs(walk.legs);
      setRouteHome(walk.loop ? start : null);
      setRouteEnd(walk.loop ? null : end);
      saveRoute({
        route_date: walk.route_date,
        memories: walk.memories,
        loop: walk.loop,
        legs: walk.legs,
        start: start ?? undefined,
        end: (!walk.loop && end) || undefined,
      });
    },
    [],
  );

  /** Forget today's walk, on screen and in the cache: the map comes back. */
  const dropRoute = useCallback(() => {
    setRoute([]);
    setRouteSize(null);
    setRouteLegs(null);
    setRouteHome(null);
    setRouteEnd(null);
    setRouteStarted(false);
    setWalkDone(false);
    setConfirmEnd(false);
    clearRoute();
    setStage('map');
  }, []);

  // Whether today's walk was already accepted: the cached copy first, so a
  // relaunch lands on it at once, then the server, which is the authority.
  // A 404 drops the cached copy: the walk was ended somewhere else, and
  // keeping it would walk a route the server no longer unlocks. Offline, the
  // cache stands. With neither, today starts at the plan page.
  useEffect(() => {
    if (!device) return;
    const today = new Date().toISOString().slice(0, 10);
    (async () => {
      const cached = await loadRoute(today);
      if (!mounted.current) return;
      if (cached) {
        setRoute(cached.memories);
        setRouteLegs(cached.legs ?? null);
        if (cached.loop && cached.start) setRouteHome(cached.start);
        if (!cached.loop && cached.end) setRouteEnd(cached.end);
        setStage('walk');
      }
      try {
        const accepted = await fetchTodaysRoute(device);
        if (!mounted.current) return;
        if (accepted) {
          takeRoute(accepted, cached?.start ?? null, cached?.end ?? null);
          setStage('walk');
        } else {
          dropRoute();
        }
      } catch {
        if (mounted.current && !cached) setStage('map');
      }
    })();
  }, [device, takeRoute, dropRoute]);

  /** End today's walk and go back to the map, where another can be planned. */
  const endWalk = useCallback(async () => {
    if (!device) return;
    setPlanBusy(true);
    setPlanError(null);
    try {
      await endRoute(device);
      if (mounted.current) dropRoute();
    } catch {
      if (mounted.current) setPlanError("Can't reach Memory Lane right now.");
    } finally {
      if (mounted.current) setPlanBusy(false);
    }
  }, [device, dropRoute]);

  // The shortest walk that reaches the "Walk here" memory and the end: the
  // estimates from where you are, or what the server said, whichever is
  // longest. It lifts the length without changing the one chosen, which comes
  // back with the pin gone.
  const walkFloor = useMemo(() => {
    const from = position ?? { lat: FALLBACK_REGION.latitude, lng: FALLBACK_REGION.longitude };
    const crow = (to: Coordinates) => metersBetween(from.lat, from.lng, to.lat, to.lng);
    const floors = [WALK_KM.min, walkToKm];
    if (walkTo) {
      floors.push(walkFloorKm(crow(walkTo.place.coordinates), walkAsk.loop, WALK_KM.step));
    }
    if (walkAsk.end) floors.push(endFloorKm(crow(walkAsk.end), WALK_KM.step));
    return Math.max(...floors);
  }, [walkTo, walkToKm, position, walkAsk.loop, walkAsk.end]);
  const askedKm = walkTo ? hereKm : walkKm;
  const planKm = walkFloor <= WALK_KM.max ? Math.max(askedKm, walkFloor) : askedKm;

  // The length and shape of the walk on the card, once it is drawn.
  const plannedKey = useRef<string | null>(null);
  const planWalk = useCallback(async (next: number, another = false) => {
    if (!device) return;
    setPlanBusy(true);
    setPlanError(null);
    let from = positionRef.current;
    if (!from && (await goToMyLocation().catch(() => false))) from = positionRef.current;
    const fallback = !from;
    const anchor = from ?? { lat: FALLBACK_REGION.latitude, lng: FALLBACK_REGION.longitude };
    try {
      const plan = (km: number) =>
        previewRoute(device, anchor, km * 1000, walkAsk, next, walkTo?.id ?? null);
      const ids = (route: TodaysRoute | null) => route?.memories.map((m) => m.id).join();
      const last = shown[shown.length - 1]?.walk ?? null;
      let km = planKm;
      let walk = await plan(km);
      // Never "the only walk": the same one back offers the nearest other
      // length, and the slider moves to say so. Never "no walk" either: an
      // empty length moves up to the nearest that has one. The longest first,
      // so nothing within reach at all costs one request, not eighteen.
      // ponytail: up to eighteen previews in a row; a server-side "nearest walk" if it drags.
      const empty = !another && walk.memories.length === 0 && km < WALK_KM.max;
      if (empty) {
        const longest = await plan(WALK_KM.max);
        if (longest.memories.length > 0) {
          for (let up = km + WALK_KM.step; up <= WALK_KM.max; up += WALK_KM.step) {
            const other = up === WALK_KM.max ? longest : await plan(up);
            if (other.memories.length > 0) {
              km = up;
              walk = other;
              break;
            }
          }
        }
      }
      if (another && ids(walk) === ids(last)) {
        const low = Math.max(WALK_KM.min, walkFloor);
        const tried = new Set([km]);
        for (const step of [-0.5, 0.5, -1, 1, -1.5, 1.5]) {
          const nearby = Math.min(Math.max(planKm + step, low), WALK_KM.max);
          if (tried.has(nearby)) continue;
          tried.add(nearby);
          const other = await plan(nearby);
          if (ids(other) !== ids(last)) {
            km = nearby;
            walk = other;
            break;
          }
        }
      }
      if (!mounted.current) return;
      if (km !== planKm) (walkTo ? setHereKm : setWalkKm)(km);
      plannedKey.current = planKey(km, walkAsk);
      setAgain(next);
      const only = another && ids(walk) === ids(last);
      setOnlyWalk(only);
      if (!another) {
        setShown([{ again: next, km, walk }]);
        setShownAt(0);
        setEmptyAt(empty && km !== planKm ? planKm : null);
      } else if (!only) {
        setShown([...shown, { again: next, km, walk }]);
        setShownAt(shown.length);
      }
      setPlanFrom(anchor);
      setPlanFallback(fallback);
      setPreview(walk);
      setStage('preview');
    } catch (e) {
      if (!mounted.current) return;
      const refusal = walkHereRefusal(e);
      if (refusal?.reason === 'too_far') {
        const km = Math.ceil(refusal.min_budget_meters / 1000 / WALK_KM.step) * WALK_KM.step;
        setWalkToKm(km);
        setPlanError(`${planKm} km is too short from here. Try ${km} km or more.`);
      } else if (refusal) {
        setWalkTo(null);
        setPlanError("That one won't fit on a walk from here.");
      } else {
        setPlanError("Can't reach Memory Lane right now.");
      }
    } finally {
      if (mounted.current) setPlanBusy(false);
    }
  }, [device, goToMyLocation, planKm, walkFloor, walkAsk, shown, walkTo]);

  /** Back, or on again, through the walks the card has shown. */
  const showAt = (i: number) => {
    const entry = shown[i];
    if (!entry) return;
    if (entry.km !== planKm) (walkTo ? setHereKm : setWalkKm)(entry.km);
    plannedKey.current = planKey(entry.km, walkAsk);
    setShownAt(i);
    setAgain(entry.again);
    setPreview(entry.walk);
    setPlanError(null);
  };

  // Draw first, adjust after: opening the card plans, and so does every
  // change to it. A "too far" answer lifts planKm, which plans once more at a
  // length that reaches. Through a ref, so a new preview does not re-plan, and
  // not for what is already drawn: a length Next walk moved to.
  const planWalkRef = useRef(planWalk);
  planWalkRef.current = planWalk;
  const planning = stage === 'preview';
  useEffect(() => {
    if (!planning) {
      plannedKey.current = null;
      return;
    }
    if (plannedKey.current !== planKey(planKm, walkAsk)) {
      planWalkRef.current(Math.floor(Math.random() * ROLLS));
    }
  }, [planning, planKm, walkAsk]);

  const backToMap = () => {
    setPlanError(null);
    setWalkTo(null);
    setStage('map');
  };

  const acceptWalk = useCallback(async () => {
    if (!device || !planFrom) return;
    setPlanBusy(true);
    setPlanError(null);
    try {
      const walk = await acceptRoute(
        device,
        planFrom,
        planKm * 1000,
        walkAsk,
        again,
        walkTo?.id ?? null,
      );
      if (!mounted.current) return;
      takeRoute(walk, planFrom, walkAsk.end);
      setPreview(null);
      setWalkTo(null);
      setStage('walk');
    } catch {
      if (mounted.current) setPlanError("Can't reach Memory Lane right now.");
    } finally {
      if (mounted.current) setPlanBusy(false);
    }
  }, [device, planFrom, planKm, walkAsk, again, takeRoute, walkTo]);

  // Once on the map, and again when a position first arrives: by where you
  // are, never by viewport, so panning fetches nothing (UI.md rule 3).
  const located = !!position;
  const me = profile?.user_id;
  useEffect(() => {
    if (stage !== 'map') return;
    const controller = new AbortController();
    const at = positionRef.current ?? {
      lat: FALLBACK_REGION.latitude,
      lng: FALLBACK_REGION.longitude,
    };
    fetchNearby(at, MAP_RADIUS_KM, device, controller.signal)
      // Locked and opened both: MapFilter picks which (docs/10, "A map of what
      // is locked"). mineVersion refetches the moment you file, edit or delete.
      .then((found) => mounted.current && setNearby(found))
      .catch(() => {});
    return () => controller.abort();
  }, [stage, located, me, mineVersion, device]);

  // The preview's zoom: the whole walk, its start and any end, clear of the card.
  useEffect(() => {
    if (stage !== 'preview' || !preview || !planFrom) return;
    const end = !preview.loop && walkAsk.end ? [walkAsk.end] : [];
    mapRef.current?.fitToCoordinates(
      [planFrom, ...preview.memories.map((memory) => memory.place.coordinates), ...end].map(
        (c) => ({ latitude: c.lat, longitude: c.lng }),
      ),
      { edgePadding: { top: 100, right: 60, bottom: 300, left: 60 }, animated: true },
    );
  }, [stage, preview, planFrom, mapRef, walkAsk.end]);

  // Ids, not memories: reachOf only asks whether this device walked to it, and
  // a Set keeps that an O(1) question inside three passes over every group.
  const earned = useMemo(() => new Set(Object.keys(unlocked).map(Number)), [unlocked]);
  // What the device has earned wins over what the server said when the route
  // was made, so a stop reads as earned the moment it is.
  const routeShown = useMemo(
    () => route.map((memory) => unlocked[memory.id] ?? memory),
    [route, unlocked],
  );
  // The only pins there are: what is locked around you on the map, the walk
  // being previewed, or the walk being walked. Nothing off the route is drawn
  // on a walk.
  const nearbyShown = useMemo(
    () =>
      nearby
        .map((memory) => unlocked[memory.id] ?? memory)
        .filter((memory) => mapShows === 'all' || memory.locked === (mapShows === 'locked')),
    [nearby, unlocked, mapShows],
  );
  // F36: until the welcome one is spent, three locked ones near you to choose
  // from. Hearts first, the corpus has no better quality signal yet.
  // ponytail: rank on a quality score once extraction stores one.
  const firstPicks = useMemo(
    () =>
      (profile?.welcome_unlocks ?? 0) > 0
        ? nearby
            .filter((memory) => memory.locked)
            .sort(
              (a, b) =>
                b.heart_count - a.heart_count ||
                (a.distance_meters ?? Infinity) - (b.distance_meters ?? Infinity),
            )
            .slice(0, 3)
        : [],
    [profile, nearby],
  );
  const pins = useMemo(
    () =>
      stage === 'map' || stage === 'end'
        ? nearbyShown
        : stage === 'preview'
          ? (preview?.memories ?? [])
          : stage === 'walk'
            ? routeShown
            : [],
    [stage, nearbyShown, preview, routeShown],
  );
  // The background watch tracks today's route, not the map's panned viewport -
  // bounded (ROUTE_SIZE, well under the OS's ~20-region cap), already "nearby
  // things to walk to", and it does not change every time somebody pans the
  // map. Re-registers whenever a stop is earned, so an already-unlocked stop
  // drops out of the watch the next time this runs rather than lingering.
  useEffect(() => {
    if (!notifyNearby) return;
    startWatching(routeShown).catch((e) => console.warn('Nearby notifications did not start:', e));
  }, [notifyNearby, routeShown]);

  const handleNotifyNearby = useCallback((next: boolean) => {
    setNotifyNearbyState(next);
    saveNotifyNearby(next);
    if (!next) stopWatching().catch(() => {});
  }, []);
  // 1-based position in the route, by memory id - a group's badge looks itself
  // up here rather than the route ever knowing about groups. Earned stops drop
  // out, and the rest keep their numbers. A preview numbers every stop.
  const routePositionById = useMemo(() => {
    const map = new Map<number, number>();
    // The map before a walk has no route: nothing on it is a stop.
    if (stage === 'map' || stage === 'end') return map;
    const walking = stage !== 'preview';
    pins.forEach((memory, i) => {
      if (!walking || !earned.has(memory.id)) map.set(memory.id, i + 1);
    });
    return map;
  }, [pins, earned, stage]);
  const routeUnlockedCount = useMemo(
    () => routeShown.filter((memory) => earned.has(memory.id)).length,
    [routeShown, earned],
  );
  // In route order, so "next" always means the nearest one not yet earned -
  // not the nearest one geographically.
  const nextRouteStop = useMemo(
    () => routeShown.find((memory) => !earned.has(memory.id)),
    [routeShown, earned],
  );
  // What is left to walk: from the person, through every unearned stop in
  // order, and home again on a loop.
  const routePath = useMemo(
    () => pathThrough(position, routeShown, earned, routeLegs, routeHome ?? routeEnd),
    [routeShown, earned, position, routeHome, routeEnd, routeLegs],
  );
  const routeDone = route.length > 0 && !nextRouteStop;
  const routeTotal = routeSize ?? route.length;
  const toNextStop =
    position && nextRouteStop
      ? metersBetween(
          position.lat,
          position.lng,
          nextRouteStop.place.coordinates.lat,
          nextRouteStop.place.coordinates.lng,
        )
      : null;
  const routeLeft = position ? pathMeters(routePath) : null;
  // The walk card's two lines: where next, then how far through and how far left.
  const routeLabel =
    routeDone || !nextRouteStop
      ? 'Every stop unlocked'
      : `Next: ${nextRouteStop.place.name}` +
        (toNextStop === null ? '' : ` · ${distance(toNextStop)}`);
  const routeProgress =
    `${nextRouteStop ? (routePositionById.get(nextRouteStop.id) ?? routeUnlockedCount + 1) : routeTotal} of ${routeTotal}` +
    (routeLeft === null || routeDone ? '' : ` · ${distance(routeLeft)} left`);
  // Banded, so panning inside one zoom level does not regroup: `region` changes
  // on every gesture, ahead of the fetch debounce.
  const precision = precisionFor(region.latitudeDelta);
  const groups = useMemo(() => groupByLocation(pins, precision), [pins, precision]);

  // On the walk the camera follows the person, and a pinch that drifts the
  // centre is put back. A drag lets go until "Center on me" (Google's pattern).
  const [following, setFollowing] = useState(true);
  useEffect(() => setFollowing(true), [stage]);
  const pinned = stage === 'walk' && !!position && !walkDone && following;
  useEffect(() => {
    // Never over a flight: `region` is still where it took off, so following
    // from it undid the pill's zoom-out, and a chain of flights each cut short
    // by the next left the camera trailing the person. Its landing sets
    // `region`, which runs this again from there.
    if (!pinned || !position || inFlight()) return;
    // 4m: under the watcher's 5m step, over the slop of a settled map.
    if (metersBetween(region.latitude, region.longitude, position.lat, position.lng) < 4) return;
    flyTo({ ...region, latitude: position.lat, longitude: position.lng }, FOLLOW_MS);
  }, [pinned, position, region, flyTo, inFlight]);
  const openMemories = useMemo(
    () => openAt.map((memory) => unlocked[memory.id] ?? memory),
    [openAt, unlocked],
  );
  // After the last stop's sheet is closed, not over it: that memory is read first.
  const showDone = walkDone && openAt.length === 0;
  // The whole walk, from the start and home on a loop; stop to stop one-way.
  const donePath = useMemo(
    () =>
      showDone ? pathThrough(routeHome, routeShown, NONE, routeLegs, routeHome ?? routeEnd) : [],
    [showDone, routeShown, routeLegs, routeHome, routeEnd],
  );
  const doneMinutes = useMemo(() => {
    const times = routeShown.map((memory) => unlocked[memory.id]?.unlocked_at);
    if (!showDone || times.some((t) => t === undefined)) return null;
    const span = Math.max(...(times as number[])) - Math.min(...(times as number[]));
    // A stop earned on an earlier day would make this a count of days.
    return span < 12 * 3600_000 ? Math.max(1, Math.round(span / 60_000)) : null;
  }, [showDone, routeShown, unlocked]);
  useEffect(() => {
    if (donePath.length < 2) return;
    mapRef.current?.fitToCoordinates(
      donePath.map((c) => ({ latitude: c.lat, longitude: c.lng })),
      { edgePadding: { top: 80, right: 60, bottom: 300, left: 60 }, animated: true },
    );
  }, [donePath, mapRef]);
  const mine = !!openMemories[openIndex] && filedBy(openMemories[openIndex], me);

  // EXPO_PUBLIC_DEV_OPEN_SCREEN, under __DEV__ only. The submit sheet is three
  // taps in and there are no taps, so without this it could only be read as
  // source. Mount-only: it sets where you land, not where you stay.
  useEffect(() => {
    const screen = devOpenScreen();
    if (!screen) return;
    setJournalOpen(screen === 'journal');
    setSubmitOpen(screen === 'submit');
  }, []);

  // EXPO_PUBLIC_DEV_OPEN_MEMORY, under __DEV__ only. See src/devOpen.ts: there
  // is no way to script a tap on this simulator, so without it the sheet cannot
  // be looked at by anything but a person. Fires once - closing it by hand must
  // not spring it open again on the next render.
  //
  // Opens the whole GROUP and pages to the memory, which is what a tap does. A
  // first version opened the one memory and quietly hid the pager, so the
  // three-deep stack screenshotted as a single: the affordance has to reproduce
  // the tap or it is a second code path that can disagree with the product.
  const openMemory = useCallback(
    (id: number): boolean => {
      const group = groups.find((g) =>
        g.memories.some((memory) => memory.id === id),
      );
      if (!group) return false;
      setOpenAt(group.memories);
      setOpenIndex(group.memories.findIndex((memory) => memory.id === id));
      return true;
    },
    [groups],
  );

  const devOpened = useRef(false);
  useEffect(() => {
    const id = devOpenMemory();
    if (id == null || devOpened.current) return;
    if (openMemory(id)) devOpened.current = true;
  }, [openMemory]);

  // Tapping the proximity notification (src/geofence.ts) opens the memory it
  // named. Waits for `groups`, which are still empty on a cold start.
  const notification = Notifications.useLastNotificationResponse();
  const handledNotification = useRef<string | null>(null);
  useEffect(() => {
    const request = notification?.notification.request;
    const id = request?.content.data?.memoryId;
    if (typeof id !== 'number' || handledNotification.current === request!.identifier) return;
    if (!openMemory(id)) return;
    handledNotification.current = request!.identifier;
    setJournalOpen(false);
    setSubmitOpen(false);
  }, [notification, openMemory]);

  // Whatever you stand on opens, walk or no walk: free ones first, then steps
  // (docs/10, "Steps open a memory").
  const withinReach = useMemo(
    () =>
      stage === 'walk' || stage === 'map'
        ? groups.filter((group) => reachOf(group, position, earned) === 'unlockable')
        : [],
    [stage, groups, position, earned],
  );
  const collected = useMemo(() => inUnlockOrder(unlocked), [unlocked]);
  // Filing unlocks what you filed; the journal keeps that under My Memories.
  const unlockedByOthers = useMemo(
    () => collected.filter((memory) => !filedBy(memory, me)),
    [collected, me],
  );

  // The route stop you are standing at, lowest number first. The order is a
  // suggestion: take another way round and whichever stop you reach is the one
  // to open.
  const stopHere = useMemo(() => {
    let best: { group: MemoryGroup; index: number; position: number; name: string } | null =
      null;
    for (const group of withinReach) {
      for (const [index, memory] of group.memories.entries()) {
        const at = routePositionById.get(memory.id);
        if (at && (!best || at < best.position)) {
          best = { group, index, position: at, name: memory.place.name };
        }
      }
    }
    return best;
  }, [withinReach, routePositionById]);
  const onRoute = route.length > 0;

  // The memory the ring on the map opens: the one tapped, else the route stop
  // you are at, else the nearest. docs/10, "Unlock on the map".
  const [pickedId, setPickedId] = useState<number | null>(null);
  const ringFor = useMemo(() => {
    if (!position) return null;
    const here: { group: MemoryGroup; index: number; away: number }[] = [];
    for (const group of withinReach) {
      for (const [index, memory] of group.memories.entries()) {
        const { lat, lng } = memory.place.coordinates;
        const away = metersBetween(position.lat, position.lng, lat, lng);
        if (memory.locked && away <= (memory.unlock_radius_meters ?? FALLBACK_RADIUS_M)) {
          here.push({ group, index, away });
        }
      }
    }
    const picked = here.find(({ group, index }) => group.memories[index].id === pickedId);
    if (picked) return picked;
    if (stopHere) return stopHere;
    return here.sort((a, b) => a.away - b.away)[0] ?? null;
  }, [withinReach, position, pickedId, stopHere]);
  const ringMemory = ringFor ? ringFor.group.memories[ringFor.index] : null;
  // "Center on me": on a walk once a drag let go; before one, once the map is
  // off you by more than a sixth of the screen. Never over the ring.
  const showRecenter =
    !!position &&
    !ringFor &&
    (stage === 'walk'
      ? !following && !walkDone
      : stage === 'map' &&
        metersBetween(region.latitude, region.longitude, position.lat, position.lng) >
          region.latitudeDelta * 111_000 * 0.15);

  // Reaching a stop is the moment the app is for. The transition, not the
  // state: ringFor gets a new identity on every 5m position update. Light,
  // because the heavier taps belong to the unlock itself. A sheet open on the
  // memory gives way, or it would hide the ring.
  const inReach = ringMemory !== null;
  const wasInReach = useRef(false);
  useEffect(() => {
    if (inReach && !wasInReach.current) {
      if (!short) Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Light).catch(() => {});
      setOpenAt((open) => (open.some((m) => m.id === ringMemory?.id && m.locked) ? [] : open));
    }
    wasInReach.current = inReach;
  }, [inReach, ringMemory, short]);
  // A refusal belongs to the memory it was for.
  useEffect(() => setUnlockError(null), [ringMemory?.id]);

  const placesUnlocked = useMemo(
    () => new Set(collected.map((memory) => memory.place.id)).size,
    [collected],
  );
  // Always the server's, never ours: every memory carries it. FALLBACK_RADIUS_M
  // only for the moments before a route has answered.
  const radiusMeters =
    [...route, ...(preview?.memories ?? [])].find((memory) => memory.unlock_radius_meters)
      ?.unlock_radius_meters ?? FALLBACK_RADIUS_M;

  // In reach, a pin is not opened but held: tapping it points the ring at it.
  const pickRing = (group: MemoryGroup) => {
    Haptics.selectionAsync().catch(() => {});
    const locked = group.memories.filter((memory) => memory.locked);
    setPickedId((locked.find((memory) => routePositionById.has(memory.id)) ?? locked[0]).id);
    setUnlockError(null);
  };

  const openGroup = (group: MemoryGroup, index = 0) => {
    // A pin is a small target on a moving map, and a tap that lands has to feel
    // different from one that misses. The heavier taps are reserved for the
    // unlock, so this is the lightest one there is.
    Haptics.selectionAsync().catch(() => {});
    setOpenAt(group.memories);
    setOpenIndex(index);
    setUnlockError(null);
  };

  // A wide group is several places the grid merged because the map is zoomed
  // out, not several memories sharing a doorway. Opening a sheet on it would
  // page through venues miles apart, so it splits instead.
  const zoomTo = (group: MemoryGroup) => {
    Haptics.selectionAsync().catch(() => {});
    const span = (group.spanMeters * 3) / 111_000;
    flyTo({
      latitude: group.lat,
      longitude: group.lng,
      latitudeDelta: Math.max(span, LOCATED_DELTA),
      longitudeDelta: Math.max(span, LOCATED_DELTA),
    });
  };

  const unlock = useCallback(
    async (memory: LocatedMemory): Promise<boolean> => {
      // No position is fine: a free unlock opens it from anywhere.
      const at = positionRef.current;

      setUnlocking(true);
      setUnlockError(null);
      try {
        const opened = await unlockMemory(memory.id, at, await deviceId());
        if (!mounted.current) return false;
        if (opened) {
          // This was the last not-yet-earned stop of a started route: the same
          // Success haptic UnlockButton fires for one memory, once more - an
          // affirmation on the unlock that already happened, not a new mechanic.
          if (
            routeStarted &&
            nextRouteStop?.id === memory.id &&
            routeShown.every((stop) => stop.id === memory.id || earned.has(stop.id))
          ) {
            Haptics.notificationAsync(Haptics.NotificationFeedbackType.Success).catch(() => {});
            setWalkDone(true);
          }
          // What it cost, and the streak the walk's card shows, counting today.
          deviceId()
            .then(fetchProfile)
            .then((who) => mounted.current && setProfile(who))
            .catch(() => {});
          setUnlocked(await rememberUnlocked(unlocked, opened));
          return true;
        } else {
          // The server re-measures, and GPS moves between the press and the
          // request. Silence here would read as a broken button.
          setUnlockError('Not quite there. Take a few more steps.');
        }
      } catch (e) {
        if (!mounted.current) return false;
        const short = outOfSteps(e);
        if (short) {
          setUnlockError(
            `It takes ${short.price.toLocaleString()} steps. You have ${short.steps.toLocaleString()}.`,
          );
          setPaywallOpen(true);
        } else {
          setUnlockError("Can't reach Memory Lane right now.");
        }
      } finally {
        if (mounted.current) setUnlocking(false);
      }
      return false;
    },
    [unlocked, routeStarted, nextRouteStop, routeShown, earned],
  );

  // Count what was walked, from where the last count stopped.
  const countSteps = useCallback(() => {
    deviceId()
      .then(async (id) => {
        const who = await fetchProfile(id);
        const after = (await syncSteps(id, who)) ?? who;
        if (!mounted.current) return;
        // A walk's worth landing is felt; a stroll to the fridge is not.
        if (after.steps - who.steps >= 100) {
          Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Light).catch(() => {});
        }
        setProfile(after);
      })
      .catch(() => {});
  }, []);
  const checkJournal = useCallback(() => {
    deviceId()
      .then((id) => fetchMine(id))
      .then((page) => anyNew(page.memories))
      .then((fresh) => mounted.current && setJournalNew(fresh))
      .catch(() => {});
  }, []);
  // Asked at launch, and again each time the journal closes: a look at My
  // Memories there is what clears it.
  useEffect(() => {
    if (!journalOpen) checkJournal();
  }, [journalOpen, checkJournal]);
  // Back in the app, count what was walked while it was away.
  useEffect(() => {
    const sub = AppState.addEventListener('change', (state) => {
      if (state !== 'active') return;
      countSteps();
      checkJournal();
    });
    return () => sub.remove();
  }, [countSteps, checkJournal]);

  const heart = useCallback(
    async (memory: LocatedMemory) => {
      try {
        // A second tap takes it back.
        const undo = hearted.has(memory.id);
        const count = await (undo ? unheartMemory : heartMemory)(memory.id, await deviceId());
        if (!mounted.current) return;
        setHearted(await (undo ? forgetHearted : rememberHearted)(hearted, memory.id));
        // openMemories prefers unlocked[id] over openAt's own snapshot, so a
        // memory already in the collection needs patching there too or the
        // sheet would keep showing the stale count.
        setOpenAt((current) =>
          current.map((m) => (m.id === memory.id ? { ...m, heart_count: count } : m)),
        );
        if (unlocked[memory.id]) {
          setUnlocked(
            await updateUnlocked(unlocked, { ...unlocked[memory.id], heart_count: count }),
          );
        }
      } catch {
        // Silent: a heart is a passive nicety, not a gated outcome the app
        // has to explain a failure for the way unlock's error message does.
      }
    },
    [hearted, unlocked],
  );

  // Reported from this device already. Local only: the server counts accounts,
  // and this stops the control offering a second press that does nothing.
  const [reported, setReported] = useState<Set<number>>(new Set());
  const report = useCallback(async (memory: LocatedMemory) => {
    // Optimistic: it is idempotent per device, and a report that says it landed
    // beats one that silently did not.
    setReported((current) => new Set(current).add(memory.id));
    reportMemory(memory.id, await deviceId()).catch(() => {});
  }, []);
  const block = useCallback(async (memory: LocatedMemory) => {
    const author = memory.author?.id;
    if (!author) return;
    try {
      await blockUser(author, await deviceId());
    } catch {
      return;
    }
    if (!mounted.current) return;
    setNearby((current) => current.filter((m) => m.author?.id !== author));
    setOpenAt([]);
  }, []);

  const posted = useCallback(
    async (memory: LocatedMemory) => {
      // Already unlocked by the server - filing something is standing there -
      // so it goes straight into the collection.
      setUnlocked(await rememberUnlocked(unlocked, memory));
      // Filing is what made this device a user, if nothing had yet: without the
      // id the sheet below would take their own memory for a stranger's.
      setProfile((who) =>
        who
          ? { ...who, submitted: who.submitted + 1, user_id: who.user_id ?? memory.author?.id ?? null }
          : who,
      );
      setMineVersion((v) => v + 1);
      // Show them what they filed. The modal closing is not a confirmation,
      // and this is also the first sight of what anybody else will find here.
      setOpenAt([memory]);
      setOpenIndex(0);
    },
    [unlocked],
  );

  /** Opens Submit as an editor rather than a blank form - the journal and the
   *  map sheet both lead here. */
  const openEditor = useCallback((memory: LocatedMemory) => {
    setEditingMemory(memory);
    setSubmitOpen(true);
  }, []);

  const saved = useCallback(
    async (memory: LocatedMemory) => {
      setUnlocked(await updateUnlocked(unlocked, memory));
      setMineVersion((v) => v + 1);
      // The sheet, if it is the one open on this memory, should show what was
      // just saved rather than the words it had when it opened.
      setOpenAt((current) => current.map((m) => (m.id === memory.id ? memory : m)));
    },
    [unlocked],
  );

  const deleted = useCallback(
    async (id: number) => {
      setUnlocked(await forgetUnlocked(unlocked, id));
      setProfile((who) => (who ? { ...who, submitted: Math.max(0, who.submitted - 1) } : who));
      setMineVersion((v) => v + 1);
      // Closes the sheet outright rather than trying to keep a stack's other
      // members in view - simpler, and the editor that led here only ever
      // opened on one memory at a time regardless of what it was stacked with.
      setOpenAt([]);
    },
    [unlocked],
  );

  /** Signing in or out changes whose collection this is - the server answers
   *  /v1/unlocks for every device on the account - so it is refetched rather
   *  than left showing what this handset happened to have earned. */
  const accountChanged = useCallback(
    (who: Profile) => {
      setProfile(who);
      setDisplayName(who.display_name ?? '');
      const on = who.providers.length > 0;
      setSignedIn(on);
      saveSignedIn(on);
      if (!device) return;
      fetchUnlocked(device)
        .then(async (earned) => {
          if (!mounted.current || earned.length === 0) return;
          setUnlocked(await mergeUnlocked(earned));
        })
        .catch(() => {});
    },
    [device],
  );

  const rename = useCallback(
    (next: string) => {
      setDisplayName(next);
      if (!device) return;
      // Saved as it is typed, so a failure is not fatal - the next keystroke
      // retries. But it cannot be silent: the server holds the name submissions
      // are signed with, so a save that never lands means posting as Anonymous
      // while the field on screen says otherwise.
      saveDisplayName(device, next)
        .then(() => setNameError(null))
        .catch((e) =>
          setNameError(
            wasRefused(e)
              ? "That name can't be used here."
              : "Your name didn't save. Keep typing to try again.",
          ),
        );
    },
    [device],
  );

  const walking = stage === 'walk';

  if (!logoDone) {
    return (
      <StartupLogo
        onDone={() => setLogoDone(true)}
      />
    );
  }

  if (signedIn === null) return null;

  if (!signedIn) {
    return (
      <SafeAreaProvider>
        <StatusBar style="auto" />
        <SignInScreen
          device={device}
          onProfile={accountChanged}
          onSkip={() => {
            setSignedIn(true);
            saveSignedIn(true);
          }}
        />
      </SafeAreaProvider>
    );
  }

  return (
    <SafeAreaProvider>
      <View style={styles.container}>
        {/* "auto" rather than "dark": the bar has to invert with everything
            else, and hardcoding it is how an app ends up with black glyphs on a
            black background at night. */}
        <StatusBar style="auto" />

        {/* The map never unmounts: that would mean refetching, losing the
            viewport and re-animating to GPS on every glance at the journal. */}
        <View style={styles.screen}>
          <MapView
            ref={mapRef}
            style={StyleSheet.absoluteFill}
            initialRegion={FALLBACK_REGION}
            showsUserLocation={permission === 'granted' && !DEV_PINNED}
            // See src/mapStyle.ts: the map is a backdrop, not a competitor.
            mapType={Platform.OS === 'ios' ? 'mutedStandard' : 'standard'}
            // Apple Maps follows the system on its own, but only if it is not
            // told otherwise; naming it here keeps the default explicit.
            userInterfaceStyle={scheme === 'dark' ? 'dark' : 'light'}
            customMapStyle={MUTED_ANDROID_STYLE}
            showsPointsOfInterests={false}
            rotateEnabled={!pinned}
            pitchEnabled={!pinned}
            onRegionChangeComplete={onRegionChangeComplete}
            onMapReady={onMapReady}
            // A one-finger drag is a look around: stop following. A pinch is
            // two and keeps it. Apple Maps never reports isGesture.
            onTouchMove={(e) => {
              if (pinned && e.nativeEvent.touches.length === 1) setFollowing(false);
            }}
            onPress={(e) => {
              if (stage !== 'end') return;
              const { latitude: lat, longitude: lng } = e.nativeEvent.coordinate;
              Haptics.selectionAsync().catch(() => {});
              setWalkAsk((ask) => ({ ...ask, end: { lat, lng } }));
              setWalkToKm(0);
              setStage('preview');
            }}
            // Teleport, under __DEV__ only: the pinned position ignores the
            // simulator's GPS. See src/devLocation.ts. Pressed on a pin, onto
            // the pin itself, so you stand inside its 20 m; the press lands up
            // to a pin's width off its point. Reaching here over a marker needs
            // patches/react-native-maps+1.29.8.patch.
            onLongPress={
              __DEV__
                ? (e) => {
                    const { latitude: lat, longitude: lng } = e.nativeEvent.coordinate;
                    const slop = (region.latitudeDelta * 111_000 * 24) / Dimensions.get('window').height;
                    let pin: { lat: number; lng: number } | null = null;
                    let best = slop;
                    for (const group of groups) {
                      const away = metersBetween(lat, lng, group.lat, group.lng);
                      if (away <= best) {
                        best = away;
                        pin = group;
                      }
                    }
                    Haptics.selectionAsync().catch(() => {});
                    setHere(pin ? { lat: pin.lat, lng: pin.lng } : { lat, lng });
                    // And 500 steps, for testing the steps gate without walking.
                    deviceId()
                      .then(devSteps)
                      .then((who) => mounted.current && setProfile(who))
                      .catch(() => {});
                  }
                : undefined
            }
          >
            {/* Once, around the person, at the server's radius - never around
                each pin, which would be fifteen overlapping circles and no
                information. No position, nothing to draw. */}
            {position && (
              <Circle
                center={{ latitude: position.lat, longitude: position.lng }}
                radius={radiusMeters}
                strokeWidth={1.5}
                // A Circle takes a real colour, not a platform-resolved one.
                strokeColor={solid(scheme === 'dark').reachStroke}
                fillColor={solid(scheme === 'dark').reachFill}
              />
            )}
            {DEV_PINNED && position && (
              <Marker
                coordinate={{ latitude: position.lat, longitude: position.lng }}
                anchor={{ x: 0.5, y: 0.5 }}
                tracksViewChanges={false}
              >
                <View style={styles.devDot} />
              </Marker>
            )}

            {stage === 'preview' && previewPath.length > 1 && (
              <RouteLine path={previewPath} dark={scheme === 'dark'} />
            )}
            {donePath.length > 1 && <RouteLine path={donePath} dark={scheme === 'dark'} />}

            {groups.map((group) => {
              // The first of a group's memories that is also a route stop -
              // a mixed stack shows the route's number for the whole stack.
              let routePosition: number | null = null;
              for (const memory of group.memories) {
                const at = routePositionById.get(memory.id);
                if (at) {
                  routePosition = at;
                  break;
                }
              }
              const near = reachOf(group, position, earned);
              // Short of steps, standing on it opens nothing: never seal (F11).
              const reach = near === 'unlockable' && short ? 'locked' : near;
              return (
                <MemoryMarker
                  key={group.key}
                  group={group}
                  reach={reach}
                  lit={walking && reach === 'unlockable'}
                  next={
                    walking && group.memories.some((memory) => memory.id === nextRouteStop?.id)
                  }
                  routePosition={routePosition}
                  routeSize={walking ? routeTotal : pins.length}
                  // A preview is a look, not a walk: its stops open once accepted.
                  onPress={() =>
                    !walking && stage !== 'map'
                      ? undefined
                      : group.spanMeters > CLUSTER_SPAN_M
                        ? zoomTo(group)
                        : withinReach.includes(group)
                          ? pickRing(group)
                          : openGroup(group)
                  }
                />
              );
            })}

          </MapView>

          {/* The lock alone, centred over you: you are standing on it. */}
          {ringFor && ringMemory && (
            <UnlockHere
              busy={unlocking}
              onHold={setHolding}
              error={unlockError}
              short={short}
              onSkip={() => setPaywallOpen(true)}
              onUnlock={async () => {
                if (walking) setRouteStarted(true);
                const opened = await unlock(ringMemory);
                setHolding(false);
                if (!opened) return;
                setRevealId(ringMemory.id);
                setPickedId(null);
                // Not openGroup: its tap would land on the hold's Success.
                setOpenAt(ringFor.group.memories);
                setOpenIndex(ringFor.index);
              }}
            />
          )}
          {showRecenter && (
            <GlassButton
              place={styles.recenter}
              style={styles.circle}
              hitSlop={4}
              accessibilityRole="button"
              accessibilityLabel="Center on me"
              onPress={() => {
                Haptics.selectionAsync().catch(() => {});
                const you = positionRef.current;
                if (stage === 'walk') setFollowing(true);
                else if (you) flyTo({ ...region, latitude: you.lat, longitude: you.lng });
              }}
            >
              <Glyph name="location.fill" size={18} weight="medium" color={color.ink} />
            </GlassButton>
          )}

          {walking && !position && (
            <GlassButton
              place={styles.locate}
              style={styles.bigPill}
              tint={color.ember}
              accessibilityRole="button"
              accessibilityLabel="Turn on location"
              accessibilityHint="Asks for permission to use your location"
              onPress={() => {
                if (permission === 'blocked') {
                  Linking.openSettings();
                  return;
                }
                goToMyLocation().catch(() => false);
              }}
            >
              {/* Without location nothing can ever unlock, so the button says so
                  rather than leaving a walk whose stops never open. */}
              <Text style={styles.locateText}>Turn on location</Text>
            </GlassButton>
          )}

          {stage === 'map' && firstPicks.length > 0 && openAt.length === 0 && !journalOpen && (
            <FirstPick
              picks={firstPicks}
              located={!!position}
              onLocate={() => {
                if (permission === 'blocked') {
                  Linking.openSettings();
                  return;
                }
                goToMyLocation().catch(() => false);
              }}
              onPick={(memory) => {
                Haptics.selectionAsync().catch(() => {});
                setOpenAt([memory]);
              }}
            />
          )}

          {/* Not under the journal: iOS 26 draws the slider's glass over covers. */}
          {stage === 'preview' && !journalOpen && (
            <Preview
              stops={preview ? preview.memories.length : null}
              meters={pathMeters(previewPath)}
              km={planKm}
              onKm={walkTo ? setHereKm : setWalkKm}
              ask={walkAsk}
              onAsk={(ask) => {
                setWalkAsk(ask);
                // The server's length was for the other shape of walk.
                setWalkToKm(0);
              }}
              floorKm={walkFloor}
              onPickEnd={() => setStage('end')}
              fallback={planFallback}
              through={walkTo?.place.name ?? null}
              busy={planBusy}
              error={planError}
              onAccept={acceptWalk}
              onNext={
                shownAt < shown.length - 1
                  ? () => showAt(shownAt + 1)
                  : onlyWalk
                    ? null
                    : () => planWalk((shown[shown.length - 1]?.again ?? again) + 1, true)
              }
              onBack={shownAt > 0 ? () => showAt(shownAt - 1) : null}
              walkNumber={shownAt + 1}
              emptyAt={emptyAt}
              onMap={backToMap}
            />
          )}

          {confirmEnd && (
            <EndWalk
              left={routeTotal - routeUnlockedCount}
              busy={planBusy}
              error={planError}
              onEnd={endWalk}
              onKeep={() => {
                setPlanError(null);
                setConfirmEnd(false);
              }}
            />
          )}

          {showDone && (
            <WalkDone
              stops={routeUnlockedCount}
              meters={pathMeters(donePath)}
              loop={!!routeHome}
              minutes={doneMinutes}
              streak={profile?.streak ?? 0}
              onDone={() => setWalkDone(false)}
            />
          )}

          {stage === 'end' && <EndPick onCancel={() => setStage('preview')} />}
          {stage === 'loading' && <View style={styles.cover} />}

          {/* Top centre: what opens memories today. A tap counts again. */}
          {wallet && (
            <StepsPill
              wallet={wallet}
              holding={holding}
              place={[styles.corner, styles.steps]}
              // What it means, and a recount behind it.
              onPress={() => {
                Haptics.selectionAsync().catch(() => {});
                countSteps();
                setHowOpen(true);
              }}
            />
          )}
          {/* Last, so they sit over every card. The bottom is where a thumb
              acts, the top where an eye reads (docs/10, "Act at the bottom,
              read at the top"). Top left the Journal, top right the two rare
              ones. */}
          {(stage === 'map' || stage === 'walk') && !confirmEnd && !showDone && (
            <GlassButton
              place={styles.topLeft}
              style={styles.circle}
              hitSlop={4}
              accessibilityRole="button"
              accessibilityLabel="Journal"
              accessibilityHint={journalNew ? 'Something new on your memories' : undefined}
              onPress={() => {
                Haptics.selectionAsync().catch(() => {});
                setJournalOpen(true);
              }}
            >
              <Glyph name="book.closed" size={20} weight="medium" color={color.ink} />
              {journalNew && <View style={styles.newDot} />}
            </GlassButton>
          )}
          <View style={styles.topRight}>
            {stage === 'map' && <MapFilter shows={mapShows} onShow={setMapShows} />}
            <GlassButton
              style={styles.circle}
              hitSlop={4}
              accessibilityRole="button"
              accessibilityLabel="Settings"
              onPress={() => {
                Haptics.selectionAsync().catch(() => {});
                setSettingsOpen(true);
              }}
            >
              <Glyph name="gearshape" size={20} weight="medium" color={color.ink} />
            </GlassButton>
          </View>
          {/* Two equal halves: Plan a walk before a walk, the walk card on
              one, and Add. Not over a card with its own buttons at the
              bottom. Add is there walk or no walk: filing is standing
              somewhere, not unlocking. */}
          {(stage === 'map' || stage === 'walk') && !confirmEnd && !showDone && (
            <View style={styles.bottom}>
              {stage === 'map' && (
                <GlassButton
                  place={styles.half}
                  style={styles.pill}
                  tint={color.ember}
                  accessibilityRole="button"
                  accessibilityLabel="Plan a walk"
                  onPress={() => {
                    Haptics.selectionAsync().catch(() => {});
                    setWalkTo(null);
                    setWalkToKm(0);
                    setPreview(null);
                    setStage('preview');
                  }}
                >
                  <Glyph name="figure.walk" size={16} weight="semibold" color={color.paper} />
                  <Text style={styles.planText}>Plan a walk</Text>
                </GlassButton>
              )}
              {/* The walk's one card (F9): where next and how far, a tap to see
                  it, and ✕ to end it. Standing on a stop, UnlockHere takes its
                  place and carries its progress line. */}
              {walking && onRoute && !ringMemory && !showDone && !confirmEnd && (
                <GlassButton
                  place={styles.half}
                  style={styles.walkCard}
                  accessible={false}
                  onPress={() => {
                    setRouteStarted(true);
                    setFollowing(true);
                    const you = positionRef.current;
                    if (you) {
                      // Pinned on you, so zoomed out around you, not refitted.
                      flyTo(
                        around(
                          you,
                          nextRouteStop
                            ? [nextRouteStop.place.coordinates]
                            : routeShown.map((memory) => memory.place.coordinates),
                          LOCATED_DELTA / 5,
                        ),
                      );
                    } else if (nextRouteStop) {
                      flyTo({
                        latitude: nextRouteStop.place.coordinates.lat,
                        longitude: nextRouteStop.place.coordinates.lng,
                        latitudeDelta: LOCATED_DELTA,
                        longitudeDelta: LOCATED_DELTA,
                      });
                    } else {
                      mapRef.current?.fitToCoordinates(
                        routeShown.map((memory) => ({
                          latitude: memory.place.coordinates.lat,
                          longitude: memory.place.coordinates.lng,
                        })),
                        { edgePadding: { top: 80, right: 80, bottom: 160, left: 80 }, animated: true },
                      );
                    }
                  }}
                >
                  <View
                    style={styles.walkText}
                    accessible
                    accessibilityRole="button"
                    accessibilityLabel={`${routeLabel}. ${routeProgress}.`}
                    accessibilityHint={
                      routeDone ? 'Shows the whole walk' : 'Shows you and the next stop'
                    }
                  >
                    <Text style={styles.walkNext} numberOfLines={1}>
                      {routeLabel}
                    </Text>
                    <Text style={styles.walkLeft} numberOfLines={1}>
                      {routeProgress}
                    </Text>
                  </View>
                  {/* Nothing left to reach, nothing to lose, so no are-you-sure. */}
                  <CloseButton
                    label="End walk"
                    onPress={() => {
                      Haptics.selectionAsync().catch(() => {});
                      if (routeDone) endWalk();
                      else setConfirmEnd(true);
                    }}
                  />
                </GlassButton>
              )}
              {/* Add keeps its half while the ring has the walk card's. */}
              {stage !== 'map' && !(walking && onRoute && !ringMemory) && (
                <View style={styles.half} />
              )}
              <GlassButton
                place={styles.half}
                style={styles.pill}
                tint={color.ember}
                accessibilityRole="button"
                accessibilityLabel="Add a memory here"
                onPress={async () => {
                  // Without a fix the sheet says "Waiting for your location" and
                  // holds Post until one arrives, which beats a dead tap.
                  if (!positionRef.current) await goToMyLocation().catch(() => false);
                  Haptics.selectionAsync().catch(() => {});
                  setSubmitOpen(true);
                }}
              >
                <Glyph name="plus" size={16} weight="semibold" color={color.paper} />
                <Text style={styles.planText}>Add memory</Text>
              </GlassButton>
            </View>
          )}
        </View>

        <Drawer open={journalOpen} onOpen={() => setJournalOpen(true)} onClose={() => setJournalOpen(false)}>
          <Memories
            device={device}
            profile={profile}
            displayName={displayName}
            unlockedCount={collected.length}
            placeCount={placesUnlocked}
            onEditProfile={() => setProfileOpen(true)}
            streak={profile?.streak ?? 0}
            focused={journalOpen}
            refreshKey={mineVersion}
            unlocked={unlockedByOthers}
            hearted={hearted}
            onOpenMine={openEditor}
            onOpenStop={(memory) => {
              setOpenAt([memory]);
              setOpenIndex(0);
            }}
            onClose={() => setJournalOpen(false)}
            position={position}
          />
        </Drawer>

        <Settings
          visible={settingsOpen}
          onClose={() => setSettingsOpen(false)}
          onSubscribe={() => {
            setSettingsOpen(false);
            setPaywallOpen(true);
          }}
          device={device}
          profile={profile}
          onProfile={accountChanged}
          radiusMeters={radiusMeters}
          permission={permission}
          onRequestLocation={() => {
            if (permission === 'granted' || permission === 'blocked') {
              Linking.openSettings();
              return;
            }
            goToMyLocation().catch(() => false);
          }}
          notifyNearby={notifyNearby}
          onNotifyNearby={handleNotifyNearby}
        />

        <EditProfile
          visible={profileOpen}
          onClose={() => setProfileOpen(false)}
          device={device}
          profile={profile}
          onProfile={accountChanged}
          displayName={displayName}
          onDisplayName={rename}
          nameError={nameError}
        />

        <MemorySheet
          // Only your own, and only while it is open: the locked composition
          // has nowhere to put this.
          onEdit={mine && openMemories[openIndex]?.locked === false ? openEditor : undefined}
          // Only what a person filed, and not your own.
          onReport={openMemories[openIndex]?.author && !mine ? report : undefined}
          reported={reported.has(openMemories[openIndex]?.id ?? -1)}
          onBlock={openMemories[openIndex]?.author && !mine ? block : undefined}
          memories={openMemories}
          index={openIndex}
          onIndex={setOpenIndex}
          onClose={() => setOpenAt([])}
          position={position}
          revealId={revealId}
          compact={!journalOpen}
          onHeart={heart}
          // The map's peek: a walk through that pin, drawn at once.
          onWalkHere={
            stage === 'map'
              ? () => {
                  setWalkTo(openMemories[openIndex] ?? null);
                  setWalkToKm(0);
                  // From the floor: the shortest walk that reaches it.
                  setHereKm(WALK_KM.min);
                  setPlanError(null);
                  setPreview(null);
                  setOpenAt([]);
                  setStage('preview');
                }
              : undefined
          }
          hearted={!!openMemories[openIndex] && hearted.has(openMemories[openIndex].id)}
          freeLeft={profile?.welcome_unlocks ?? 0}
          stepPrice={profile && !profile.subscribed ? profile.steps_per_unlock : undefined}
          stepsShort={short}
          opening={unlocking}
          onOpenFree={async () => {
            const memory = openMemories[openIndex];
            if (!memory || !(await unlock(memory))) return;
            Haptics.notificationAsync(Haptics.NotificationFeedbackType.Success).catch(() => {});
            setRevealId(memory.id);
          }}
        />

        <HowItWorks
          visible={howOpen}
          onClose={() => setHowOpen(false)}
          wallet={wallet}
          profile={profile}
          radiusMeters={radiusMeters}
        />

        <Paywall
          visible={paywallOpen}
          onClose={() => setPaywallOpen(false)}
          device={device}
          onProfile={setProfile}
          stepPrice={profile?.steps_per_unlock ?? 1000}
        />

        <Submit
          visible={submitOpen}
          position={position}
          device={device}
          editing={editingMemory}
          onClose={() => {
            setSubmitOpen(false);
            setEditingMemory(null);
          }}
          onPosted={posted}
          onSaved={saved}
          onDeleted={deleted}
          author={{ name: displayName.trim() || 'Anonymous', avatar_url: profile?.avatar_url }}
        />
      </View>
    </SafeAreaProvider>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: color.paper },
  screen: { flex: 1 },
  devDot: { width: 16, height: 16, borderRadius: 8, borderWidth: 3, borderColor: color.paperRaised, backgroundColor: color.ember },
  // What the map sits behind while the app finds out whether today's walk is
  // already accepted - a flash of the plan page would be a lie.
  cover: { position: 'absolute', top: 0, right: 0, bottom: 0, left: 0, backgroundColor: color.paper },
  // Glass over the map (src/Glass.tsx). `corner` and friends place a
  // control; `pill`, `bigPill` and `circle` are its shape.
  corner: { position: 'absolute', top: 64 },
  steps: { alignSelf: 'center' },
  topLeft: { position: 'absolute', top: 64, left: 18 },
  // The filter left of Settings, so Settings never moves.
  topRight: { position: 'absolute', top: 64, right: 18, flexDirection: 'row', gap: 8 },
  // Edge to edge, two equal halves. At 70, 12pt over Apple's logo and Legal
  // link (HIG Maps asks 10).
  bottom: {
    position: 'absolute',
    bottom: 70,
    left: 18,
    right: 18,
    flexDirection: 'row',
    alignItems: 'center',
    gap: 12,
  },
  half: { flex: 1 },
  pill,
  planText: { ...label, fontSize: 15, color: color.paper },
  // The size of a button, not a pill: it is the one thing to do.
  bigPill: {
    minHeight: 52,
    paddingHorizontal: 24,
    borderRadius: radius.pill,
    alignItems: 'center',
    justifyContent: 'center',
  },
  circle: { width: 44, height: 44, borderRadius: 22, alignItems: 'center', justifyContent: 'center' },
  newDot: {
    position: 'absolute',
    top: 4,
    right: 4,
    width: 10,
    height: 10,
    borderRadius: 5,
    borderWidth: 1.5,
    borderColor: color.paper,
    backgroundColor: color.ember,
  },
  locate: { position: 'absolute', bottom: 134, alignSelf: 'center' },
  locateText: { ...buttonText, color: color.paper },
  // Directly above "Turn on location" while that shows, in its place after.
  walkCard: { ...pill, minHeight: 56, paddingLeft: 20, paddingRight: 12, gap: 12 },
  walkText: { flex: 1, gap: 2 },
  walkNext: { ...label, fontSize: 15, color: color.ink },
  walkLeft: { ...label, fontSize: 13 },
  // Above Add, clear of the walk card's 56pt.
  recenter: { position: 'absolute', right: 18, bottom: 134 },
});
