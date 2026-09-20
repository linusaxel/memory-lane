/** What a coordinate looks like on the map, in its four states.
 *
 * No animation lives in here. Animating a custom marker's children is a known
 * source of flicker in react-native-maps, and a pin that strobes while you walk
 * past it is worse than a pin that simply changes. The pulse belongs in the
 * banner, which is not a marker.
 */

import { StyleSheet, Text, View } from 'react-native';
import { Marker } from 'react-native-maps';

import type { MemoryGroup } from './cluster.ts';
import { groupLabel } from './cluster.ts';

export type Reach = 'open' | 'locked' | 'unlockable';

type Props = {
  group: MemoryGroup;
  reach: Reach;
  onPress: () => void;
};

export default function MemoryMarker({ group, reach, onPress }: Props) {
  const count = group.memories.length;

  return (
    <Marker
      // The reach is part of the key on purpose. tracksViewChanges is off for
      // the frame cost, so the marker only repaints when React gives it a new
      // identity - which is exactly when its state changed.
      key={`${group.key}:${reach}`}
      coordinate={{ latitude: group.lat, longitude: group.lng }}
      title={groupLabel(group)}
      tracksViewChanges={false}
      onPress={onPress}
    >
      {reach === 'open' ? (
        count > 1 && (
          <View style={styles.badge}>
            <Text style={styles.count}>{count}</Text>
          </View>
        )
      ) : (
        <Lock count={count} reachable={reach === 'unlockable'} />
      )}
    </Marker>
  );
}

/** A padlock, drawn rather than set in an emoji font: the shackle has to read
 *  at 30px and the body has to take the state colour, which an emoji will not. */
function Lock({ count, reachable }: { count: number; reachable: boolean }) {
  const size = reachable ? REACHABLE : DISTANT;
  const tint = reachable ? '#f59e0b' : '#a1a1aa';

  return (
    // The one you can open has to survive being covered by the blue location
    // dot, because the pin you are standing on is the pin that matters.
    <View style={[styles.lockWrap, reachable && styles.halo]}>
      <View
        style={[
          styles.shackle,
          { borderColor: tint, width: size * 0.42, height: size * 0.3, top: size * 0.06 },
        ]}
      />
      <View
        style={[
          styles.badge,
          { backgroundColor: tint, width: size, height: size, borderRadius: size / 2 },
        ]}
      >
        <Text style={[styles.count, reachable && styles.countBig]}>{count > 1 ? count : ''}</Text>
      </View>
    </View>
  );
}

const DISTANT = 28;
const REACHABLE = 44;

const styles = StyleSheet.create({
  lockWrap: { alignItems: 'center', justifyContent: 'flex-end', padding: 6 },
  // A soft ring the user-location dot cannot hide behind.
  halo: {
    borderRadius: 34,
    backgroundColor: 'rgba(245,158,11,0.22)',
  },
  shackle: {
    borderWidth: 3,
    borderBottomWidth: 0,
    borderTopLeftRadius: 999,
    borderTopRightRadius: 999,
  },
  badge: {
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
  count: { color: '#fff', fontSize: 13, fontWeight: '700' },
  countBig: { fontSize: 15 },
});
