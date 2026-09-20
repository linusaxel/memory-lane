import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import {
  ActivityIndicator,
  Linking,
  Platform,
  Pressable,
  StyleSheet,
  Text,
  View,
} from 'react-native';
import MapView from 'react-native-maps';
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

import { fetchNearby, unlockMemory, type Coordinates, type LocatedMemory } from './src/api.ts';
import { groupByLocation, type MemoryGroup } from './src/cluster.ts';
import { MUTED_ANDROID_STYLE } from './src/mapStyle.ts';
import { FALLBACK_RADIUS_M, nearestLocked, reachOf } from './src/reach.ts';
import { regionToRadiusKm, type Region } from './src/region.ts';
import {
  inUnlockOrder,
  loadUnlocked,
  primerWasDismissed,
  rememberPrimerDismissed,
  rememberUnlocked,
  type Unlocked,
} from './src/unlocked.ts';
import Collection from './src/Collection.tsx';
import Settings from './src/Settings.tsx';
import { color, font } from './src/theme.ts';
import LocationPrimer from './src/LocationPrimer.tsx';
import TabBar, { type Tab } from './src/TabBar.tsx';
import MemoryMarker from './src/MemoryMarker.tsx';
import MemorySheet from './src/MemorySheet.tsx';
import ReachBanner from './src/ReachBanner.tsx';

/**
 * Where to look when we have no location permission. A blank grey map is a
 * store-review rejection, and reviewers routinely tap Deny - so this points at
 * Manhattan, where the seeded content actually is.
 */
const FALLBACK_REGION: Region = {
  latitude: 40.7484,
  longitude: -73.9857,
  latitudeDelta: 0.09,
  longitudeDelta: 0.09,
};

const DEBOUNCE_MS = 400;

/** Separate, because "nothing here" and "we could not ask" must not look alike. */
type Status = 'loading' | 'ready' | 'failed';

/** 'blocked' is the one that cannot be fixed by asking again - only Settings. */
type Permission = 'unknown' | 'granted' | 'denied' | 'blocked';

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

  const [region, setRegion] = useState<Region>(FALLBACK_REGION);
  const [memories, setMemories] = useState<LocatedMemory[]>([]);
  // What was tapped is a point, not a memory: the sheet pages through it.
  const [openAt, setOpenAt] = useState<LocatedMemory[]>([]);
  const [openIndex, setOpenIndex] = useState(0);
  const [status, setStatus] = useState<Status>('loading');
  const [position, setPosition] = useState<Coordinates | null>(null);
  const [permission, setPermission] = useState<Permission>('unknown');
  const [primerDismissed, setPrimerDismissed] = useState(false);
  const [unlocked, setUnlocked] = useState<Unlocked>({});
  const [unlocking, setUnlocking] = useState(false);
  const [unlockError, setUnlockError] = useState<string | null>(null);
  const [tab, setTab] = useState<Tab>('map');

  const mapRef = useRef<MapView>(null);
  const debounce = useRef<ReturnType<typeof setTimeout> | null>(null);
  const latestRequest = useRef(0);
  const mounted = useRef(true);
  // load() must not be rebuilt every time the person moves, or the mount effect
  // that calls it would re-run and re-centre the map underneath them.
  const positionRef = useRef<Coordinates | null>(null);
  const watcher = useRef<Location.LocationSubscription | null>(null);

  useEffect(() => {
    return () => {
      mounted.current = false;
      if (debounce.current) clearTimeout(debounce.current);
      watcher.current?.remove();
    };
  }, []);

  const load = useCallback(async (r: Region) => {
    // Responses can land out of order: a slow request for the region you just
    // left resolves after a fast one for the region you are looking at, and
    // overwrites it - including stamping 'failed' over a newer success. Only
    // the most recent request is allowed to write.
    const request = ++latestRequest.current;
    const isStale = () => !mounted.current || request !== latestRequest.current;

    setStatus('loading');
    try {
      const found = await fetchNearby(r.latitude, r.longitude, regionToRadiusKm(r));
      if (isStale()) return;
      setMemories(found);
      setStatus('ready');
    } catch {
      if (isStale()) return;
      // Keep the last good pins. They are still true of the place, and a map
      // that empties itself on a dropped request looks like the area went
      // blank rather than the network.
      setStatus('failed');
    }
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
    watcher.current = await Location.watchPositionAsync(
      // The radius is 150m, so a finer interval spends battery to tell us
      // nothing. Foreground only - see rule 2 in UI.md.
      { accuracy: Location.Accuracy.Balanced, distanceInterval: 25 },
      remember,
    );
  }, [remember]);

  const goToMyLocation = useCallback(async () => {
    const granted = await Location.requestForegroundPermissionsAsync();
    if (granted.status !== 'granted') {
      setPermission(granted.canAskAgain ? 'denied' : 'blocked');
      return false;
    }
    setPermission('granted');

    const pos = await Location.getCurrentPositionAsync({});
    remember(pos);
    watchPosition();
    const next: Region = {
      latitude: pos.coords.latitude,
      longitude: pos.coords.longitude,
      latitudeDelta: 0.09,
      longitudeDelta: 0.09,
    };
    mapRef.current?.animateToRegion(next, 600);
    setRegion(next);
    load(next);
    return true;
  }, [load, remember, watchPosition]);

  useEffect(() => {
    (async () => {
      // Never the system dialog first. Someone who already said yes should not
      // be asked again, so check silently and only prime a genuine newcomer.
      const existing = await Location.getForegroundPermissionsAsync().catch(() => null);
      if (!mounted.current) return;

      if (existing?.granted) {
        const centred = await goToMyLocation().catch(() => false);
        if (!centred) load(FALLBACK_REGION);
        return;
      }

      setPermission(existing && !existing.canAskAgain ? 'blocked' : 'denied');
      // The map is real and populated behind the primer - see rule 1 in UI.md.
      load(FALLBACK_REGION);
    })();
  }, [goToMyLocation, load]);

  useEffect(() => {
    loadUnlocked().then((stored) => {
      if (mounted.current) setUnlocked(stored);
    });
    primerWasDismissed().then((dismissed) => {
      if (mounted.current && dismissed) setPrimerDismissed(true);
    });
  }, []);

  const onRegionChangeComplete = useCallback(
    (r: Region) => {
      setRegion(r);
      if (debounce.current) clearTimeout(debounce.current);
      debounce.current = setTimeout(() => load(r), DEBOUNCE_MS);
    },
    [load],
  );

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
  // The radius is the server's, so read it off a memory rather than restating
  // it here - a number in two places is a number that will disagree.
  const radiusMeters =
    memories.find((memory) => memory.unlock_radius_meters)?.unlock_radius_meters ??
    FALLBACK_RADIUS_M;

  const openGroup = (group: MemoryGroup) => {
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
        const opened = await unlockMemory(memory.id, at);
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
        <StatusBar style="dark" />

        {/* Both tabs stay mounted. Unmounting the map means refetching, losing
            the viewport and re-animating to GPS every time somebody glances at
            their collection - a tab switch should cost nothing. */}
        <View style={[styles.screen, tab !== 'map' && styles.hidden]}>
          <MapView
            ref={mapRef}
            style={StyleSheet.absoluteFill}
            initialRegion={FALLBACK_REGION}
            showsUserLocation={permission === 'granted'}
            // See src/mapStyle.ts: the map is a backdrop, not a competitor.
            mapType={Platform.OS === 'ios' ? 'mutedStandard' : 'standard'}
            customMapStyle={MUTED_ANDROID_STYLE}
            showsPointsOfInterests={false}
            onRegionChangeComplete={onRegionChangeComplete}
          >
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

          {showPrimer ? (
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
          ) : status === 'failed' ? (
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
          memories={openMemories}
          index={openIndex}
          onIndex={setOpenIndex}
          onClose={() => setOpenAt([])}
          position={position}
          onUnlock={unlock}
          unlocking={unlocking}
          unlockError={unlockError}
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
  locateText: {
    color: color.paper,
    fontFamily: font.monoBold,
    fontSize: 12,
    letterSpacing: 1.2,
    textTransform: 'uppercase',
  },
});
