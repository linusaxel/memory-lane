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
import Padlock from './Padlock.tsx';
import { color, font } from './theme.ts';
import type { Reach } from './reach.ts';

const STATE_LABEL: Record<Reach, string> = {
  open: 'Open',
  locked: 'Locked, too far to open',
  unlockable: 'Locked, within reach',
};

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
      // The callout title says where; only the colour says whether you can read
      // it, and colour is not available to everyone.
      accessibilityLabel={`${groupLabel(group)}. ${STATE_LABEL[reach]}.`}
      tracksViewChanges={false}
      onPress={onPress}
    >
      {reach === 'open' ? (
        count > 1 && (
          <View style={[styles.badge, styles.open]}>
            <Text style={styles.count}>{count}</Text>
          </View>
        )
      ) : (
        <Lock count={count} reachable={reach === 'unlockable'} />
      )}
    </Marker>
  );
}

function Lock({ count, reachable }: { count: number; reachable: boolean }) {
  // Out of reach: a solid grey disc. In reach: a ring the blue location dot
  // sits *inside*, which is the only shape that survives being stood on - and
  // the pin you are standing on is the pin that matters. It also echoes the
  // ring in the sheet, so the map and the control are visibly the same object.
  if (!reachable) {
    return (
      <View style={styles.lockWrap}>
        <View style={[styles.badge, styles.distant]}>
          {count > 1 ? (
            <Text style={styles.count}>{count}</Text>
          ) : (
            <Padlock size={DISTANT * 0.34} color={color.paper} />
          )}
        </View>
      </View>
    );
  }

  return (
    <View style={[styles.lockWrap, styles.halo]}>
      <View style={styles.ring} />
      <View style={styles.tag}>
        {count > 1 ? (
          <Text style={styles.count}>{count}</Text>
        ) : (
          <Padlock size={10} color={color.paper} />
        )}
      </View>
    </View>
  );
}

const DISTANT = 28;
const REACHABLE = 44;

const styles = StyleSheet.create({
  lockWrap: { alignItems: 'center', justifyContent: 'center', padding: 7 },
  // A soft glow so the pin is findable before you can read its shape.
  // A literal rather than a palette entry: this is a translucent wash and the
  // seal's dark value is lighter, so one alpha over both reads about the same.
  halo: { borderRadius: 40, backgroundColor: 'rgba(192,70,43,0.16)' },
  badge: {
    minWidth: 26,
    height: 26,
    paddingHorizontal: 6,
    borderRadius: 13,
    borderWidth: 2,
    borderColor: color.paper,
    alignItems: 'center',
    justifyContent: 'center',
  },
  open: { backgroundColor: color.ink },
  distant: {
    backgroundColor: color.faded,
    width: DISTANT,
    height: DISTANT,
    borderRadius: DISTANT / 2,
  },
  ring: {
    width: REACHABLE,
    height: REACHABLE,
    borderRadius: REACHABLE / 2,
    borderWidth: 5,
    borderColor: color.seal,
    backgroundColor: color.paper,
  },
  // Offset to the corner, because the middle is where the blue dot lands.
  tag: {
    position: 'absolute',
    top: 0,
    right: 0,
    minWidth: 20,
    height: 20,
    paddingHorizontal: 5,
    borderRadius: 10,
    backgroundColor: color.sealDeep,
    borderWidth: 2,
    borderColor: color.paper,
    alignItems: 'center',
    justifyContent: 'center',
  },
  count: { color: color.paper, fontFamily: font.monoBold, fontSize: 11 },
});
