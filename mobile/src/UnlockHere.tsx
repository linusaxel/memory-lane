/** The lock, low on the map where a thumb reaches, for the memory you are
 *  standing on, and under it which one: its place, its year or source, and ‹ ›
 *  when more than one is in reach (docs/10, "The lock says where"). */

import { useEffect } from 'react';
import { AccessibilityInfo, Pressable, StyleSheet, Text, View } from 'react-native';

import type { LocatedMemory } from './api.ts';
import Glyph from './Glyph.tsx';
import LocketUnlock, { type Iris } from './LocketUnlock.tsx';
import { color, dim, floating, font, label } from './theme.ts';

type Props = {
  memory: LocatedMemory;
  /** Which of the memories in reach this is, and how many there are. */
  index: number;
  count: number;
  onStep: (by: 1 | -1) => void;
  /** Asks the server. True opens the locket, false springs it back. */
  requestUnlock: () => Promise<boolean>;
  /** The locket is diving in: bring the memory up. */
  onDiveStart: (from: Iris) => void;
  onOpened: () => void;
  error: string | null;
};

export default function UnlockHere({
  memory,
  index,
  count,
  onStep,
  requestUnlock,
  onDiveStart,
  onOpened,
  error,
}: Props) {
  const from = [memory.year, memory.source_name].filter(Boolean).join(' · ');
  const many = count > 1;
  const { lat, lng } = memory.place.coordinates;

  useEffect(() => {
    if (error) AccessibilityInfo.announceForAccessibility(error);
  }, [error]);

  return (
    <View style={styles.stack} pointerEvents="box-none">
      <LocketUnlock
        // A fresh locket per memory: ‹ › must not carry a half-turned key over.
        key={memory.id}
        locket={memory.locket}
        placeName={memory.place.name}
        coordinates={`${Math.abs(lat).toFixed(2)} ${lat < 0 ? 'S' : 'N'} · ${Math.abs(lng).toFixed(2)} ${lng < 0 ? 'W' : 'E'}`}
        requestUnlock={requestUnlock}
        onDiveStart={onDiveStart}
        onOpened={onOpened}
        size={LOCKET}
      />
      <View style={styles.card}>
        {many && (
          <Arrow glyph="chevron.left" name="Previous memory here" onPress={() => onStep(-1)} />
        )}
        <View style={styles.text}>
          <Text style={styles.name} numberOfLines={2}>
            {memory.place.name}
          </Text>
          {(from !== '' || many) && (
            <Text style={label}>
              {[from, many && `${index + 1} of ${count}`].filter(Boolean).join(' · ')}
            </Text>
          )}
        </View>
        {many && <Arrow glyph="chevron.right" name="Next memory here" onPress={() => onStep(1)} />}
      </View>
    </View>
  );
}

type ArrowProps = { glyph: 'chevron.left' | 'chevron.right'; name: string; onPress: () => void };

function Arrow({ glyph, name, onPress }: ArrowProps) {
  return (
    <Pressable
      style={dim(styles.arrow)}
      onPress={onPress}
      accessibilityRole="button"
      accessibilityLabel={name}
    >
      <Glyph name={glyph} size={22} weight="semibold" color={color.ink} />
    </Pressable>
  );
}

const LOCKET = 180;

const styles = StyleSheet.create({
  // Above Plan a walk / Add (App's `bottom`, at 70), which stay one tap away.
  stack: { position: 'absolute', left: 16, right: 16, bottom: 134, alignItems: 'center', gap: 14 },
  card: {
    alignSelf: 'stretch',
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: 8,
    paddingVertical: 12,
    ...floating,
  },
  text: { flex: 1, alignItems: 'center', gap: 4, paddingHorizontal: 8 },
  name: { ...font.display, fontSize: 20, lineHeight: 24, color: color.ink, textAlign: 'center' },
  arrow: { width: 44, height: 44, alignItems: 'center', justifyContent: 'center' },
});
