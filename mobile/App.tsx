import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import {
  Animated,
  Linking,
  Platform,
  Pressable,
  StyleSheet,
  Text,
  View,
  useColorScheme,
} from 'react-native';
import MapView, { Circle } from 'react-native-maps';
import * as Haptics from 'expo-haptics';
import * as Location from 'expo-location';
import * as SplashScreen from 'expo-splash-screen';
import { StatusBar } from 'expo-status-bar';
import { useFonts } from 'expo-font';
import {
  Fraunces_400Regular,
  Fraunces_600SemiBold,
  Fraunces_700Bold,
} from '@expo-google-fonts/fraunces';
import {
  IBMPlexMono_400Regular,
  IBMPlexMono_500Medium,
  IBMPlexMono_600SemiBold,
} from '@expo-google-fonts/ibm-plex-mono';
import { SafeAreaProvider } from 'react-native-safe-area-context';

import {
  acceptRoute,
  fetchProfile,
  fetchTodaysRoute,
  fetchUnlocked,
  heartMemory,
  previewRoute,
  saveDisplayName,
  unlockMemory,
  type Coordinates,
  type LocatedMemory,
  type Profile,
  type TodaysRoute,
  type WalkAsk,
  type WalkedRoute,
} from './src/api.ts';
import { CLUSTER_SPAN_M, groupByLocation, type MemoryGroup, precisionFor } from './src/cluster.ts';
import { devLocation } from './src/devLocation.ts';
import { devOpenMemory, devOpenScreen, devOpenTab } from './src/devOpen.ts';
import { startWatching, stopWatching } from './src/geofence.ts';
import { loadHearted, rememberHearted } from './src/hearted.ts';
import { MUTED_ANDROID_STYLE } from './src/mapStyle.ts';
import { FALLBACK_RADIUS_M, reachOf } from './src/reach.ts';
import { around, metersBetween, pathMeters, type Region } from './src/region.ts';
import { loadNotifyNearby, saveNotifyNearby } from './src/notifyNearby.ts';
import { loadRoute, saveRoute } from './src/route.ts';
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
import { Plan, Preview, WALK_KM, WalkDone } from './src/Plan.tsx';
import Settings from './src/Settings.tsx';
import Submit from './src/Submit.tsx';
import { distance, walkDate } from './src/format.ts';
import { buttonText, color, dim, font, label } from './src/theme.ts';
import TabBar, { type Tab } from './src/TabBar.tsx';
import type { Permission } from './src/types.ts';
import { useMapCamera } from './src/useMapCamera.ts';
import { useNearby } from './src/useNearby.ts';
import MemoryMarker from './src/MemoryMarker.tsx';
import MemorySheet from './src/MemorySheet.tsx';
import NextStopArrow from './src/NextStopArrow.tsx';
import { useBreath } from './src/useBreath.ts';
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
 *  it for "Show me another" taps. */
const ROLLS = 1_000_000;

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

/** Plan the walk, preview it, walk it. `loading` is the moment before the
 *  device knows whether it already accepted today's walk. */
type Stage = 'loading' | 'plan' | 'preview' | 'walk';

export default function App() {
  // Two families carry the whole design, so there is no sensible half-loaded
  // state - the splash stays up the few hundred ms this takes.
  const [fontsReady] = useFonts({
    Fraunces_400Regular,
    Fraunces_600SemiBold,
    Fraunces_700Bold,
    IBMPlexMono_400Regular,
    IBMPlexMono_500Medium,
    IBMPlexMono_600SemiBold,
  });
  const [logoDone, setLogoDone] = useState(false);

  // Only for grouping pins at the zoom they are seen at.
  const [region, setRegion] = useState<Region>(FALLBACK_REGION);
  const [stage, setStage] = useState<Stage>('loading');
  const [walkKm, setWalkKm] = useState(WALK_KM.initial);
  const [walkAsk, setWalkAsk] = useState<WalkAsk>({ loop: true, tag: null });
  // Where the previewed walk starts, and whether that is central
  // Copenhagen standing in for a position we could not have.
  const [planFrom, setPlanFrom] = useState<Coordinates | null>(null);
  const [planFallback, setPlanFallback] = useState(false);
  // Which of the walks as good this preview is: a fresh roll for every plan,
  // one up for "Show me another", and the accept sends the same.
  const [again, setAgain] = useState(0);
  // "Show me another" came back unchanged: that was the only walk that long.
  const [onlyWalk, setOnlyWalk] = useState(false);
  const [preview, setPreview] = useState<TodaysRoute | null>(null);
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
  // Local convenience only, for a heart button that starts filled on
  // relaunch - the server's memory_hearts row is the durable fact.
  const [hearted, setHearted] = useState<Set<number>>(new Set());
  // Whether the local store has answered yet. Until it has, the collection must
  // not claim to be empty - see Memories' `unlockedReady`.
  const [collectionReady, setCollectionReady] = useState(false);
  const [nameError, setNameError] = useState<string | null>(null);
  const [unlocking, setUnlocking] = useState(false);
  const [unlockError, setUnlockError] = useState<string | null>(null);
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
  // Street shapes between consecutive stops; null draws them straight.
  const [routeLegs, setRouteLegs] = useState<Coordinates[][] | null>(null);
  // A walk from the Walks list, drawn over Explore instead of what is nearby.
  // Read-only: Explore unlocks nothing. Any tab change puts it away.
  const [pastWalk, setPastWalk] = useState<WalkedRoute | null>(null);
  // Resolved once at launch. Held in state rather than awaited at each call
  // site because the submit form needs it synchronously to decide whether it
  // can open at all.
  const [device, setDevice] = useState<string | null>(null);
  const [displayName, setDisplayName] = useState('');
  const [profile, setProfile] = useState<Profile | null>(null);
  const [submitOpen, setSubmitOpen] = useState(false);
  // Set to open Submit as an editor for this memory instead of a blank form.
  // Null means Submit is either closed or filing something new.
  const [editingMemory, setEditingMemory] = useState<LocatedMemory | null>(null);
  // Bumped after a post, a save or a delete so Memories' "My memories" section
  // refetches without the tab having to be left and come back to.
  const [mineVersion, setMineVersion] = useState(0);
  // Only the handful of values the palette cannot carry need this: the map's
  // own appearance, and the two rgba literals a MapView Circle insists on.
  const scheme = useColorScheme();
  const [tab, setTab] = useState<Tab>('walk');

  // Region reports go through the camera, not straight from the map: a move
  // replayed from onMapReady never reports itself and the map still announces
  // where it was born. See src/useMapCamera.ts.
  const { mapRef, flyTo, inFlight, onMapReady, onRegionChangeComplete } =
    useMapCamera(setRegion);
  // Walk and Explore share the one MapView (rule 9) but not a camera: each
  // keeps where it was left. Explore's first visit centres on you.
  const cameraOf = useRef<Partial<Record<Tab, Region>>>({});
  const mapTab = useRef<Tab>('walk');
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
    loadUnlocked().then((stored) => {
      if (!mounted.current) return;
      setUnlocked(stored);
      setCollectionReady(true);
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
          })
          .catch(() => {});
        const earned = await fetchUnlocked(id);
        if (!mounted.current || earned.length === 0) return;
        setUnlocked(await mergeUnlocked(earned));
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
            preview.loop ? planFrom : null,
            { out: preview.out_leg, home: preview.home_leg },
          )
        : [],
    [preview, planFrom],
  );

  /** Make `walk` today's route, on screen and in the local cache. `start` is
   *  where it was planned from - the server never stores it. */
  const takeRoute = useCallback(
    (walk: TodaysRoute, start: Coordinates | null) => {
      setRoute(walk.memories);
      setRouteSize(walk.size);
      setRouteLegs(walk.legs);
      setRouteHome(walk.loop ? start : null);
      saveRoute({
        route_date: walk.route_date,
        memories: walk.memories,
        loop: walk.loop,
        legs: walk.legs,
        start: start ?? undefined,
      });
    },
    [],
  );

  // Whether today's walk was already accepted: the cached copy first, so a
  // relaunch lands on it at once, then the server, which is the authority.
  // With neither, today starts at the plan page.
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
        setStage('walk');
      }
      try {
        const accepted = await fetchTodaysRoute(device);
        if (!mounted.current) return;
        if (accepted) {
          takeRoute(accepted, cached?.start ?? null);
          setStage('walk');
        } else if (!cached) {
          setStage('plan');
        }
      } catch {
        if (mounted.current && !cached) setStage('plan');
      }
    })();
  }, [device, takeRoute]);

  const planWalk = useCallback(async (next: number, another = false) => {
    if (!device) return;
    setPlanBusy(true);
    setPlanError(null);
    let from = positionRef.current;
    if (!from && (await goToMyLocation().catch(() => false))) from = positionRef.current;
    const fallback = !from;
    const anchor = from ?? { lat: FALLBACK_REGION.latitude, lng: FALLBACK_REGION.longitude };
    try {
      const walk = await previewRoute(device, anchor, walkKm * 1000, walkAsk, next);
      if (!mounted.current) return;
      const ids = (route: TodaysRoute | null) => route?.memories.map((m) => m.id).join();
      setAgain(next);
      setOnlyWalk(another && ids(walk) === ids(preview));
      setPlanFrom(anchor);
      setPlanFallback(fallback);
      setPreview(walk);
      setStage('preview');
    } catch {
      if (mounted.current) setPlanError("Can't reach Memory Lane right now.");
    } finally {
      if (mounted.current) setPlanBusy(false);
    }
  }, [device, goToMyLocation, walkKm, walkAsk, preview]);

  const acceptWalk = useCallback(async () => {
    if (!device || !planFrom) return;
    setPlanBusy(true);
    setPlanError(null);
    try {
      const walk = await acceptRoute(device, planFrom, walkKm * 1000, walkAsk, again);
      if (!mounted.current) return;
      takeRoute(walk, planFrom);
      setPreview(null);
      setStage('walk');
    } catch {
      if (mounted.current) setPlanError("Can't reach Memory Lane right now.");
    } finally {
      if (mounted.current) setPlanBusy(false);
    }
  }, [device, planFrom, walkKm, walkAsk, again, takeRoute]);

  // The preview's zoom: the whole loop and its start, clear of the card.
  useEffect(() => {
    if (stage !== 'preview' || !preview || !planFrom) return;
    mapRef.current?.fitToCoordinates(
      [planFrom, ...preview.memories.map((memory) => memory.place.coordinates)].map((c) => ({
        latitude: c.lat,
        longitude: c.lng,
      })),
      { edgePadding: { top: 100, right: 60, bottom: 300, left: 60 }, animated: true },
    );
  }, [stage, preview, planFrom, mapRef]);

  // Ids, not memories: reachOf only asks whether this device walked to it, and
  // a Set keeps that an O(1) question inside three passes over every group.
  const earned = useMemo(() => new Set(Object.keys(unlocked).map(Number)), [unlocked]);
  // What the device has earned wins over what the server said when the route
  // was made, so a stop reads as earned the moment it is.
  const routeShown = useMemo(
    () => route.map((memory) => unlocked[memory.id] ?? memory),
    [route, unlocked],
  );
  // The only pins there are: the walk being previewed, or the walk being
  // walked. Nothing off the route is drawn.
  const pins = useMemo(
    () => (stage === 'preview' ? (preview?.memories ?? []) : stage === 'walk' ? routeShown : []),
    [stage, preview, routeShown],
  );
  // The background watch tracks today's route, not the map's panned viewport -
  // bounded (ROUTE_SIZE, well under the OS's ~20-region cap), already "nearby
  // things to walk to", and it does not change every time somebody pans the
  // map. Re-registers whenever a stop is earned, so an already-unlocked stop
  // drops out of the watch the next time this runs rather than lingering.
  useEffect(() => {
    if (!notifyNearby) return;
    startWatching(routeShown).catch(() => {});
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
    () => pathThrough(position, routeShown, earned, routeLegs, routeHome),
    [routeShown, earned, position, routeHome, routeLegs],
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
  const routeLabel = routeDone
    ? `Route walked · ${routeUnlockedCount} of ${routeTotal}`
    : routeStarted && nextRouteStop
      ? `Next: ${nextRouteStop.place.name}` +
        (toNextStop === null ? '' : ` · ${distance(toNextStop)}`)
      : `Today's route · ${routeUnlockedCount} of ${routeTotal}` +
        (routeLeft === null ? '' : ` · ${distance(routeLeft)}`);
  // Banded, so panning inside one zoom level does not regroup: `region` changes
  // on every gesture, ahead of the fetch debounce.
  const precision = precisionFor(region.latitudeDelta);
  const selectTab = useCallback(
    (next: Tab, to?: Region) => {
      setTab(next);
      setPastWalk(null);
      if ((next !== 'walk' && next !== 'explore') || next === mapTab.current) return;
      cameraOf.current[mapTab.current] = region;
      mapTab.current = next;
      const here = positionRef.current;
      const back =
        to ??
        cameraOf.current[next] ??
        (here && {
          latitude: here.lat,
          longitude: here.lng,
          latitudeDelta: LOCATED_DELTA,
          longitudeDelta: LOCATED_DELTA,
        });
      if (back) flyTo(back);
    },
    [region, flyTo],
  );
  const groups = useMemo(() => groupByLocation(pins, precision), [pins, precision]);

  // On the walk the camera is pinned on the person: it follows them, cannot be
  // dragged off them, and a pinch that drifts the centre is put back. Where the
  // next stop is off screen, NextStopArrow points the way instead.
  const pinned = tab === 'walk' && stage === 'walk' && !!position && !walkDone;
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
  // Explore: everything under the viewport, whatever today's walk is. What
  // this device earned reads open, as it does on the walk.
  const nearby = useNearby(region, tab === 'explore' && !pastWalk);
  const exploreGroups = useMemo(
    () =>
      groupByLocation(
        (pastWalk?.memories ?? nearby).map((memory) => unlocked[memory.id] ?? memory),
        precision,
      ),
    [pastWalk, nearby, unlocked, precision],
  );
  // Stop to stop: the start was never stored (docs/10 § Routes).
  const pastPath = useMemo(
    () => (pastWalk ? pathThrough(null, pastWalk.memories, NONE, pastWalk.legs, null) : []),
    [pastWalk],
  );
  useEffect(() => {
    if (pastPath.length === 0) return;
    mapRef.current?.fitToCoordinates(
      pastPath.map((c) => ({ latitude: c.lat, longitude: c.lng })),
      { edgePadding: { top: 100, right: 60, bottom: 200, left: 60 }, animated: true },
    );
  }, [pastPath, mapRef]);
  const openMemories = useMemo(
    () => openAt.map((memory) => unlocked[memory.id] ?? memory),
    [openAt, unlocked],
  );
  // After the last stop's sheet is closed, not over it: that memory is read first.
  const showDone = walkDone && tab === 'walk' && openAt.length === 0;
  // The whole walk, from the start and home on a loop; stop to stop one-way.
  const donePath = useMemo(
    () => (showDone ? pathThrough(routeHome, routeShown, NONE, routeLegs, routeHome) : []),
    [showDone, routeShown, routeLegs, routeHome],
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
  // Both sides have to be a real id: an extracted memory's author is null and
  // a signed-out profile's user_id is undefined, and undefined === undefined
  // would otherwise call every extracted memory yours before the profile has
  // even loaded.
  const mine =
    !!openMemories[openIndex]?.author?.id &&
    !!profile?.user_id &&
    openMemories[openIndex].author?.id === profile.user_id;

  // EXPO_PUBLIC_DEV_OPEN_SCREEN, under __DEV__ only. The submit sheet is three
  // taps in and there are no taps, so without this it could only be read as
  // source. Mount-only: it sets where you land, not where you stay.
  useEffect(() => {
    const screen = devOpenScreen();
    if (!screen) return;
    const next = devOpenTab(screen);
    setTab(next);
    if (next === 'explore') mapTab.current = next;
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
  const devOpened = useRef(false);
  useEffect(() => {
    const id = devOpenMemory();
    if (id == null || devOpened.current) return;
    const group = (tab === 'explore' ? exploreGroups : groups).find((g) =>
      g.memories.some((memory) => memory.id === id),
    );
    if (!group) return;
    devOpened.current = true;
    setOpenAt(group.memories);
    setOpenIndex(group.memories.findIndex((memory) => memory.id === id));
  }, [tab, groups, exploreGroups]);

  const withinReach = useMemo(
    () =>
      stage === 'walk'
        ? groups.filter((group) => reachOf(group, position, earned) === 'unlockable')
        : [],
    [stage, groups, position, earned],
  );
  const collected = useMemo(() => inUnlockOrder(unlocked), [unlocked]);

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
  const pillBreath = useBreath(stopHere !== null);
  const pillSlot = position && { bottom: 44 };

  // Reaching a stop is the moment the app is for. The transition, not the
  // state: stopHere gets a new identity on every 25m position update. Light,
  // because the heavier taps belong to the unlock itself.
  const inReach = stopHere !== null;
  const wasInReach = useRef(false);
  useEffect(() => {
    if (inReach && !wasInReach.current) {
      Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Light).catch(() => {});
    }
    wasInReach.current = inReach;
  }, [inReach]);

  const placesUnlocked = useMemo(
    () => new Set(collected.map((memory) => memory.place.id)).size,
    [collected],
  );
  // Always the server's, never ours: every memory carries it. FALLBACK_RADIUS_M
  // only for the moments before a route has answered.
  const radiusMeters =
    [...route, ...(preview?.memories ?? [])].find((memory) => memory.unlock_radius_meters)
      ?.unlock_radius_meters ?? FALLBACK_RADIUS_M;

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
    async (memory: LocatedMemory) => {
      const at = positionRef.current;
      if (!at) return;

      setUnlocking(true);
      setUnlockError(null);
      try {
        const opened = await unlockMemory(memory.id, at, await deviceId());
        if (!mounted.current) return;
        if (opened) {
          // This was the last not-yet-earned stop of a started route: the same
          // success haptic UnlockButton fires for one memory
          // (src/UnlockButton.tsx:105-107), once more - an affirmation on the
          // unlock that already happened, not a new mechanic.
          if (
            routeStarted &&
            nextRouteStop?.id === memory.id &&
            routeShown.every((stop) => stop.id === memory.id || earned.has(stop.id))
          ) {
            Haptics.notificationAsync(Haptics.NotificationFeedbackType.Success).catch(() => {});
            setWalkDone(true);
            // The streak the card shows, counting today.
            deviceId()
              .then(fetchProfile)
              .then((who) => mounted.current && setProfile(who))
              .catch(() => {});
          }
          setUnlocked(await rememberUnlocked(unlocked, opened));
        } else {
          // The server re-measures, and GPS moves between the press and the
          // request. Silence here would read as a broken button.
          setUnlockError('Not close enough yet - try a few steps nearer.');
        }
      } catch {
        if (mounted.current) setUnlockError("Can't reach Memory Lane right now.");
      } finally {
        if (mounted.current) setUnlocking(false);
      }
    },
    [unlocked, routeStarted, nextRouteStop, routeShown, earned],
  );

  const heart = useCallback(
    async (memory: LocatedMemory) => {
      try {
        const count = await heartMemory(memory.id, await deviceId());
        if (!mounted.current) return;
        setHearted(await rememberHearted(hearted, memory.id));
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

  const posted = useCallback(
    async (memory: LocatedMemory) => {
      // Already unlocked by the server - filing something is standing there -
      // so it goes straight into the collection.
      setUnlocked(await rememberUnlocked(unlocked, memory));
      setProfile((who) => (who ? { ...who, submitted: who.submitted + 1 } : who));
      setMineVersion((v) => v + 1);
      // Show them what they filed. The modal closing is not a confirmation,
      // and this is also the first sight of what anybody else will find here.
      setOpenAt([memory]);
      setOpenIndex(0);
    },
    [unlocked],
  );

  /** Opens Submit as an editor rather than a blank form - the Memories tab
   *  and the map sheet both lead here. */
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
        .catch(() => setNameError('Could not save your name. Keep typing to try again.'));
    },
    [device],
  );

  const walking = stage === 'walk';

  if (!fontsReady) return null;

  if (!logoDone) {
    return (
      <StartupLogo
        onDone={() => setLogoDone(true)}
      />
    );
  }

  return (
    <SafeAreaProvider>
      <View style={styles.container}>
        {/* "auto" rather than "dark": the bar has to invert with everything
            else, and hardcoding it is how an app ends up with black glyphs on a
            black background at night. */}
        <StatusBar style="auto" />

        {/* Every tab stays mounted. Unmounting the map means refetching, losing
            the viewport and re-animating to GPS on every glance at the
            collection - a tab switch should cost nothing. */}
        <View style={[styles.screen, tab !== 'walk' && tab !== 'explore' && styles.hidden]}>
          <MapView
            ref={mapRef}
            style={StyleSheet.absoluteFill}
            initialRegion={FALLBACK_REGION}
            showsUserLocation={permission === 'granted'}
            // See src/mapStyle.ts: the map is a backdrop, not a competitor.
            mapType={Platform.OS === 'ios' ? 'mutedStandard' : 'standard'}
            // Apple Maps follows the system on its own, but only if it is not
            // told otherwise; naming it here keeps the default explicit.
            userInterfaceStyle={scheme === 'dark' ? 'dark' : 'light'}
            customMapStyle={MUTED_ANDROID_STYLE}
            showsPointsOfInterests={false}
            scrollEnabled={!pinned}
            rotateEnabled={!pinned}
            pitchEnabled={!pinned}
            onRegionChangeComplete={onRegionChangeComplete}
            onMapReady={onMapReady}
          >
            {/* Once, around the person, at the server's radius - never around
                each pin, which would be fifteen overlapping circles and no
                information. No position, nothing to draw. */}
            {tab === 'walk' && position && (
              <Circle
                center={{ latitude: position.lat, longitude: position.lng }}
                radius={radiusMeters}
                strokeWidth={1.5}
                // Not from the palette: a Circle takes a real colour, not a
                // platform-resolved one, and the seal needs more presence on a
                // dark map than on parchment.
                strokeColor={scheme === 'dark' ? 'rgba(217,165,75,0.7)' : 'rgba(138,90,23,0.55)'}
                fillColor={scheme === 'dark' ? 'rgba(217,165,75,0.12)' : 'rgba(138,90,23,0.07)'}
              />
            )}

            {tab === 'walk' && stage === 'preview' && previewPath.length > 1 && (
              <RouteLine path={previewPath} dark={scheme === 'dark'} />
            )}
            {donePath.length > 1 && <RouteLine path={donePath} dark={scheme === 'dark'} />}
            {tab === 'explore' && pastPath.length > 1 && (
              <RouteLine path={pastPath} dark={scheme === 'dark'} />
            )}

            {(tab === 'walk' ? groups : []).map((group) => {
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
              const reach = reachOf(group, position, earned);
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
                    !walking
                      ? undefined
                      : group.spanMeters > CLUSTER_SPAN_M
                        ? zoomTo(group)
                        : openGroup(group)
                  }
                />
              );
            })}

            {(tab === 'explore' ? exploreGroups : []).map((group) => {
              // Nothing is earned in Explore, so nothing reads as nearly or
              // already openable: the walk is where a stop opens.
              const reach = reachOf(group, position, earned);
              return (
                <MemoryMarker
                  key={group.key}
                  group={group}
                  reach={reach === 'unlockable' || reach === 'warm' ? 'locked' : reach}
                  lit={false}
                  onPress={() =>
                    group.spanMeters > CLUSTER_SPAN_M ? zoomTo(group) : openGroup(group)
                  }
                />
              );
            })}
          </MapView>

          {pinned && nextRouteStop && (
            <NextStopArrow
              region={region}
              target={nextRouteStop.place.coordinates}
              dark={scheme === 'dark'}
            />
          )}

          {/* Top right, because every other overlay on this screen lives at the
              bottom and this one must never be the thing covering the unlock.
              Shown even with no position: standing somewhere empty is the best
              moment to file the first memory there, and the press asks for
              location rather than hiding the possibility. */}
          {/* Explore too: filing is standing somewhere, not unlocking. */}
          {((walking && tab === 'walk') || (tab === 'explore' && !pastWalk)) && (
            <Pressable
              style={dim(styles.add)}
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
              <Text style={styles.addText}>+ Add</Text>
            </Pressable>
          )}

          {/* In the same bottom slot every other floating control here shares -
              never a second region of the screen. Above "Turn on location"
              while that shows, in its place once there is a position. */}
          {walking && tab === 'walk' && onRoute && stopHere && (
            <Animated.View style={[styles.routeAt, pillSlot, pillBreath]}>
              <Pressable
                style={dim()}
                accessibilityRole="button"
                accessibilityLabel={`You're at stop ${stopHere.position}: ${stopHere.name}. Open to unlock.`}
                onPress={() => {
                  setRouteStarted(true);
                  // At the stop's own page: in a stack, the route memory is
                  // not necessarily the first one.
                  openGroup(stopHere.group, stopHere.index);
                }}
              >
                <Text style={styles.routeAtText}>
                  {`You're at stop ${stopHere.position} · open it`}
                </Text>
              </Pressable>
            </Animated.View>
          )}
          {walking && tab === 'walk' && onRoute && !stopHere && !showDone && (
            <Pressable
              style={dim([styles.route, pillSlot])}
              accessibilityRole="button"
              accessibilityLabel={
                routeDone
                  ? `Route walked · ${routeUnlockedCount} of ${routeTotal} unlocked.`
                  : routeStarted && nextRouteStop
                    ? `Next stop: ${nextRouteStop.place.name}.`
                    : `Today's route · ${routeUnlockedCount} of ${routeTotal} unlocked.`
              }
              accessibilityHint={
                routeDone
                  ? 'Shows the whole route'
                  : routeStarted
                    ? 'Centers the map on you and the next stop'
                    : "Starts today's route"
              }
              onPress={() => {
                setRouteStarted(true);
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
              <Text style={styles.routeText}>{routeLabel}</Text>
            </Pressable>
          )}

          {tab === 'explore' && pastWalk && (
            <Pressable
              style={dim([styles.route, { bottom: 44 }])}
              accessibilityRole="button"
              accessibilityLabel={`Walk of ${walkDate(pastWalk.route_date)}, ${pastWalk.earned} of ${pastWalk.size}. Close.`}
              onPress={() => selectTab('collection')}
            >
              <Text style={styles.routeText}>
                {`${walkDate(pastWalk.route_date)} · ${pastWalk.earned} of ${pastWalk.size} · Close`}
              </Text>
            </Pressable>
          )}

          {walking && tab === 'walk' && !position && (
            <Pressable
              style={dim(styles.locate)}
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
            </Pressable>
          )}

          {tab === 'walk' && stage === 'preview' && preview && (
            <Preview
              stops={preview.memories.length}
              meters={pathMeters(previewPath)}
              loop={preview.loop}
              fallback={planFallback}
              busy={planBusy}
              error={planError}
              onAccept={acceptWalk}
              onAnother={onlyWalk ? null : () => planWalk(again + 1, true)}
              onBack={() => {
                setPlanError(null);
                setStage('plan');
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

          {/* Opaque, over a map that stays mounted behind it (rule 9). */}
          {tab === 'walk' && stage === 'plan' && (
            <Plan
              km={walkKm}
              onKm={setWalkKm}
              ask={walkAsk}
              onAsk={setWalkAsk}
              onGo={() => planWalk(Math.floor(Math.random() * ROLLS))}
              busy={planBusy}
              error={planError}
            />
          )}
          {tab === 'walk' && stage === 'loading' && <View style={styles.cover} />}
        </View>

        <View style={[styles.screen, tab !== 'collection' && styles.hidden]}>
          <Memories
            unlocked={collected}
            unlockedReady={collectionReady}
            onOpenUnlocked={(memory) => {
              // One memory, not its point: the collection is a list of things
              // you earned, and a stack of strangers at the same coordinate is
              // not that.
              setOpenAt([memory]);
              setOpenIndex(0);
            }}
            device={device}
            focused={tab === 'collection'}
            refreshKey={mineVersion}
            onOpenMine={openEditor}
            onOpenWalk={(walk) => {
              selectTab('explore');
              setPastWalk(walk);
            }}
            position={position}
          />
        </View>

        <View style={[styles.screen, tab !== 'you' && styles.hidden]}>
          <Settings
            unlockedCount={collected.length}
            placeCount={placesUnlocked}
            submittedCount={profile?.submitted ?? 0}
            displayName={displayName}
            onDisplayName={rename}
            nameError={nameError}
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
        </View>

        <TabBar tab={tab} unlockedCount={collected.length} onSelect={selectTab} />

        <MemorySheet
          earned={!!openMemories[openIndex] && earned.has(openMemories[openIndex].id)}
          // Only your own, and only while it is open - a sealed one shows the
          // locked composition instead, which has nowhere to put this.
          onEdit={mine && openMemories[openIndex]?.locked === false ? openEditor : undefined}
          memories={openMemories}
          index={openIndex}
          onIndex={setOpenIndex}
          onClose={() => setOpenAt([])}
          position={position}
          // Explore opens the sheet locked with no ring: unlocking is Walk's.
          onUnlock={tab === 'walk' ? unlock : undefined}
          walkStop={
            tab === 'explore' && walking && openMemories[openIndex]
              ? routePositionById.get(openMemories[openIndex].id)
              : undefined
          }
          onShowOnWalk={(memory) => {
            setOpenAt([]);
            const you = positionRef.current;
            selectTab(
              'walk',
              you
                ? around(you, [memory.place.coordinates], LOCATED_DELTA)
                : {
                    latitude: memory.place.coordinates.lat,
                    longitude: memory.place.coordinates.lng,
                    latitudeDelta: LOCATED_DELTA,
                    longitudeDelta: LOCATED_DELTA,
                  },
            );
          }}
          unlocking={unlocking}
          unlockError={unlockError}
          onHeart={heart}
          hearted={!!openMemories[openIndex] && hearted.has(openMemories[openIndex].id)}
        />

        <Submit
          visible={submitOpen}
          position={position}
          device={device}
          displayName={displayName}
          onDisplayName={rename}
          editing={editingMemory}
          onClose={() => {
            setSubmitOpen(false);
            setEditingMemory(null);
          }}
          onPosted={posted}
          onSaved={saved}
          onDeleted={deleted}
        />
      </View>
    </SafeAreaProvider>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: color.paper },
  screen: { flex: 1 },
  // display:none rather than unmounting: the map keeps its region and its pins.
  hidden: { display: 'none' },
  // What the map sits behind while the app finds out whether today's walk is
  // already accepted - a flash of the plan page would be a lie.
  cover: { position: 'absolute', top: 0, right: 0, bottom: 0, left: 0, backgroundColor: color.paper },
  // Paper and a rule, like the banner it sits beside - the seal belongs to the
  // unlock and writing is not that.
  add: {
    position: 'absolute',
    // Level with the banner, which sits at the same top and is the only other
    // thing up here.
    top: 64,
    right: 18,
    backgroundColor: color.paper,
    borderWidth: 1,
    borderColor: color.rule,
    paddingHorizontal: 14,
    paddingVertical: 11,
    borderRadius: 4,
  },
  addText: { ...label, color: color.ink },
  locate: {
    position: 'absolute',
    bottom: 44,
    alignSelf: 'center',
    backgroundColor: color.ink,
    paddingHorizontal: 26,
    paddingVertical: 14,
    borderRadius: 4,
    shadowColor: '#000',
    shadowOpacity: 0.18,
    shadowRadius: 14,
    shadowOffset: { width: 0, height: 6 },
    elevation: 5,
  },
  locateText: { ...buttonText, color: color.paper },
  // Directly above "Turn on location", sharing its shadow token - UI.md's rule is that
  // only two shadows exist in this app, and this is the same kind of small
  // solid control as the one it sits on.
  route: {
    position: 'absolute',
    bottom: 100,
    alignSelf: 'center',
    backgroundColor: color.paper,
    borderWidth: 1,
    borderColor: color.rule,
    paddingHorizontal: 16,
    paddingVertical: 9,
    borderRadius: 4,
    shadowColor: '#000',
    shadowOpacity: 0.18,
    shadowRadius: 14,
    shadowOffset: { width: 0, height: 6 },
    elevation: 5,
  },
  routeText: {
    fontFamily: font.monoMedium,
    fontSize: 12,
    letterSpacing: 0.3,
    color: color.inkSoft,
  },
  // The route pill's one loud moment: the reach banner's seal, in its slot.
  routeAt: { position: 'absolute', bottom: 100, alignSelf: 'center' },
  routeAtText: {
    paddingHorizontal: 16,
    paddingVertical: 9,
    borderRadius: 4,
    overflow: 'hidden',
    fontFamily: font.monoBold,
    fontSize: 12,
    letterSpacing: 1,
    textTransform: 'uppercase',
    backgroundColor: color.seal,
    color: color.paper,
  },
});
