/** The ring, over the map, for the memory you are standing on. A hold opens the
 *  sheet on the story; before it, the place and what is waiting is all there is
 *  to show (docs/10, "Unlock on the map"). */

import { Pressable, StyleSheet, Text, View, type StyleProp, type ViewStyle } from 'react-native';

import type { LocatedMemory } from './api.ts';
import Approach from './Approach.tsx';
import { button, buttonTextSmall, color, font, label, lift, radius } from './theme.ts';
import UnlockButton from './UnlockButton.tsx';
import { shortfall } from './wallet.ts';

type Props = {
  memory: LocatedMemory;
  onUnlock: () => void;
  busy: boolean;
  error: string | null;
  /** What opening it spends; null for a subscriber. */
  cost: string | null;
  /** Steps still to walk before this opens. Then there is no ring to hold,
   *  only how far off it is and the way round it. */
  short: number;
  onSkip: () => void;
  place?: StyleProp<ViewStyle>;
};

export default function UnlockHere({ memory, onUnlock, busy, error, cost, short, onSkip, place }: Props) {
  const from = [memory.year, memory.source_name].filter(Boolean).join(' · ');
  const waiting = [
    memory.media_count === 1
      ? '1 attachment'
      : memory.media_count > 1 && `${memory.media_count} attachments`,
    memory.note_count === 1 ? '1 note' : memory.note_count > 1 && `${memory.note_count} notes`,
  ].filter(Boolean);
  return (
    <View style={[styles.card, place]}>
      {short > 0 ? (
        <Approach meters={0} radius={1} />
      ) : (
        <UnlockButton onUnlock={onUnlock} busy={busy} />
      )}
      <View style={styles.text}>
        <Text style={styles.name} numberOfLines={2}>
          {memory.place.name}
        </Text>
        {from !== '' && <Text style={label}>{from}</Text>}
        {waiting.length > 0 && (
          <Text style={styles.waiting}>{waiting.join(' · ')} waiting</Text>
        )}
        <Text style={styles.note}>{short > 0 ? shortfall(short) : (error ?? 'You made it.')}</Text>
        {short > 0 ? (
          <Pressable
            style={[button.quiet, button.small, styles.skip]}
            hitSlop={4}
            accessibilityRole="button"
            onPress={onSkip}
          >
            <Text style={styles.skipText}>Skip the steps</Text>
          </Pressable>
        ) : (
          cost && !error && <Text style={label}>{cost}</Text>
        )}
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
  skip: { alignSelf: 'flex-start', marginTop: 4 },
  skipText: { ...buttonTextSmall, color: color.ink },
});
