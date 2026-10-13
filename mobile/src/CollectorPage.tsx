/** Your Collector: a sheet of its own, opened from the Collector across the
 *  top of the map, and the one place that is you (docs/10, "One you"): your
 *  name, and the gear for Settings. A character sheet: the look in its plate with a bar for each thing the next rank wants,
 *  the eight looks as a chain with the ones ahead as silhouettes, the next
 *  rank's checklist. The class was picked once, at onboarding, and is not
 *  switched here. A stage needs lockets and memories you filed both (docs/10,
 *  "The Collector"); when a memory is what's missing, the page offers to
 *  leave one. No shop, no prices, no currency. */

import { Modal, Pressable, ScrollView, StyleSheet, Text, TextInput, View } from 'react-native';

import CloseButton from './CloseButton.tsx';
import CollectorLook from './CollectorLook.tsx';
import Plate from './Plate.tsx';
import Button from './Button.tsx';
import { FILED, STAGES, classOf, wants, wantsWords, type ClassId } from './collector.ts';
import { Bar, Coin, Foil, Panel, Ribbon, Velvet } from './Game.tsx';
import Glyph from './Glyph.tsx';
import Icon from './Icon.tsx';
import { color, dim, foil, font, input, label, screenTitle } from './theme.ts';

type Props = {
  visible: boolean;
  onClose: () => void;
  id: ClassId;
  stage: number;
  lockets: number;
  filed: number;
  onAdd: () => void;
  /** Empty means Anonymous. Saved as it is typed, so there is no Save button
   *  to forget to press. */
  displayName: string;
  onDisplayName: (next: string) => void;
  /** Set when the last save did not land. The field keeps the typed value
   *  either way, so without this the name looks saved and is not. */
  nameError: string | null;
  /** Close this and open Settings: one sheet at a time. */
  onSettings: () => void;
};

export default function CollectorPage({
  visible,
  onClose,
  id,
  stage,
  lockets,
  filed,
  onAdd,
  displayName,
  onDisplayName,
  nameError,
  onSettings,
}: Props) {
  const chosen = classOf(id);
  const want = wants(stage, lockets, filed);
  const next = stage + 1 < STAGES.length;
  return (
    <Modal
      visible={visible}
      animationType="slide"
      presentationStyle="pageSheet"
      onRequestClose={onClose}
    >
      <ScrollView
        style={styles.screen}
        contentContainerStyle={styles.body}
        keyboardShouldPersistTaps="handled"
      >
        <View style={styles.top}>
          <View>
            <Ribbon label="Character" />
            <Text style={styles.title}>Your Collector</Text>
          </View>
          <View style={styles.corner}>
            <Pressable
              style={dim(styles.cog)}
              hitSlop={8}
              onPress={onSettings}
              accessibilityRole="button"
              accessibilityLabel="Settings"
            >
              <Icon name="settings" size={24} color={color.ink} />
            </Pressable>
            <CloseButton onPress={onClose} label="Close Collector" />
          </View>
        </View>

        {/* A character sheet: the plate, the class, the rank and a bar for
            each thing the next one wants (docs/10, "Game menus"). */}
        <Velvet style={styles.hero} accessible testID="collector-page">
          <Plate size={128} on>
            <CollectorLook id={chosen.id} stage={stage} size={120} />
          </Plate>
          <View style={styles.sheet}>
            <Foil style={styles.tag}>
              <Text style={styles.tagText}>{chosen.name.toUpperCase()}</Text>
            </Foil>
            <Text style={styles.rank} accessibilityRole="header" numberOfLines={2}>
              {chosen.ranks[stage]}
            </Text>
            <Text style={styles.of}>{`Rank ${stage + 1} of ${STAGES.length}`}</Text>
            <Scale name="Lockets" have={lockets} need={next && STAGES[stage + 1]} />
            <Scale name="Added" have={filed} need={next && FILED[stage + 1]} />
          </View>
        </Velvet>

        <Text style={styles.groupTitle}>Your name</Text>
        <TextInput
          style={styles.name}
          value={displayName}
          onChangeText={onDisplayName}
          placeholder="Anonymous"
          placeholderTextColor={color.inkFaint}
          maxLength={60}
          autoCapitalize="words"
          accessibilityLabel="The name your memories are signed with"
        />
        <Text style={styles.nameNote}>
          {nameError ?? 'Signs the memories you leave. Blank stays anonymous.'}
        </Text>

        <Text style={styles.groupTitle}>Evolution</Text>
        <View style={styles.chain}>
          {STAGES.map((at, i) => (
            <View
              key={at}
              style={[styles.link, i === stage && styles.linkNow, i > stage && styles.linkAhead]}
              accessible
              accessibilityLabel={
                i <= stage
                  ? `${chosen.ranks[i]}, reached`
                  : `${chosen.ranks[i]}, at ${at} lockets and ${FILED[i]} added`
              }
            >
              <CollectorLook id={chosen.id} stage={i} size={36} ahead={i > stage} />
            </View>
          ))}
        </View>

        {want && (
          <Panel title={`Next: ${chosen.ranks[stage + 1]}`} style={styles.next}>
            {wantsWords(want) !== '' && (
              <Text
                style={styles.wants}
              >{`${wantsWords(want)} to ${chosen.ranks[stage + 1]}`}</Text>
            )}
            <Goal text={`Open ${STAGES[stage + 1]} lockets`} met={want.lockets === 0} />
            <Goal
              text={`Leave ${FILED[stage + 1]} ${FILED[stage + 1] === 1 ? 'memory' : 'memories'}`}
              met={want.filed === 0}
            />
          </Panel>
        )}
        {want && want.filed > 0 && (
          <Button
            kind="go"
            label="Leave a memory here"
            glyph="plus"
            onPress={onAdd}
            accessibilityHint="Files a memory where you stand"
            place={styles.add}
          />
        )}
      </ScrollView>
    </Modal>
  );
}

/** One thing the next rank wants, as a bar on the sheet: "4 / 8". */
function Scale({ name, have, need }: { name: string; have: number; need: number | false }) {
  return (
    <View style={styles.scale}>
      <View style={styles.scaleTop}>
        <Text style={styles.scaleName}>{name.toUpperCase()}</Text>
        <Text style={styles.scaleCount}>{need ? `${have} / ${need}` : have}</Text>
      </View>
      <Bar into={need ? Math.min(1, have / need) : 1} height={8} />
    </View>
  );
}

/** A line on the next rank's checklist: a foil check once met. */
function Goal({ text, met }: { text: string; met: boolean }) {
  return (
    <View style={styles.goal} accessible accessibilityLabel={`${text}${met ? ', done' : ''}`}>
      {met ? (
        <Coin size={26}>
          <Glyph name="checkmark" size={12} weight="bold" color={foil.text} />
        </Coin>
      ) : (
        <View style={styles.goalOpen} />
      )}
      <Text style={[styles.goalText, met && styles.goalMet]}>{text}</Text>
    </View>
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
  corner: { flexDirection: 'row', alignItems: 'center', gap: 14 },
  cog: { padding: 6 },
  hero: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 16,
    marginTop: 20,
    padding: 16,
    borderRadius: 24,
    borderWidth: 1.5,
    borderColor: color.edge,
  },
  sheet: { flex: 1, gap: 6 },
  tag: { alignSelf: 'flex-start', paddingHorizontal: 8, paddingVertical: 3, borderRadius: 8 },
  tagText: { ...font.display, fontSize: 10, letterSpacing: 1.4, color: foil.text },
  rank: { ...screenTitle, fontSize: 24, lineHeight: 28, color: color.onVelvet },
  of: { ...font.uiBold, fontSize: 12, color: color.onVelvetGold },
  scale: { gap: 3, marginTop: 4 },
  scaleTop: { flexDirection: 'row', justifyContent: 'space-between' },
  scaleName: { ...font.uiBold, fontSize: 11, letterSpacing: 1, color: color.onVelvetSoft },
  scaleCount: { ...font.uiBold, fontSize: 11, color: color.onVelvetSoft },
  name: { ...input, ...font.title, fontSize: 22, marginTop: 10 },
  nameNote: {
    ...font.ui,
    fontSize: 13,
    lineHeight: 20,
    color: color.inkFaint,
    marginTop: 6,
    marginLeft: 4,
  },
  groupTitle: { ...label, fontSize: 12, color: color.inkFaint, marginTop: 28, marginLeft: 4 },
  // The eight looks side by side, the ones ahead as silhouettes.
  chain: { flexDirection: 'row', justifyContent: 'space-between', marginTop: 10 },
  link: {
    width: 40,
    height: 48,
    borderTopLeftRadius: 20,
    borderTopRightRadius: 20,
    borderRadius: 8,
    alignItems: 'center',
    justifyContent: 'flex-end',
    overflow: 'hidden',
    backgroundColor: color.paperRaised,
    borderWidth: 1,
    borderColor: color.goldLine,
  },
  linkNow: { borderWidth: 2.5, borderColor: color.plum },
  linkAhead: { backgroundColor: color.quiet, borderColor: color.quiet },
  next: { marginTop: 28, gap: 10 },
  wants: { ...font.ui, fontSize: 13, color: color.inkFaint },
  goal: { flexDirection: 'row', alignItems: 'center', gap: 10, minHeight: 32 },
  goalOpen: {
    width: 26,
    height: 26,
    borderRadius: 13,
    borderWidth: 2,
    borderColor: color.rule,
  },
  goalText: { ...font.uiMedium, fontSize: 16, color: color.ink },
  goalMet: { color: color.inkFaint },
  add: { marginTop: 16 },
});
