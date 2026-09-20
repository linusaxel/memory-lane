/** Everything this device has earned. A tab, not a drawer.
 *
 * Unlocking has to be worth something after the walk home. Buried behind a pill
 * on the map, the reward for standing somewhere was one read and then finding
 * the right pin again; as a tab it is a place the person owns.
 *
 * Nothing here touches the network: the list is exactly what `unlocked.ts`
 * holds, so it works on a train. The server has its own copy, merged in at
 * launch by App.tsx - that is what survives the local one being cleared.
 */

import { FlatList, Pressable, StyleSheet, Text, View } from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';

import Padlock from './Padlock.tsx';
import { color, font, label } from './theme.ts';
import type { UnlockedMemory } from './unlocked.ts';

type Props = {
  memories: UnlockedMemory[];
  onOpen: (memory: UnlockedMemory) => void;
};

/** Anything unlocked before this app recorded timestamps has none, and the
 *  arithmetic on undefined renders as "Invalid Date". Those memories were still
 *  earned; they just cannot say when. */
function formatWhen(at: number | undefined): string | null {
  if (!Number.isFinite(at)) return null;
  const days = Math.floor((Date.now() - (at as number)) / 86_400_000);
  if (days <= 0) return 'today';
  if (days === 1) return 'yesterday';
  if (days < 30) return `${days} days ago`;
  return new Date(at as number).toLocaleDateString();
}

export default function Collection({ memories, onOpen }: Props) {
  const insets = useSafeAreaInsets();

  return (
    <View style={[styles.screen, { paddingTop: insets.top + 14 }]}>
      <Text style={styles.title}>Unlocked</Text>
      <Text style={styles.subtitle}>
        {memories.length === 0
          ? 'Nothing yet.'
          : `${memories.length} ${memories.length === 1 ? 'memory' : 'memories'} you walked to`}
      </Text>

      {memories.length === 0 ? (
        <View style={styles.empty}>
          <Padlock size={40} color={color.rule} />
          <Text style={styles.emptyText}>
            Memories open when you stand where they happened. Whatever you open stays here.
          </Text>
        </View>
      ) : (
        <FlatList
          data={memories}
          keyExtractor={(memory) => String(memory.id)}
          contentContainerStyle={styles.list}
          renderItem={({ item }) => (
            <Pressable
              style={styles.row}
              onPress={() => onOpen(item)}
              accessibilityRole="button"
              accessibilityLabel={[item.place.name, formatWhen(item.unlocked_at) && `unlocked ${formatWhen(item.unlocked_at)}`]
                .filter(Boolean)
                .join(', ')}
            >
              <Text style={styles.place} numberOfLines={1}>
                {item.place.name}
              </Text>
              <Text style={styles.summary} numberOfLines={2}>
                {item.summary}
              </Text>
              {formatWhen(item.unlocked_at) && (
                <Text style={styles.when}>{formatWhen(item.unlocked_at)}</Text>
              )}
            </Pressable>
          )}
        />
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  screen: { flex: 1, backgroundColor: color.paper },
  title: { fontFamily: font.display, fontSize: 34, color: color.ink, paddingHorizontal: 24 },
  subtitle: { ...label, paddingHorizontal: 24, paddingTop: 8 },
  list: { padding: 24, paddingTop: 26, gap: 26 },
  // A ruled entry, like a catalogue card. No nested card, no shadow.
  row: { gap: 6, borderTopWidth: 1, borderTopColor: color.rule, paddingTop: 16 },
  place: { fontFamily: font.displaySemi, fontSize: 19, lineHeight: 26, color: color.ink },
  summary: { fontFamily: font.prose, fontSize: 16, lineHeight: 25, color: color.inkSoft },
  when: { ...label, fontSize: 10, marginTop: 2 },
  empty: { flex: 1, alignItems: 'center', justifyContent: 'center', paddingHorizontal: 48, gap: 18 },
  emptyText: {
    fontFamily: font.prose,
    fontSize: 16,
    lineHeight: 26,
    color: color.inkFaint,
    textAlign: 'center',
  },
});
