/** What an empty map should say instead of nothing.
 *
 * The corpus is one comedy podcast's touring history: New York, then a long
 * tail. Open the app anywhere else and every screen is correct and blank. "No
 * memories here yet" is honest and it is a dead end - the person has no way to
 * know whether the app is broken, empty, or simply not about where they are.
 *
 * So the empty state names the nearest place that is not empty, and takes you
 * there. Looking is not unlocking: you still cannot read anything until you are
 * standing somewhere, which is the whole product. But you can see that it
 * exists.
 */

import { Pressable, StyleSheet, Text, View } from 'react-native';

import type { Coordinates, Hotspot } from './api.ts';
import { distance } from './format.ts';
import { metersBetween } from './region.ts';
import { color, font, label } from './theme.ts';

type Props = {
  hotspots: Hotspot[];
  /** Where the map is looking, so "nearest" means nearest to what you can see. */
  from: Coordinates;
  onGo: (hotspot: Hotspot) => void;
};

function distanceLabel(from: Coordinates, hotspot: Hotspot): string {
  return distance(metersBetween(from.lat, from.lng, hotspot.lat, hotspot.lng), {
    suffix: 'away',
  });
}

export default function Elsewhere({ hotspots, from, onGo }: Props) {
  if (hotspots.length === 0) return null;

  const nearest = [...hotspots].sort(
    (a, b) =>
      metersBetween(from.lat, from.lng, a.lat, a.lng) -
      metersBetween(from.lat, from.lng, b.lat, b.lng),
  )[0];

  return (
    <View style={styles.card}>
      <Text style={styles.kicker}>Nothing here</Text>
      <Text style={styles.title}>
        The closest memories are in {nearest.label}
      </Text>
      <Text style={styles.body}>
        {nearest.memories} of them, {distanceLabel(from, nearest)}. You still have to stand there
        to read one.
      </Text>
      <Pressable style={styles.go} onPress={() => onGo(nearest)} accessibilityRole="button">
        <Text style={styles.goText}>Show me {nearest.label}</Text>
      </Pressable>
    </View>
  );
}

const styles = StyleSheet.create({
  card: {
    position: 'absolute',
    left: 16,
    right: 16,
    bottom: 26,
    backgroundColor: color.paper,
    borderWidth: 1,
    borderColor: color.rule,
    borderRadius: 6,
    padding: 22,
    gap: 8,
    shadowColor: '#000',
    shadowOpacity: 0.14,
    shadowRadius: 18,
    shadowOffset: { width: 0, height: 8 },
    elevation: 6,
  },
  kicker: { ...label },
  title: { fontFamily: font.display, fontSize: 21, lineHeight: 28, color: color.ink },
  body: { fontFamily: font.prose, fontSize: 15, lineHeight: 23, color: color.inkSoft },
  go: {
    marginTop: 10,
    backgroundColor: color.ink,
    paddingVertical: 15,
    borderRadius: 4,
    alignItems: 'center',
  },
  goText: {
    color: color.paper,
    fontFamily: font.monoBold,
    fontSize: 12,
    letterSpacing: 1.2,
    textTransform: 'uppercase',
  },
});
