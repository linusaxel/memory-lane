import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { ActivityIndicator, Pressable, StyleSheet, Text, View } from 'react-native';
import MapView, { Marker } from 'react-native-maps';
import * as Location from 'expo-location';
import { StatusBar } from 'expo-status-bar';

import { fetchNearby, unlockMemory, type Coordinates, type LocatedMemory } from './src/api.ts';
import { groupByLocation, groupLabel, type MemoryGroup } from './src/cluster.ts';
import { metersBetween, regionToRadiusKm, type Region } from './src/region.ts';
import { loadUnlocked, rememberUnlocked, type Unlocked } from './src/unlocked.ts';
import MemorySheet from './src/MemorySheet.tsx';

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

/** Three pin states, because a map that looks the same whether or not you can
 *  read a memory makes you tap every pin to find out. */
type Reach = 'open' | 'locked' | 'unlockable';

export default function App() {
  const [region, setRegion] = useState<Region>(FALLBACK_REGION);
  const [memories, setMemories] = useState<LocatedMemory[]>([]);
  // What was tapped is a point, not a memory: the sheet pages through it.
  const [openAt, setOpenAt] = useState<LocatedMemory[]>([]);
  const [openIndex, setOpenIndex] = useState(0);
  const [status, setStatus] = useState<Status>('loading');
  const [position, setPosition] = useState<Coordinates | null>(null);
  const [unlocked, setUnlocked] = useState<Unlocked>({});
  const [unlocking, setUnlocking] = useState(false);
  const [unlockError, setUnlockError] = useState<string | null>(null);

  const mapRef = useRef<MapView>(null);
  const debounce = useRef<ReturnType<typeof setTimeout> | null>(null);
  const latestRequest = useRef(0);
  const mounted = useRef(true);
  // load() must not be rebuilt every time the person moves, or the mount effect
  // that calls it would re-run and re-centre the map underneath them.
  const positionRef = useRef<Coordinates | null>(null);

  useEffect(() => {
    return () => {
      mounted.current = false;
      if (debounce.current) clearTimeout(debounce.current);
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
      const found = await fetchNearby(
        r.latitude,
        r.longitude,
        regionToRadiusKm(r),
        positionRef.current,
      );
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

  const goToMyLocation = useCallback(async () => {
    const { status: permission } = await Location.requestForegroundPermissionsAsync();
    if (permission !== 'granted') return false;

    const pos = await Location.getCurrentPositionAsync({});
    positionRef.current = { lat: pos.coords.latitude, lng: pos.coords.longitude };
    setPosition(positionRef.current);
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
  }, [load]);

  useEffect(() => {
    (async () => {
      const centred = await goToMyLocation().catch(() => false);
      // Permission denied, or location unavailable: show the fallback region
      // rather than an empty map.
      if (!centred) load(FALLBACK_REGION);
    })();
  }, [goToMyLocation, load]);

  const onRegionChangeComplete = useCallback(
    (r: Region) => {
      setRegion(r);
      if (debounce.current) clearTimeout(debounce.current);
      debounce.current = setTimeout(() => load(r), DEBOUNCE_MS);
    },
    [load],
  );

  useEffect(() => {
    loadUnlocked().then((stored) => {
      if (mounted.current) setUnlocked(stored);
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

  const reachOf = (group: MemoryGroup): Reach => {
    const locked = group.memories.filter((memory) => memory.locked);
    if (locked.length === 0) return 'open';
    if (!position) return 'locked';
    const away = metersBetween(position.lat, position.lng, group.lat, group.lng);
    return away <= (locked[0].unlock_radius_meters ?? 150) ? 'unlockable' : 'locked';
  };

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
        ? 'Finding memories\u2026'
        : memories.length === 0
          ? 'No memories here yet'
          : `${memories.length} ${memories.length === 1 ? 'memory' : 'memories'} here`;

  return (
    <View style={styles.container}>
      <StatusBar style="dark" />

      <MapView
        ref={mapRef}
        style={StyleSheet.absoluteFill}
        initialRegion={FALLBACK_REGION}
        showsUserLocation
        onRegionChangeComplete={onRegionChangeComplete}
      >
        {groups.map((group) => {
          const reach = reachOf(group);
          const count = group.memories.length;
          return (
            <Marker
              key={group.key}
              coordinate={{ latitude: group.lat, longitude: group.lng }}
              title={groupLabel(group)}
              onPress={() => openGroup(group)}
            >
              {reach === 'open' ? (
                count > 1 && (
                  <View style={styles.cluster}>
                    <Text style={styles.clusterText}>{count}</Text>
                  </View>
                )
              ) : (
                <View style={[styles.cluster, reach === 'locked' ? styles.far : styles.reachable]}>
                  <Text style={styles.clusterText}>{count > 1 ? count : '\u25cf'}</Text>
                </View>
              )}
            </Marker>
          );
        })}
      </MapView>

      <View style={styles.banner} pointerEvents="none">
        <Text style={styles.bannerText}>{bannerText}</Text>
        {status === 'loading' && <ActivityIndicator size="small" color="#71717a" />}
      </View>

      {status === 'failed' ? (
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
  );
}

const styles = StyleSheet.create({
  container: { flex: 1 },
  banner: {
    position: 'absolute',
    top: 64,
    alignSelf: 'center',
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
    backgroundColor: 'rgba(255,255,255,0.94)',
    paddingHorizontal: 16,
    paddingVertical: 9,
    borderRadius: 20,
    shadowColor: '#000',
    shadowOpacity: 0.12,
    shadowRadius: 8,
    shadowOffset: { width: 0, height: 2 },
    elevation: 3,
  },
  bannerText: { fontSize: 14, color: '#3f3f46', fontWeight: '500' },
  locate: {
    position: 'absolute',
    bottom: 44,
    alignSelf: 'center',
    backgroundColor: '#18181b',
    paddingHorizontal: 22,
    paddingVertical: 13,
    borderRadius: 24,
    shadowColor: '#000',
    shadowOpacity: 0.2,
    shadowRadius: 10,
    shadowOffset: { width: 0, height: 3 },
    elevation: 4,
  },
  locateText: { color: '#fff', fontSize: 15, fontWeight: '600' },
  // Sits on the default pin so a stack is countable before it is tapped.
  cluster: {
    minWidth: 26,
    height: 26,
    paddingHorizontal: 6,
    borderRadius: 13,
    backgroundColor: '#18181b',
    borderWidth: 2,
    borderColor: '#fff',
    alignItems: 'center',
    justifyContent: 'center',
  },
  clusterText: { color: '#fff', fontSize: 13, fontWeight: '700' },
  // Locked reads as inert; unlockable reads as the one thing worth walking to.
  far: { backgroundColor: '#a1a1aa' },
  reachable: { backgroundColor: '#f59e0b' },
});
