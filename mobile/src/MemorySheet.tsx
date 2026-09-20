import {
  Linking,
  Modal,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  View,
} from 'react-native';

import type { LocatedMemory } from './api.ts';

type Props = {
  memory: LocatedMemory | null;
  onClose: () => void;
};

function formatDistance(meters: number | null): string | null {
  if (meters == null) return null;
  return meters < 1000
    ? `${Math.round(meters)} m away`
    : `${(meters / 1000).toFixed(1)} km away`;
}

function formatTimestamp(seconds: number): string {
  const total = Math.floor(seconds);
  const h = Math.floor(total / 3600);
  const m = Math.floor((total % 3600) / 60);
  const s = total % 60;
  const mm = h > 0 ? String(m).padStart(2, '0') : String(m);
  return `${h > 0 ? `${h}:` : ''}${mm}:${String(s).padStart(2, '0')}`;
}

export default function MemorySheet({ memory, onClose }: Props) {
  return (
    <Modal
      visible={!!memory}
      animationType="slide"
      presentationStyle="pageSheet"
      // Required, or the Android back button does nothing.
      onRequestClose={onClose}
    >
      {memory && (
        <View style={styles.sheet}>
          <View style={styles.grabberRow}>
            <View style={styles.grabber} />
          </View>

          <ScrollView contentContainerStyle={styles.body}>
            <Text style={styles.place}>{memory.place.name}</Text>

            <View style={styles.metaRow}>
              {formatDistance(memory.distance_meters) && (
                <Text style={styles.meta}>{formatDistance(memory.distance_meters)}</Text>
              )}
              {memory.confidence === 'high' && (
                <Text style={[styles.meta, styles.confident]}>high confidence</Text>
              )}
            </View>

            {/* No images exist anywhere in the schema, so the summary carries
                the whole sheet - it gets the typographic weight. */}
            <Text style={styles.summary}>{memory.summary}</Text>

            {memory.tags?.length > 0 && (
              <View style={styles.tags}>
                {memory.tags.map((tag) => (
                  <Text key={tag} style={styles.tag}>
                    {tag}
                  </Text>
                ))}
              </View>
            )}

            {memory.content.title && (
              <Text style={styles.source} numberOfLines={2}>
                {memory.content.title}
              </Text>
            )}
          </ScrollView>

          <View style={styles.actions}>
            <Pressable
              style={styles.watch}
              // timestamp_url already points at the right second.
              onPress={() => Linking.openURL(memory.content.timestamp_url)}
            >
              <Text style={styles.watchText}>
                Watch at {formatTimestamp(memory.content.timestamp_start)}
              </Text>
            </Pressable>
            <Pressable style={styles.close} onPress={onClose}>
              <Text style={styles.closeText}>Close</Text>
            </Pressable>
          </View>
        </View>
      )}
    </Modal>
  );
}

const styles = StyleSheet.create({
  sheet: { flex: 1, backgroundColor: '#fff' },
  grabberRow: { alignItems: 'center', paddingTop: 10 },
  grabber: { width: 40, height: 5, borderRadius: 3, backgroundColor: '#d4d4d8' },
  body: { padding: 24, paddingBottom: 12 },
  place: { fontSize: 26, fontWeight: '700', color: '#18181b', letterSpacing: -0.5 },
  metaRow: { flexDirection: 'row', gap: 12, marginTop: 6 },
  meta: { fontSize: 13, color: '#71717a' },
  confident: { color: '#15803d' },
  summary: { fontSize: 17, lineHeight: 26, color: '#27272a', marginTop: 20 },
  tags: { flexDirection: 'row', flexWrap: 'wrap', gap: 8, marginTop: 22 },
  tag: {
    fontSize: 12,
    color: '#3f3f46',
    backgroundColor: '#f4f4f5',
    paddingHorizontal: 10,
    paddingVertical: 5,
    borderRadius: 12,
    overflow: 'hidden',
  },
  source: { fontSize: 13, color: '#a1a1aa', marginTop: 24, fontStyle: 'italic' },
  actions: { padding: 20, gap: 10, borderTopWidth: 1, borderTopColor: '#f4f4f5' },
  watch: { backgroundColor: '#dc2626', paddingVertical: 15, borderRadius: 12, alignItems: 'center' },
  watchText: { color: '#fff', fontSize: 16, fontWeight: '600' },
  close: { paddingVertical: 12, alignItems: 'center' },
  closeText: { color: '#71717a', fontSize: 15 },
});
