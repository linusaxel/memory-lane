/** What the level pill opens: your level and keepsakes on top, then how the
 *  app works, in the order you meet it (docs/10, "A walk planner, nothing
 *  else" and "Walks earn XP; rare memories wait for a level"). */

import { Modal, ScrollView, StyleSheet, Text, View } from 'react-native';

import type { Item, Profile } from './api.ts';
import CloseButton from './CloseButton.tsx';
import Glyph from './Glyph.tsx';
import { color, figure, font, label } from './theme.ts';

type Props = {
  visible: boolean;
  onClose: () => void;
  profile: Profile | null;
  radiusMeters: number;
};

export default function HowItWorks({ visible, onClose, profile, radiusMeters }: Props) {
  const found = new Map((profile?.items ?? []).map((item) => [item.index, item]));
  return (
    <Modal visible={visible} animationType="slide" presentationStyle="pageSheet" onRequestClose={onClose}>
      <ScrollView style={styles.screen} contentContainerStyle={styles.body}>
        <View style={styles.top}>
          <Text style={styles.title}>Your walks</Text>
          <CloseButton onPress={onClose} />
        </View>
        <View style={styles.now}>
          <Text style={styles.figure}>{`Level ${profile?.level ?? 1}`}</Text>
          <Text style={styles.unit}>
            {`${(profile?.xp ?? 0).toLocaleString()} / ${(profile?.xp_next ?? 50).toLocaleString()} XP`}
          </Text>
        </View>

        {/* Every keepsake there is, the ones not found yet as a blank. */}
        <Text style={styles.shelfTitle}>{`Keepsakes · ${found.size} of ${profile?.items_total ?? 0}`}</Text>
        <View style={styles.shelf}>
          {Array.from({ length: profile?.items_total ?? 0 }, (_, i) => (
            <Keepsake key={i} item={found.get(i)} />
          ))}
        </View>

        {/* Each heading is the rule on its own, the line under it a picture
            or a reason; one number each, said as something you can feel.
            docs/09 part 11 has the research. */}
        <Section title="Plan a walk">
          Memory Lane plans a walk past memories near you, about one a kilometre. The list
          shows what each one is about. Don't like them? Try another walk.
        </Section>
        <Section title="Stand there to read it">
          Every stop is a memory of something that happened right there. Get within{' '}
          {Math.round(radiusMeters)} m, about the width of a street, and hold the ring.
          Memories only open on a walk.
        </Section>
        <Section title="Finish it to level up">
          Reach every stop and the walk counts: ten XP a memory, ten a kilometre, one walk a
          day. Now and then one leaves a keepsake. From level 4, the rarest stories near you
          can join your walks.
        </Section>
        <Section title={profile?.subscribed ? 'Walk as much as you like' : 'One walk a day'}>
          {profile?.subscribed
            ? "You're subscribed: plan a new walk whenever you finish one."
            : 'Your first walk each day is free. Subscribe for as many as you like.'}
        </Section>

      </ScrollView>
    </Modal>
  );
}

function Keepsake({ item }: { item: Item | undefined }) {
  return (
    <View
      style={styles.keepsake}
      accessible
      accessibilityLabel={item ? `${item.name}. ${item.line}` : 'Not found yet'}
    >
      <Glyph
        // The server names the symbol; an unknown one draws nothing, not a crash.
        name={(item?.glyph ?? 'questionmark') as 'questionmark'}
        size={22}
        color={item ? color.ember : color.rule}
      />
      <Text style={styles.keepsakeName} numberOfLines={2}>
        {item ? `${item.name}${item.count > 1 ? ` ×${item.count}` : ''}` : ' '}
      </Text>
    </View>
  );
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <View style={styles.section}>
      <Text style={styles.sectionTitle}>{title}</Text>
      <Text style={styles.text}>{children}</Text>
    </View>
  );
}

// Settings' sheet, so the two read as one app.
const styles = StyleSheet.create({
  screen: { flex: 1, backgroundColor: color.paper },
  body: { paddingHorizontal: 24, paddingTop: 28, paddingBottom: 72, gap: 6 },
  top: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' },
  title: { ...font.display, fontSize: 34, color: color.ink },
  now: { flexDirection: 'row', alignItems: 'baseline', gap: 8, marginTop: 12 },
  figure,
  unit: { ...label, fontSize: 12 },
  shelfTitle: { ...label, fontSize: 12, marginTop: 24 },
  shelf: { flexDirection: 'row', flexWrap: 'wrap', gap: 8, marginTop: 10 },
  keepsake: {
    width: 76,
    minHeight: 76,
    alignItems: 'center',
    gap: 6,
    paddingVertical: 10,
    borderRadius: 14,
    borderWidth: 1,
    borderColor: color.rule,
  },
  keepsakeName: { ...font.prose, fontSize: 11, lineHeight: 14, color: color.inkSoft, textAlign: 'center' },
  section: { marginTop: 30, gap: 8, borderTopWidth: 1, borderTopColor: color.rule, paddingTop: 18 },
  // The heading is the rule, so it reads first; the line under it is the why.
  sectionTitle: { ...font.displaySemi, fontSize: 19, lineHeight: 25, color: color.ink },
  text: { ...font.prose, fontSize: 16, lineHeight: 25, color: color.inkSoft },
});
