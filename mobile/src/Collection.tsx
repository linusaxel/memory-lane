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
import { when } from './format.ts';
import { color, dim, font, label } from './theme.ts';
import type { UnlockedMemory } from './unlocked.ts';

type Props = {
  memories: UnlockedMemory[];
  /** False until the local store has been read. Without it this screen says
   *  "Nothing yet." to somebody with a full collection for the frame before the
   *  disk answers - the same "nothing here" / "we could not ask" collision
   *  `Status` exists to prevent on the map. It is one boolean and not a
   *  `Status` because `loadUnlocked` cannot fail: it returns {} instead. */
  ready: boolean;
  onOpen: (memory: UnlockedMemory) => void;
};

export default function Collection({ memories, ready, onOpen }: Props) {
  const insets = useSafeAreaInsets();

  return (
    <View style={[styles.screen, { paddingTop: insets.top + 14 }]}>
      <Text style={styles.title}>Unlocked</Text>
      <Text style={styles.subtitle}>
        {!ready
          ? ''
          : memories.length === 0
            ? 'Nothing yet.'
            : `${memories.length} ${memories.length === 1 ? 'memory' : 'memories'} you walked to`}
      </Text>

      {/* No spinner: this is a disk read that resolves in a frame, and a
          spinner that flashes is worse than a beat of nothing. */}
      {!ready ? null : memories.length === 0 ? (
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
              style={dim(styles.row)}
              onPress={() => onOpen(item)}
              accessibilityRole="button"
              accessibilityLabel={[item.place.name, when(item.unlocked_at) && `unlocked ${when(item.unlocked_at)}`]
                .filter(Boolean)
                .join(', ')}
            >
              <Text style={styles.place} numberOfLines={1}>
                {item.place.name}
              </Text>
              <Text style={styles.summary} numberOfLines={2}>
                {item.summary}
              </Text>
              {when(item.unlocked_at) && (
                <Text style={styles.when}>{when(item.unlocked_at)}</Text>
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
