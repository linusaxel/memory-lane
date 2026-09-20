/** Everything this device has earned.
 *
 * Unlocking has to be worth something after the walk home. Without this the
 * reward for standing somewhere is one read and then the memory is buried under
 * whichever pin you happened to be near, findable only by going back - which is
 * the opposite of a reward.
 *
 * Local by construction: the list is exactly what `unlocked.ts` holds, because
 * the server does not know who unlocked anything and is not going to.
 */

import { FlatList, Modal, Pressable, StyleSheet, Text, View } from 'react-native';

import type { UnlockedMemory } from './unlocked.ts';

type Props = {
  visible: boolean;
  memories: UnlockedMemory[];
  onOpen: (memory: UnlockedMemory) => void;
  onClose: () => void;
};

function formatWhen(at: number): string {
  const days = Math.floor((Date.now() - at) / 86_400_000);
  if (days <= 0) return 'today';
  if (days === 1) return 'yesterday';
  if (days < 30) return `${days} days ago`;
  return new Date(at).toLocaleDateString();
}

export default function Collection({ visible, memories, onOpen, onClose }: Props) {
  return (
    <Modal
      visible={visible}
      animationType="slide"
      presentationStyle="pageSheet"
      onRequestClose={onClose}
    >
      <View style={styles.sheet}>
        <View style={styles.grabberRow}>
          <View style={styles.grabber} />
        </View>

        <Text style={styles.title}>Unlocked</Text>
        <Text style={styles.subtitle}>
          {memories.length === 0
            ? 'Nothing yet. Memories open when you stand where they happened.'
            : `${memories.length} ${memories.length === 1 ? 'memory' : 'memories'} you walked to`}
        </Text>

        <FlatList
          data={memories}
          keyExtractor={(memory) => String(memory.id)}
          contentContainerStyle={styles.list}
          renderItem={({ item }) => (
            <Pressable
              style={styles.row}
              onPress={() => onOpen(item)}
              accessibilityRole="button"
              accessibilityLabel={`${item.place.name}, unlocked ${formatWhen(item.unlocked_at)}`}
            >
              <Text style={styles.place} numberOfLines={1}>
                {item.place.name}
              </Text>
              <Text style={styles.summary} numberOfLines={2}>
                {item.summary}
              </Text>
              <Text style={styles.when}>{formatWhen(item.unlocked_at)}</Text>
            </Pressable>
          )}
        />

        <Pressable style={styles.close} onPress={onClose}>
          <Text style={styles.closeText}>Close</Text>
        </Pressable>
      </View>
    </Modal>
  );
}

const styles = StyleSheet.create({
  sheet: { flex: 1, backgroundColor: '#fff' },
  grabberRow: { alignItems: 'center', paddingTop: 10 },
  grabber: { width: 40, height: 5, borderRadius: 3, backgroundColor: '#d4d4d8' },
  title: { fontSize: 26, fontWeight: '700', color: '#18181b', letterSpacing: -0.5, paddingHorizontal: 24, paddingTop: 18 },
  subtitle: { fontSize: 14, color: '#71717a', paddingHorizontal: 24, paddingTop: 4 },
  list: { padding: 24, gap: 18 },
  row: { gap: 4 },
  place: { fontSize: 17, fontWeight: '600', color: '#18181b' },
  summary: { fontSize: 15, lineHeight: 22, color: '#52525b' },
  when: { fontSize: 12, color: '#a1a1aa' },
  close: { paddingVertical: 16, alignItems: 'center', borderTopWidth: 1, borderTopColor: '#f4f4f5' },
  closeText: { color: '#71717a', fontSize: 15 },
});
