/** The lock, low on the map where a thumb reaches, for the memory you are
 *  standing on, and under it which one: its place, its year or source, and ‹ ›
 *  when more than one is in reach (docs/10, "The lock says where"). */

import { Pressable, StyleSheet, Text, View } from 'react-native';

import type { LocatedMemory } from './api.ts';
import Glyph from './Glyph.tsx';
import { color, floating, font, label } from './theme.ts';
import UnlockButton from './UnlockButton.tsx';

type Props = {
  memory: LocatedMemory;
  /** Which of the memories in reach this is, and how many there are. */
  index: number;
  count: number;
  onStep: (by: 1 | -1) => void;
  onUnlock: () => void;
  busy: boolean;
  error: string | null;
};

export default function UnlockHere({
  memory,
  index,
  count,
  onStep,
  onUnlock,
  busy,
  error,
}: Props) {
  const from = [memory.year, memory.source_name].filter(Boolean).join(' · ');
  const many = count > 1;
  return (
    <View style={styles.stack} pointerEvents="box-none">
      <UnlockButton onUnlock={onUnlock} busy={busy} error={error} />
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
        {many && (
          <Arrow glyph="chevron.right" name="Next memory here" onPress={() => onStep(1)} />
        )}
      </View>
    </View>
  );
}

type ArrowProps = { glyph: 'chevron.left' | 'chevron.right'; name: string; onPress: () => void };

function Arrow({ glyph, name, onPress }: ArrowProps) {
  return (
    <Pressable
      style={styles.arrow}
      onPress={onPress}
      accessibilityRole="button"
      accessibilityLabel={name}
    >
      <Glyph name={glyph} size={22} weight="semibold" color={color.ink} />
    </Pressable>
  );
}

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
