/** This month's city board: who opened the most memories in the city. A sheet
 *  from the account menu, never on the walk (docs/10, "A city board, by opens"). */

import { useEffect, useState } from 'react';
import { Modal, ScrollView, StyleSheet, Text, View } from 'react-native';

import { fetchBoard, type BoardRow } from './api.ts';
import Avatar from './Avatar.tsx';
import CloseButton from './CloseButton.tsx';
import { color, font, label } from './theme.ts';

type Props = { visible: boolean; onClose: () => void; device: string | null };

export default function Board({ visible, onClose, device }: Props) {
  const [board, setBoard] = useState<{ city: string; rows: BoardRow[] } | null>(null);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    if (!visible || !device) return;
    const abort = new AbortController();
    setFailed(false);
    fetchBoard(device, abort.signal)
      .then(setBoard)
      .catch(() => !abort.signal.aborted && setFailed(true));
    return () => abort.abort();
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
          <Text style={styles.title}>{board?.city ?? 'Board'}</Text>
          <CloseButton onPress={onClose} label="Close board" />
        </View>
        <Text style={styles.note}>Memories opened here this month.</Text>
        {failed && <Text style={styles.note}>Couldn't load the board.</Text>}
        {board?.rows.length === 0 && <Text style={styles.note}>Nobody yet. Go for a walk.</Text>}
        {board?.rows.map((r, i) => (
          <View
            key={`${r.rank}-${i}`}
            style={[styles.row, i > 0 && r.rank > board.rows[i - 1].rank + 1 && styles.gap]}
            testID={r.mine ? 'board-me' : undefined}
          >
            <Text style={[styles.rank, r.mine && styles.mine]}>{r.rank}</Text>
            <Avatar url={r.avatar_url} name={r.display_name} size={32} />
            <Text style={[styles.name, r.mine && styles.mine]} numberOfLines={1}>
              {r.mine ? 'You' : r.display_name}
            </Text>
            <Text style={[styles.opens, r.mine && styles.mine]}>{r.opens}</Text>
          </View>
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
  title: { ...font.display, fontSize: 34, color: color.ink },
  note: { ...font.prose, fontSize: 15, lineHeight: 24, color: color.inkFaint, marginBottom: 12 },
  row: { flexDirection: 'row', alignItems: 'center', gap: 12, paddingVertical: 8 },
  // Your own row, when it is below the top: a break says the ranks skip.
  gap: { marginTop: 18, borderTopWidth: 1, borderTopColor: color.rule, paddingTop: 18 },
  rank: { ...label, minWidth: 28, fontVariant: ['tabular-nums'] },
  name: { flex: 1, ...font.uiMedium, fontSize: 17, color: color.ink },
  opens: { ...font.uiBold, fontSize: 17, color: color.ink, fontVariant: ['tabular-nums'] },
  mine: { color: color.purple },
});
