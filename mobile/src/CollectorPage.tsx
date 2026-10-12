/** Your Collector: a sheet of its own, opened from the Collector in the
 *  journal's header (docs/10, "The Collector"). A character sheet: the look
 *  now in its plate, how far to the next robe, the path of eight as a ladder
 *  with the ones ahead as silhouettes, and the four classes as crests. The stage comes along on a switch: it is your
 *  lockets, not the class's. No shop, no prices, no currency. */

import { Modal, Pressable, ScrollView, StyleSheet, Text, View } from 'react-native';

import CloseButton from './CloseButton.tsx';
import CollectorLook from './CollectorLook.tsx';
import Plate from './Plate.tsx';
import { CLASSES, STAGES, classOf, rankInto, toNext, type ClassId } from './collector.ts';
import { color, dim, font, label, screenTitle } from './theme.ts';

type Props = {
  visible: boolean;
  onClose: () => void;
  id: ClassId;
  stage: number;
  lockets: number;
  onChoose: (id: ClassId) => void;
};

export default function CollectorPage({ visible, onClose, id, stage, lockets, onChoose }: Props) {
  const chosen = classOf(id);
  const left = toNext(lockets);
  const next = stage + 1 < STAGES.length ? chosen.ranks[stage + 1] : null;
  const into = rankInto(stage, lockets);
  return (
    <Modal
      visible={visible}
      animationType="slide"
      presentationStyle="pageSheet"
      onRequestClose={onClose}
    >
      <ScrollView style={styles.screen} contentContainerStyle={styles.body}>
        <View style={styles.top}>
          <Text style={styles.title}>Your Collector</Text>
          <CloseButton onPress={onClose} label="Close Collector" />
        </View>

        <View style={styles.hero} accessible testID="collector-page">
          <Plate size={200} on>
            <CollectorLook id={chosen.id} stage={stage} size={184} />
          </Plate>
          <Text style={[label, styles.className]}>{chosen.name}</Text>
          <Text style={styles.rank} accessibilityRole="header">
            {chosen.ranks[stage]}
          </Text>
          <Text style={styles.count}>
            {`${lockets} ${lockets === 1 ? 'locket' : 'lockets'}`}
            {next !== null && left !== null && left > 0 ? ` · ${left} more to the next robe` : ''}
          </Text>
          <View style={styles.bar}>
            <View style={[styles.fill, { width: `${into * 100}%` }]} />
          </View>
        </View>

        <Text style={styles.groupTitle}>The path</Text>
        <View style={styles.ladder}>
          {STAGES.map((at, i) => (
            <View
              key={at}
              style={styles.rung}
              accessible
              accessibilityLabel={
                i <= stage ? `${chosen.ranks[i]}, reached` : `${chosen.ranks[i]}, at ${at} lockets`
              }
            >
              <View style={styles.spine}>
                <View style={[styles.line, i === 0 && styles.clear, i <= stage && styles.lineOn]} />
                <View
                  style={[styles.knot, i <= stage && styles.knotOn, i === stage && styles.knotNow]}
                />
                <View
                  style={[
                    styles.line,
                    i === STAGES.length - 1 && styles.clear,
                    i < stage && styles.lineOn,
                  ]}
                />
              </View>
              <CollectorLook id={chosen.id} stage={i} size={48} ahead={i > stage} />
              <View style={styles.rungWords}>
                <Text style={[styles.stepRank, i > stage && styles.ahead]} numberOfLines={1}>
                  {chosen.ranks[i]}
                </Text>
                <Text style={styles.stepAt}>{i === stage ? 'You' : `at ${at}`}</Text>
              </View>
            </View>
          ))}
        </View>

        <Text style={styles.groupTitle}>Your class</Text>
        <View style={styles.classes}>
          {CLASSES.map((c) => (
            <Pressable
              key={c.id}
              style={dim(styles.class)}
              onPress={() => onChoose(c.id)}
              accessibilityRole="radio"
              accessibilityState={{ selected: c.id === chosen.id }}
              accessibilityLabel={c.name}
            >
              <Plate size={72} on={c.id === chosen.id}>
                <CollectorLook id={c.id} stage={stage} size={64} />
              </Plate>
              <Text style={styles.crestName}>{c.name}</Text>
            </Pressable>
          ))}
        </View>
      </ScrollView>
    </Modal>
  );
}

const styles = StyleSheet.create({
  screen: { flex: 1, backgroundColor: color.paper },
  body: { paddingHorizontal: 20, paddingTop: 28, paddingBottom: 72 },
  // The journal's title bar, as Settings has it.
  top: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingHorizontal: 4,
  },
  title: screenTitle,
  hero: { alignItems: 'center', gap: 6, marginTop: 24 },
  className: { marginTop: 14 },
  rank: { ...screenTitle, fontSize: 28, lineHeight: 34, textAlign: 'center' },
  count: { ...font.prose, fontSize: 16, color: color.inkSoft },
  bar: {
    alignSelf: 'stretch',
    height: 6,
    borderRadius: 3,
    backgroundColor: color.track,
    marginTop: 8,
    marginHorizontal: 32,
  },
  fill: { height: 6, borderRadius: 3, backgroundColor: color.plum },
  groupTitle: { ...label, fontSize: 12, color: color.inkFaint, marginTop: 32, marginLeft: 4 },
  // The path of eight, a ladder: a gold spine up to where you stand.
  ladder: { marginTop: 8, paddingHorizontal: 4 },
  rung: { flexDirection: 'row', alignItems: 'center', gap: 12, height: 60 },
  spine: { width: 16, alignSelf: 'stretch', alignItems: 'center' },
  line: { flex: 1, width: 2, backgroundColor: color.rule },
  lineOn: { backgroundColor: color.gold },
  clear: { backgroundColor: 'transparent' },
  knot: {
    width: 10,
    height: 10,
    borderRadius: 5,
    borderWidth: 2,
    borderColor: color.rule,
    backgroundColor: color.paper,
  },
  knotOn: { borderColor: color.gold, backgroundColor: color.gold },
  knotNow: { width: 16, height: 16, borderRadius: 8, borderColor: color.plum, borderWidth: 3 },
  rungWords: { flex: 1, gap: 2 },
  stepRank: { ...font.uiBold, fontSize: 15, color: color.ink },
  ahead: { color: color.inkFaint },
  stepAt: { ...font.ui, fontSize: 12, color: color.inkFaint },
  classes: { flexDirection: 'row', flexWrap: 'wrap', gap: 12, marginTop: 12 },
  class: {
    width: '47%',
    flexGrow: 1,
    alignItems: 'center',
    gap: 10,
    paddingVertical: 18,
    borderRadius: 16,
  },
  crestName: { ...font.uiBold, fontSize: 14, color: color.ink },
});
