/** Where stories wait: each neighbourhood, opened out of total. A sheet from
 *  the account menu. A row plans a one-way walk that ends there, so a walker
 *  whose own streets are read has somewhere to go (docs/10, "Where stories
 *  wait"). No pins and no stories: counts only. */

import { useEffect, useState } from 'react';
import { Modal, Pressable, ScrollView, StyleSheet, Text, View } from 'react-native';

import { fetchNeighbourhoods, type Coordinates, type Neighbourhood } from './api.ts';
import CloseButton from './CloseButton.tsx';
import DiamondRule from './DiamondRule.tsx';
import { color, font, screenTitle } from './theme.ts';

type Props = {
  visible: boolean;
  onClose: () => void;
  device: string | null;
  at: Coordinates | null;
  /** Plans a walk ending there; unset on a walk, when the rows only read. */
  onPick?: (end: Coordinates) => void;
};

export default function Neighbourhoods({ visible, onClose, device, at, onPick }: Props) {
  const [rows, setRows] = useState<Neighbourhood[] | null>(null);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    if (!visible || !device) return;
    const abort = new AbortController();
    setFailed(false);
    fetchNeighbourhoods(device, at, abort.signal)
      .then(setRows)
      .catch(() => !abort.signal.aborted && setFailed(true));
    return () => abort.abort();
    // Where you are when it opens; not every step after.
  }, [visible, device]);

  return (
    <Modal
      visible={visible}
      animationType="slide"
      presentationStyle="pageSheet"
      onRequestClose={onClose}
    >
      <ScrollView style={styles.screen} contentContainerStyle={styles.body}>
        <View style={styles.top}>
          <Text style={styles.title} accessibilityRole="header">
            Where stories wait
          </Text>
          <CloseButton onPress={onClose} label="Close where stories wait" />
        </View>
        <Text style={styles.subtitle}>
          {onPick ? 'Tap one for a walk that ends there.' : 'Opened, out of what is there.'}
        </Text>
        <DiamondRule place={styles.rule} />
        {failed && <Text style={styles.note}>Couldn't load the neighbourhoods.</Text>}
        {rows?.length === 0 && <Text style={styles.note}>No neighbourhoods here yet.</Text>}
        {rows?.map((n) => (
          <Pressable
            key={n.name}
            style={styles.row}
            disabled={!onPick}
            onPress={() => onPick?.(n.end)}
            accessibilityRole={onPick ? 'button' : undefined}
            accessibilityLabel={`${n.name}, ${n.opened} of ${n.total} opened`}
            testID="neighbourhood"
          >
            <Text style={styles.name} numberOfLines={1}>
              {n.name}
            </Text>
            <Text style={[styles.count, n.opened === n.total && styles.done]}>
              {`${n.opened} of ${n.total}`}
            </Text>
          </Pressable>
        ))}
      </ScrollView>
    </Modal>
  );
}

const styles = StyleSheet.create({
  screen: { flex: 1, backgroundColor: color.paper },
  body: { paddingHorizontal: 24, paddingTop: 28, paddingBottom: 72, gap: 6 },
  // Settings' title bar, so the sheets read as one app.
  top: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' },
  title: screenTitle,
  subtitle: { ...font.storyItalic, fontSize: 18, lineHeight: 24, color: color.inkSoft },
  rule: { marginVertical: 20 },
  note: { ...font.prose, fontSize: 15, lineHeight: 24, color: color.inkFaint, marginBottom: 12 },
  row: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 14,
    paddingVertical: 14,
    borderBottomWidth: 1,
    borderBottomColor: color.rule,
  },
  name: { flex: 1, ...font.uiMedium, fontSize: 17, color: color.ink },
  count: { ...font.ui, fontSize: 15, color: color.inkSoft },
  // Read through: what you earned is plum.
  done: { color: color.plum },
});
