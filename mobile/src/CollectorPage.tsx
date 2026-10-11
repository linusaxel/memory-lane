/** Your Collector: a sheet of its own, opened from the Collector in the
 *  journal's header (docs/10, "The Collector"). The look now, how far to the
 *  next, the path of eight with the ones ahead as silhouettes, and the four
 *  classes to switch between. The stage comes along on a switch: it is your
 *  lockets, not the class's. No shop, no prices, no currency. */

import { Modal, Pressable, ScrollView, StyleSheet, Text, View } from 'react-native';

import CloseButton from './CloseButton.tsx';
import CollectorLook from './CollectorLook.tsx';
import { CLASSES, STAGES, classOf, toNext, type ClassId } from './collector.ts';
import { color, dim, font, label, lift, screenTitle } from './theme.ts';

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
  // A rank kept after a memory was hidden can sit above the count: the bar is full.
  const from = STAGES[stage];
  const into =
    next === null ? 1 : Math.min(1, (lockets - from) / Math.max(1, STAGES[stage + 1] - from));
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
          <CollectorLook id={chosen.id} stage={stage} size={200} />
          <Text style={label}>{chosen.name}</Text>
          <Text style={styles.rank} accessibilityRole="header">
            {chosen.ranks[stage]}
          </Text>
          <Text style={styles.count}>
            {`${lockets} ${lockets === 1 ? 'locket' : 'lockets'}`}
            {next !== null && left !== null && left > 0 ? ` · ${left} to ${next}` : ''}
          </Text>
          <View style={styles.bar}>
            <View style={[styles.fill, { width: `${into * 100}%` }]} />
          </View>
        </View>

        <Text style={styles.groupTitle}>The path</Text>
        <ScrollView
          horizontal
          showsHorizontalScrollIndicator={false}
          contentContainerStyle={styles.path}
        >
          {STAGES.map((at, i) => (
            <View
              key={at}
              style={styles.step}
              accessible
              accessibilityLabel={
                i <= stage ? `${chosen.ranks[i]}, reached` : `${chosen.ranks[i]}, at ${at} lockets`
              }
            >
              <CollectorLook id={chosen.id} stage={i} size={64} ahead={i > stage} />
              <Text style={[styles.stepRank, i > stage && styles.ahead]} numberOfLines={2}>
                {chosen.ranks[i]}
              </Text>
              <Text style={styles.stepAt}>{`at ${at}`}</Text>
            </View>
          ))}
        </ScrollView>

        <Text style={styles.groupTitle}>Your class</Text>
        <View style={styles.classes}>
          {CLASSES.map((c) => (
            <Pressable
              key={c.id}
              style={dim([styles.class, c.id === chosen.id && styles.classOn])}
              onPress={() => onChoose(c.id)}
              accessibilityRole="radio"
              accessibilityState={{ selected: c.id === chosen.id }}
              accessibilityLabel={c.name}
            >
              <CollectorLook id={c.id} stage={stage} size={72} />
              <Text style={styles.className}>{c.name}</Text>
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
  hero: { alignItems: 'center', gap: 6, marginTop: 20 },
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
  path: { gap: 12, paddingVertical: 12, paddingHorizontal: 4 },
  step: { width: 76, alignItems: 'center', gap: 4 },
  stepRank: { ...font.uiBold, fontSize: 12, color: color.ink, textAlign: 'center' },
  ahead: { color: color.inkFaint },
  stepAt: { ...font.ui, fontSize: 11, color: color.inkFaint },
  classes: { flexDirection: 'row', flexWrap: 'wrap', gap: 12, marginTop: 12 },
  class: {
    width: '47%',
    flexGrow: 1,
    alignItems: 'center',
    gap: 6,
    paddingVertical: 14,
    borderRadius: 16,
    backgroundColor: color.paperRaised,
    borderWidth: StyleSheet.hairlineWidth,
    borderColor: color.goldLine,
    ...lift,
    shadowOpacity: 0.06,
  },
  classOn: { borderWidth: 2, borderColor: color.gold },
  className: { ...font.uiBold, fontSize: 14, color: color.ink },
});
