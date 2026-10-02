/** What the keys pill opens: how the app works, in the order you meet it.
 *  The keys on top, then the rules (docs/10, "A walk planner, nothing else"). */

import { Modal, ScrollView, StyleSheet, Text, View } from 'react-native';

import type { Profile } from './api.ts';
import CloseButton from './CloseButton.tsx';
import { color, figure, font, label } from './theme.ts';

type Props = {
  visible: boolean;
  onClose: () => void;
  keys: number;
  profile: Profile | null;
  radiusMeters: number;
};

export default function HowItWorks({ visible, onClose, keys, profile, radiusMeters }: Props) {
  return (
    <Modal visible={visible} animationType="slide" presentationStyle="pageSheet" onRequestClose={onClose}>
      <ScrollView style={styles.screen} contentContainerStyle={styles.body}>
        <View style={styles.top}>
          <Text style={styles.title}>How it works</Text>
          <CloseButton onPress={onClose} />
        </View>
        <View style={styles.now}>
          <Text style={styles.figure}>{keys.toLocaleString()}</Text>
          <Text style={styles.unit}>{keys === 1 ? 'key' : 'keys'}</Text>
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
        <Section title="Finish it for a key">
          Reach every stop and you earn a key. What keys open is coming soon.
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
  section: { marginTop: 30, gap: 8, borderTopWidth: 1, borderTopColor: color.rule, paddingTop: 18 },
  // The heading is the rule, so it reads first; the line under it is the why.
  sectionTitle: { ...font.displaySemi, fontSize: 19, lineHeight: 25, color: color.ink },
  text: { ...font.prose, fontSize: 16, lineHeight: 25, color: color.inkSoft },
});
