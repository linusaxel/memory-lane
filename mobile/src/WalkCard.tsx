/** A walk you finished, as a card: its shape drawn small, its date and what it
 *  came to. The walk is the collectible (docs/10, "Walks earn XP; rare
 *  memories wait for a level"). The shape is the planned walk through its
 *  stops; the start is never stored, so it begins at the first stop. */

import { StyleSheet, Text, View, useColorScheme } from 'react-native';
import Svg, { Circle, Polyline } from 'react-native-svg';

import type { Coordinates, WalkedRoute } from './api.ts';
import { distance, walkDate } from './format.ts';
import { color, font, label, solid } from './theme.ts';

/** The street shape through every stop, or straight lines without one. */
export function walkPath(walk: WalkedRoute): Coordinates[] {
  return walk.memories.flatMap((memory, i) =>
    i > 0 && walk.legs?.[i - 1] ? walk.legs[i - 1] : [memory.place.coordinates],
  );
}

/** `path` drawn to fit a square of `size`, north up. Real colours, not
 *  platform-resolved ones: react-native-svg is UI.md's exception, like the map. */
export function WalkShape({ path, size }: { path: Coordinates[]; size: number }) {
  const real = solid(useColorScheme() === 'dark');
  if (path.length === 0) return <View style={{ width: size, height: size }} />;
  const lats = path.map((c) => c.lat);
  const lngs = path.map((c) => c.lng);
  // A degree of longitude is shorter away from the equator.
  const squash = Math.cos((((Math.min(...lats) + Math.max(...lats)) / 2) * Math.PI) / 180);
  const spanX = (Math.max(...lngs) - Math.min(...lngs)) * squash;
  const spanY = Math.max(...lats) - Math.min(...lats);
  const pad = size * 0.12;
  const scale = (size - 2 * pad) / Math.max(spanX, spanY, 1e-6);
  const offX = (size - spanX * scale) / 2;
  const offY = (size - spanY * scale) / 2;
  const at = (c: Coordinates) => ({
    x: offX + (c.lng - Math.min(...lngs)) * squash * scale,
    y: offY + (Math.max(...lats) - c.lat) * scale,
  });
  const points = path.map(at);
  return (
    <Svg width={size} height={size}>
      <Polyline
        points={points.map((p) => `${p.x},${p.y}`).join(' ')}
        fill="none"
        stroke={real.ember}
        strokeWidth={Math.max(2, size / 40)}
        strokeLinecap="round"
        strokeLinejoin="round"
      />
      <Circle cx={points[0].x} cy={points[0].y} r={Math.max(2.5, size / 30)} fill={real.ink} />
    </Svg>
  );
}

type Props = { walk: WalkedRoute; size: number };

export default function WalkCard({ walk, size }: Props) {
  const day = walkDate(walk.route_date);
  const km = distance(walk.budget_meters);
  return (
    <View
      style={[styles.card, { width: size }]}
      accessible
      accessibilityLabel={`${day}: ${walk.earned} memories, ${km}.`}
    >
      <WalkShape path={walkPath(walk)} size={size - 2} />
      <View style={styles.under}>
        <Text style={styles.day}>{day}</Text>
        <Text style={styles.meta}>{`${walk.earned} ${walk.earned === 1 ? 'memory' : 'memories'} · ${km}`}</Text>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  card: { borderRadius: 14, borderWidth: 1, borderColor: color.rule, overflow: 'hidden' },
  under: { paddingHorizontal: 10, paddingBottom: 10, gap: 2 },
  day: { ...font.displaySemi, fontSize: 14, color: color.ink },
  meta: { ...label, fontSize: 11 },
});
