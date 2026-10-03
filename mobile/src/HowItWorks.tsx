/** What the level pill opens: your level and every walk on top, then how the
 *  app works, in the order you meet it (docs/10, "A walk planner, nothing
 *  else" and "Walks earn XP; rare memories wait for a level"). */

import { useEffect, useState } from 'react';
import { Modal, ScrollView, StyleSheet, Text, View, useWindowDimensions } from 'react-native';

import { fetchWalked, type Profile, type WalkedRoute } from './api.ts';
import CloseButton from './CloseButton.tsx';
import { loadWalked } from './route.ts';
import { color, figure, font, label } from './theme.ts';
import WalkCard from './WalkCard.tsx';

type Props = {
  visible: boolean;
  onClose: () => void;
  profile: Profile | null;
  device: string | null;
  /** A card tapped: show that walk on the map. */
  onOpenWalk: (walk: WalkedRoute) => void;
  radiusMeters: number;
};

export default function HowItWorks({
  visible,
  onClose,
  profile,
  device,
  radiusMeters,
  onOpenWalk,
}: Props) {
  // The journal's cache first, so it reads offline, then the server's.
  const [walks, setWalks] = useState<WalkedRoute[]>([]);
  useEffect(() => {
    if (!visible) return;
    loadWalked().then(setWalks);
    if (device)
      fetchWalked(device)
        .then(setWalks)
        .catch(() => {});
  }, [visible, device]);
  // Two to a row, between the sheet's 24pt margins and one 12pt gap.
  const card = (useWindowDimensions().width - 48 - 12) / 2;
  return (
    <Modal
      visible={visible}
      animationType="slide"
      presentationStyle="pageSheet"
      onRequestClose={onClose}
    >
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

        {/* Every walk you took, newest first, each drawn as its shape. */}
        <Text style={styles.shelfTitle}>
          {walks.length
            ? `${walks.length} ${walks.length === 1 ? 'walk' : 'walks'}`
            : 'Your first walk goes here'}
        </Text>
        <View style={styles.shelf}>
          {walks.map((walk, i) => (
            <WalkCard key={i} walk={walk} size={card} onPress={() => onOpenWalk(walk)} />
          ))}
        </View>

        {/* Each heading is the rule on its own, the line under it a picture
            or a reason; one number each, said as something you can feel.
            docs/09 part 11 has the research. */}
        <Section title="Plan a walk">
          Memory Lane plans a walk past memories near you, about one a kilometre. The list shows
          what each one is about. Don't like them? Try another walk.
        </Section>
        <Section title="Stand there to read it">
          Every stop is a memory of something that happened right there. Get within{' '}
          {Math.round(radiusMeters)} m, about the width of a street, and hold the ring. Memories
          only open on a walk.
        </Section>
        <Section title="Finish it to level up">
          Reach every stop and the walk counts: ten XP a memory, ten a kilometre, one walk a day.
          Every walk is kept above, drawn as its shape. From level 4, epic stories near you can join
          your walks, and you only find out which when one opens.
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
  shelf: { flexDirection: 'row', flexWrap: 'wrap', gap: 12, marginTop: 10 },
  section: { marginTop: 30, gap: 8, borderTopWidth: 1, borderTopColor: color.rule, paddingTop: 18 },
  // The heading is the rule, so it reads first; the line under it is the why.
  sectionTitle: { ...font.displaySemi, fontSize: 19, lineHeight: 25, color: color.ink },
  text: { ...font.prose, fontSize: 16, lineHeight: 25, color: color.inkSoft },
});
