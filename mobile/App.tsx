import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { ActivityIndicator, Pressable, StyleSheet, Text, View } from 'react-native';
import MapView, { Marker } from 'react-native-maps';
import * as Location from 'expo-location';
import { StatusBar } from 'expo-status-bar';

import { fetchNearby, type LocatedMemory } from './src/api.ts';
import { groupByLocation, groupLabel, type MemoryGroup } from './src/cluster.ts';
import { regionToRadiusKm, type Region } from './src/region.ts';
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

export default function App() {
  const [region, setRegion] = useState<Region>(FALLBACK_REGION);
  const [memories, setMemories] = useState<LocatedMemory[]>([]);
  // What was tapped is a point, not a memory: the sheet pages through it.
  const [openAt, setOpenAt] = useState<LocatedMemory[]>([]);
  const [openIndex, setOpenIndex] = useState(0);
  const [status, setStatus] = useState<Status>('loading');

  const mapRef = useRef<MapView>(null);
  const debounce = useRef<ReturnType<typeof setTimeout> | null>(null);
  const latestRequest = useRef(0);
  const mounted = useRef(true);

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

  const goToMyLocation = useCallback(async () => {
    const { status: permission } = await Location.requestForegroundPermissionsAsync();
    if (permission !== 'granted') return false;

    const pos = await Location.getCurrentPositionAsync({});
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

  const groups = useMemo(() => groupByLocation(memories), [memories]);

  const openGroup = (group: MemoryGroup) => {
    setOpenAt(group.memories);
    setOpenIndex(0);
  };

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
        {groups.map((group) => (
          <Marker
            key={group.key}
            coordinate={{ latitude: group.lat, longitude: group.lng }}
            title={groupLabel(group)}
            onPress={() => openGroup(group)}
          >
            {group.memories.length > 1 && (
              <View style={styles.cluster}>
                <Text style={styles.clusterText}>{group.memories.length}</Text>
              </View>
            )}
          </Marker>
        ))}
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
          <Text style={styles.locateText}>Near me</Text>
        </Pressable>
      )}

      <MemorySheet
        memories={openAt}
        index={openIndex}
        onIndex={setOpenIndex}
        onClose={() => setOpenAt([])}
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
});
