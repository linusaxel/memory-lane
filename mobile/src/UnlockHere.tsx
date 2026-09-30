/** The ring, over the map, for the memory you are standing on. A hold opens the
 *  sheet on the story; before it, the place and what is waiting is all there is
 *  to show (docs/10, "Unlock on the map"). */

import { StyleSheet, Text, View, type StyleProp, type ViewStyle } from 'react-native';

import type { LocatedMemory } from './api.ts';
import { color, font, label, lift, radius } from './theme.ts';
import UnlockButton from './UnlockButton.tsx';

type Props = {
  memory: LocatedMemory;
  onUnlock: () => void;
  busy: boolean;
  error: string | null;
  /** What opening it spends; null for a subscriber. */
  cost: string | null;
  place?: StyleProp<ViewStyle>;
};

export default function UnlockHere({ memory, onUnlock, busy, error, cost, place }: Props) {
  const from = [memory.year, memory.source_name].filter(Boolean).join(' · ');
  const waiting = [
    memory.media_count === 1
      ? '1 attachment'
      : memory.media_count > 1 && `${memory.media_count} attachments`,
    memory.note_count === 1 ? '1 note' : memory.note_count > 1 && `${memory.note_count} notes`,
  ].filter(Boolean);
  return (
    <View style={[styles.card, place]}>
      <UnlockButton onUnlock={onUnlock} busy={busy} />
      <View style={styles.text}>
        <Text style={styles.name} numberOfLines={2}>
          {memory.place.name}
        </Text>
        {from !== '' && <Text style={label}>{from}</Text>}
        {waiting.length > 0 && (
          <Text style={styles.waiting}>{waiting.join(' · ')} waiting</Text>
        )}
        <Text style={styles.note}>{error ?? 'You made it.'}</Text>
        {cost && !error && <Text style={label}>{cost}</Text>}
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  card: {
    position: 'absolute',
    left: 16,
    right: 16,
    flexDirection: 'row',
    alignItems: 'center',
    gap: 16,
    paddingHorizontal: 18,
    paddingVertical: 12,
    borderRadius: radius.card,
    backgroundColor: color.paperRaised,
    ...lift,
  },
  text: { flex: 1, gap: 4 },
  name: { ...font.display, fontSize: 20, lineHeight: 24, color: color.ink },
  waiting: { ...label, color: color.sealDeep },
  note: { ...font.ui, fontSize: 15, color: color.inkSoft },
});
