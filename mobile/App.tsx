import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import {
  ActivityIndicator,
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
  fetchStats,
  fetchProfile,
  fetchUnlocked,
  reportMemory,
  saveDisplayName,
  unlockMemory,
  type Coordinates,
  type Hotspot,
  type LocatedMemory,
  type Profile,
} from './src/api.ts';
import { groupByLocation, type MemoryGroup } from './src/cluster.ts';
import { MUTED_ANDROID_STYLE } from './src/mapStyle.ts';
import { FALLBACK_RADIUS_M, nearestLocked, reachOf } from './src/reach.ts';
import type { Region } from './src/region.ts';
import {
  inUnlockOrder,
  loadUnlocked,
  mergeUnlocked,
  primerWasDismissed,
  rememberPrimerDismissed,
  rememberUnlocked,
  type Unlocked,
} from './src/unlocked.ts';
import Collection from './src/Collection.tsx';
import { deviceId } from './src/device.ts';
import Elsewhere from './src/Elsewhere.tsx';
import Settings from './src/Settings.tsx';
import Submit from './src/Submit.tsx';
import { buttonText, color, font, label } from './src/theme.ts';
import LocationPrimer from './src/LocationPrimer.tsx';
import TabBar, { type Tab } from './src/TabBar.tsx';
import { useNearby } from './src/useNearby.ts';
import type { Permission, Status } from './src/types.ts';
import { useMapCamera } from './src/useMapCamera.ts';
import MemoryMarker from './src/MemoryMarker.tsx';
import MemorySheet from './src/MemorySheet.tsx';
import ReachBanner from './src/ReachBanner.tsx';

/**
 * Where to look when we have no location permission. A blank grey map is a
 * store-review rejection, and reviewers routinely tap Deny - so this points at
 * Manhattan, where the seeded content actually is.
 *
 * Deliberately left wide. With no position nothing can unlock and there is no
 * reach circle to draw, so the only useful thing this state can say is "here is
 * roughly where the memories are".
 */
const FALLBACK_REGION: Region = {
  latitude: 40.7484,
  longitude: -73.9857,
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

  const { region, setRegion, memories, status, load, reload, onRegionChangeComplete } =
    useNearby(FALLBACK_REGION);
  // What was tapped is a point, not a memory: the sheet pages through it.
  const [openAt, setOpenAt] = useState<LocatedMemory[]>([]);
  const [openIndex, setOpenIndex] = useState(0);
  const [position, setPosition] = useState<Coordinates | null>(null);
  const [permission, setPermission] = useState<Permission>('unknown');
  const [primerDismissed, setPrimerDismissed] = useState(false);
  const [unlocked, setUnlocked] = useState<Unlocked>({});
  const [unlocking, setUnlocking] = useState(false);
  const [unlockError, setUnlockError] = useState<string | null>(null);
  const [hotspots, setHotspots] = useState<Hotspot[]>([]);
  // What the server says the gate radius is. Only /v1/stats can answer when
  // there is nothing on the map, and the circle is drawn either way.
  const [serverRadius, setServerRadius] = useState<number | null>(null);
  // Resolved once at launch. Held in state rather than awaited at each call
  // site because the submit form needs it synchronously to decide whether it
  // can open at all.
  const [device, setDevice] = useState<string | null>(null);
  const [displayName, setDisplayName] = useState('');
  const [profile, setProfile] = useState<Profile | null>(null);
  const [submitOpen, setSubmitOpen] = useState(false);
  // Reported by this device already. Local only - the server counts devices,
  // and this stops the control offering a second press that does nothing.
  const [reported, setReported] = useState<Set<number>>(new Set());
  // Only the handful of values the palette cannot carry need this: the map's
  // own appearance, and the two rgba literals a MapView Circle insists on.
  const scheme = useColorScheme();
  const [tab, setTab] = useState<Tab>('map');

  const { mapRef, flyTo, onMapReady } = useMapCamera();
  const mounted = useRef(true);
  // load() must not be rebuilt every time the person moves, or the mount effect
  // that calls it would re-run and re-centre the map underneath them.
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

  const remember = useCallback((pos: Location.LocationObject) => {
    positionRef.current = { lat: pos.coords.latitude, lng: pos.coords.longitude };
    if (mounted.current) setPosition(positionRef.current);
  }, []);

  /** Walking into range has to change the map by itself. A position read once
   *  at launch means a pin only turns unlockable if you happen to press
   *  "Near me" while standing on it, which is the opposite of the mechanic. */
  const watchPosition = useCallback(async () => {
    if (watcher.current) return;
    try {
      watcher.current = await Location.watchPositionAsync(
        // The radius is 150m, so a finer interval spends battery to tell us
        // nothing. Foreground only - see rule 2 in UI.md.
        { accuracy: Location.Accuracy.Balanced, distanceInterval: 25 },
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
    // "Near me" button calls it straight from onPress, so an unhandled
    // rejection was the whole error handling.
    let pos;
    try {
      pos = await Location.getCurrentPositionAsync({});
    } catch {
      return false;
    }
    remember(pos);
    watchPosition();
    const next: Region = {
      latitude: pos.coords.latitude,
      longitude: pos.coords.longitude,
      latitudeDelta: LOCATED_DELTA,
      longitudeDelta: LOCATED_DELTA,
    };
    // No load() here. animateToRegion fires onRegionChangeComplete when it
    // lands, and it does not land on `next` - the map fits the deltas to the
    // screen, so the region it settles on covers noticeably more ground. Asking
    // eagerly meant two requests for one press, the first of them for a
    // viewport that never actually exists.
    flyTo(next);
    setRegion(next);
    return true;
  }, [flyTo, remember, watchPosition]);

  useEffect(() => {
    (async () => {
      // Never the system dialog first. Someone who already said yes should not
      // be asked again, so check silently and only prime a genuine newcomer.
      const existing = await Location.getForegroundPermissionsAsync().catch(() => null);
      if (!mounted.current) return;

      if (existing?.granted) {
        const centred = await goToMyLocation().catch(() => false);
        // Only this branch loads by hand: nothing moved the camera, so nothing
        // is going to report a region change.
        if (!centred) load(FALLBACK_REGION);
        return;
      }

      setPermission(existing && !existing.canAskAgain ? 'blocked' : 'denied');
      // The map is real and populated behind the primer - see rule 1 in UI.md.
      load(FALLBACK_REGION);
    })();
  }, [goToMyLocation, load]);

  // Only once the map has actually come up empty. Asking on launch would spend
  // a request on the common case, where there is something here already.
  const nothingHere = status === 'ready' && memories.length === 0;
  useEffect(() => {
    if (!nothingHere || hotspots.length > 0) return;
    fetchStats()
      .then((stats) => {
        if (!mounted.current) return;
        setHotspots(stats.hotspots);
        if (stats.unlock_radius_meters) setServerRadius(stats.unlock_radius_meters);
      })
      .catch(() => {});
  }, [nothingHere, hotspots.length]);

  useEffect(() => {
    loadUnlocked().then((stored) => {
      if (mounted.current) setUnlocked(stored);
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
    primerWasDismissed().then((dismissed) => {
      if (mounted.current && dismissed) setPrimerDismissed(true);
    });
  }, []);

  // What the device has earned wins over what the server is willing to say now:
  // walking away must not take a memory back.
  const shown = useMemo(
    () => memories.map((memory) => unlocked[memory.id] ?? memory),
    [memories, unlocked],
  );
  const groups = useMemo(() => groupByLocation(shown), [shown]);
  const openMemories = useMemo(
    () => openAt.map((memory) => unlocked[memory.id] ?? memory),
    [openAt, unlocked],
  );

  const withinReach = useMemo(
    () => groups.filter((group) => reachOf(group, position) === 'unlockable'),
    [groups, position],
  );
  const collected = useMemo(() => inUnlockOrder(unlocked), [unlocked]);

  const nearest = useMemo(() => nearestLocked(groups, position), [groups, position]);

  const placesUnlocked = useMemo(
    () => new Set(collected.map((memory) => memory.place.id)).size,
    [collected],
  );
  // Always the server's, never ours. Every memory now carries it; /v1/stats is
  // the fallback for a viewport with no memories in it at all, and
  // FALLBACK_RADIUS_M only for the moments before either has answered.
  const radiusMeters =
    memories.find((memory) => memory.unlock_radius_meters)?.unlock_radius_meters ??
    serverRadius ??
    FALLBACK_RADIUS_M;

  const openGroup = (group: MemoryGroup) => {
    // A pin is a small target on a moving map, and a tap that lands has to feel
    // different from one that misses. The heavier taps are reserved for the
    // unlock, so this is the lightest one there is.
    Haptics.selectionAsync().catch(() => {});
    setOpenAt(group.memories);
    setOpenIndex(0);
    setUnlockError(null);
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
    [unlocked],
  );

  const posted = useCallback(
    async (memory: LocatedMemory) => {
      // Already unlocked by the server - filing something is standing there -
      // so it goes straight into the collection.
      setUnlocked(await rememberUnlocked(unlocked, memory));
      setProfile((who) => (who ? { ...who, submitted: who.submitted + 1 } : who));
      // Show them what they filed. The modal closing is not a confirmation,
      // and this is also the first sight of what anybody else will find here.
      setOpenAt([memory]);
      setOpenIndex(0);
      // The new pin is not in `memories` until the map asks again, and the
      // viewport has not changed - so this has to be a reload, not a load.
      reload(region);
    },
    [region, reload, unlocked],
  );

  const report = useCallback(
    async (memory: LocatedMemory) => {
      if (!device) return;
      // Optimistic: a report that silently did nothing is worse than one that
      // says it landed and did not. It is idempotent per device either way.
      setReported((current) => new Set(current).add(memory.id));
      reportMemory(memory.id, device).catch(() => {});
    },
    [device],
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
      if (device) saveDisplayName(device, next).catch(() => {});
    },
    [device],
  );

  const bannerText =
    status === 'failed'
      ? "Can't reach Memory Lane"
      : status === 'loading' && memories.length === 0
        ? 'Finding memories…'
        : memories.length === 0
          ? 'No memories here yet'
          : `${memories.length} ${memories.length === 1 ? 'memory' : 'memories'} here`;

  const showPrimer = permission !== 'granted' && !primerDismissed;

  if (!fontsReady) return null;

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
        <View style={[styles.screen, tab !== 'map' && styles.hidden]}>
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
            onRegionChangeComplete={onRegionChangeComplete}
            onMapReady={onMapReady}
          >
            {/* Once, around the person, at the server's radius - never around
                each pin, which would be fifteen overlapping circles and no
                information. No position, nothing to draw. */}
            {position && (
              <Circle
                center={{ latitude: position.lat, longitude: position.lng }}
                radius={radiusMeters}
                strokeWidth={1.5}
                // Not from the palette: a Circle takes a real colour, not a
                // platform-resolved one, and the seal needs more presence on a
                // dark map than on parchment.
                strokeColor={scheme === 'dark' ? 'rgba(226,96,63,0.7)' : 'rgba(192,70,43,0.55)'}
                fillColor={scheme === 'dark' ? 'rgba(226,96,63,0.12)' : 'rgba(192,70,43,0.07)'}
              />
            )}

            {groups.map((group) => (
              <MemoryMarker
                key={group.key}
                group={group}
                reach={reachOf(group, position)}
                onPress={() => openGroup(group)}
              />
            ))}
          </MapView>

          <View style={styles.banner} pointerEvents="none">
            <Text style={styles.bannerText}>{bannerText}</Text>
            {status === 'loading' && <ActivityIndicator size="small" color={color.inkFaint} />}
          </View>

          {/* Top right, because every other overlay on this screen lives at the
              bottom and this one must never be the thing covering the unlock.
              Shown even with no position: standing somewhere empty is the best
              moment to file the first memory there, and the press asks for
              location rather than hiding the possibility. */}
          {!showPrimer && (
            <Pressable
              style={styles.add}
              accessibilityRole="button"
              accessibilityLabel="Add a memory here"
              onPress={async () => {
                if (!positionRef.current && !(await goToMyLocation().catch(() => false))) return;
                Haptics.selectionAsync().catch(() => {});
                setSubmitOpen(true);
              }}
            >
              <Text style={styles.addText}>+ Add</Text>
            </Pressable>
          )}

          {!showPrimer && withinReach.length > 0 && (
            <ReachBanner
              count={withinReach.length}
              meters={null}
              onPress={() => openGroup(withinReach[0])}
            />
          )}
          {!showPrimer && withinReach.length === 0 && nearest && (
            <ReachBanner
              count={null}
              meters={nearest.meters}
              onPress={() => openGroup(nearest.group)}
            />
          )}

          {/* The empty state outranks the primer. "Walk within 150 m of a pin"
              is a promise about pins that are not there, and asking for
              location to unlock nothing is the wrong first impression. Once
              there is something on the map, the primer gets its turn. */}
          {nothingHere && (
            <Elsewhere
              hotspots={hotspots}
              from={{ lat: region.latitude, lng: region.longitude }}
              onGo={(hotspot) => {
                const next: Region = {
                  latitude: hotspot.lat,
                  longitude: hotspot.lng,
                  // Wide enough to take in a metro area, because the point is
                  // "here is the place", not "here is one pin in it".
                  latitudeDelta: 0.12,
                  longitudeDelta: 0.12,
                };
                flyTo(next, 900);
                setRegion(next);
              }}
            />
          )}

          {showPrimer && !nothingHere ? (
            <LocationPrimer
              blocked={permission === 'blocked'}
              onAllow={() => {
                if (permission === 'blocked') {
                  Linking.openSettings();
                  return;
                }
                goToMyLocation().catch(() => false);
              }}
              onDismiss={() => {
                setPrimerDismissed(true);
                rememberPrimerDismissed();
              }}
            />
          ) : nothingHere ? null : status === 'failed' ? (
            <Pressable style={styles.locate} onPress={() => load(region)}>
              <Text style={styles.locateText}>Try again</Text>
            </Pressable>
          ) : (
            <Pressable style={styles.locate} onPress={goToMyLocation}>
              {/* Without location nothing can ever unlock, so the button says so
                  rather than leaving a map of pins that never open. */}
              <Text style={styles.locateText}>{position ? 'Near me' : 'Turn on location'}</Text>
            </Pressable>
          )}
        </View>

        <View style={[styles.screen, tab !== 'collection' && styles.hidden]}>
          <Collection
            memories={collected}
            onOpen={(memory) => {
              // One memory, not its point: the collection is a list of things
              // you earned, and a stack of strangers at the same coordinate is
              // not that.
              setOpenAt([memory]);
              setOpenIndex(0);
            }}
          />
        </View>

        <View style={[styles.screen, tab !== 'you' && styles.hidden]}>
          <Settings
            unlockedCount={collected.length}
            placeCount={placesUnlocked}
            submittedCount={profile?.submitted ?? 0}
            displayName={displayName}
            onDisplayName={rename}
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
          />
        </View>

        <TabBar tab={tab} unlockedCount={collected.length} onSelect={setTab} />

        <MemorySheet
          // Only offered when the sheet was opened from the collection: over
          // the map you are already looking at the answer.
          onShowOnMap={
            tab === 'collection'
              ? (memory) => {
                  const next: Region = {
                    latitude: memory.place.coordinates.lat,
                    longitude: memory.place.coordinates.lng,
                    latitudeDelta: LOCATED_DELTA,
                    longitudeDelta: LOCATED_DELTA,
                  };
                  setOpenAt([]);
                  setTab('map');
                  setRegion(next);
                  flyTo(next);
                }
              : undefined
          }
          // Only what a person filed. There is nobody to report a podcast to,
          // and offering it on all 224 extracted memories would make the
          // control read as general feedback rather than a takedown.
          onReport={openMemories[openIndex]?.author ? report : undefined}
          reported={reported.has(openMemories[openIndex]?.id ?? -1)}
          memories={openMemories}
          index={openIndex}
          onIndex={setOpenIndex}
          onClose={() => setOpenAt([])}
          position={position}
          onUnlock={unlock}
          unlocking={unlocking}
          unlockError={unlockError}
        />

        <Submit
          visible={submitOpen}
          position={position}
          device={device}
          displayName={displayName}
          onDisplayName={rename}
          onClose={() => setSubmitOpen(false)}
          onPosted={posted}
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
  // A paper tab, ruled rather than shadowed. Editorial layouts use rules and
  // weight for hierarchy; the floating translucent card is the thing every
  // generated interface reaches for first.
  banner: {
    position: 'absolute',
    top: 64,
    alignSelf: 'center',
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
    backgroundColor: color.paper,
    borderWidth: 1,
    borderColor: color.rule,
    paddingHorizontal: 16,
    paddingVertical: 9,
    borderRadius: 4,
  },
  bannerText: {
    fontFamily: font.monoMedium,
    fontSize: 12,
    letterSpacing: 0.3,
    color: color.inkSoft,
  },
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
});
