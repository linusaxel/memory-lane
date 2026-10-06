/** This month's city board: who opened the most memories in the city. A sheet
 *  from the account menu, never on the walk (docs/10, "A city board, by opens"). */

import { useEffect, useState } from 'react';
import { Modal, ScrollView, StyleSheet, Text, View } from 'react-native';

import { fetchBoard, type BoardRow } from './api.ts';
import Avatar from './Avatar.tsx';
import CloseButton from './CloseButton.tsx';
import DiamondRule from './DiamondRule.tsx';
import { color, font, foil, metal, screenTitle } from './theme.ts';

const MEDAL = [metal.mid, metal.silver, metal.bronze];

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
        <Text style={styles.subtitle}>Memories opened here this month.</Text>
        <DiamondRule place={styles.rule} />
        {failed && <Text style={styles.note}>Couldn't load the board.</Text>}
        {board?.rows.length === 0 && <Text style={styles.note}>Nobody yet. Go for a walk.</Text>}
        {board?.rows.map((r, i) => (
          <View
            key={`${r.rank}-${i}`}
            style={[
              styles.row,
              r.mine && styles.mineRow,
              i > 0 && r.rank > board.rows[i - 1].rank + 1 && styles.gap,
            ]}
            testID={r.mine ? 'board-me' : undefined}
          >
            {r.rank <= 3 ? (
              <View style={[styles.medal, { backgroundColor: MEDAL[r.rank - 1] }]}>
                <Text style={styles.medalText}>{r.rank}</Text>
              </View>
            ) : (
              <Text style={styles.rank}>{r.rank}</Text>
            )}
            <Avatar url={r.avatar_url} name={r.display_name} size={40} />
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
  title: screenTitle,
  subtitle: { ...font.storyItalic, fontSize: 18, lineHeight: 24, color: color.inkSoft },
  rule: { marginVertical: 20 },
  note: { ...font.prose, fontSize: 15, lineHeight: 24, color: color.inkFaint, marginBottom: 12 },
  row: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 14,
    paddingVertical: 12,
    paddingHorizontal: 12,
    borderRadius: 20,
    borderWidth: 1,
    borderColor: 'transparent',
    borderBottomColor: color.rule,
  },
  // Your own row is plum: the one place on the board that is you.
  mineRow: { backgroundColor: color.track, borderColor: color.plum, borderBottomColor: color.plum },
  // Your own row, when it is below the top: a break says the ranks skip.
  gap: { marginTop: 18 },
  medal: {
    width: 30,
    height: 30,
    borderRadius: 15,
    alignItems: 'center',
    justifyContent: 'center',
  },
  medalText: { ...font.title, fontSize: 16, color: foil.text },
  rank: { ...font.title, fontSize: 16, width: 30, textAlign: 'center', color: color.inkFaint },
  name: { flex: 1, ...font.uiMedium, fontSize: 17, color: color.ink },
  opens: { ...font.title, fontSize: 26, lineHeight: 32, color: color.ink },
  mine: { color: color.plum },
});
