/** What the keys pill opens: how the app works, in the words of what you
 *  can see on the map. The balance on top, then the rules in the order you
 *  meet them. */

import { Modal, ScrollView, StyleSheet, Text, View } from 'react-native';

import type { Profile } from './api.ts';
import CloseButton from './CloseButton.tsx';
import { color, figure, font, label } from './theme.ts';
import type { Wallet } from './wallet.ts';

type Props = {
  visible: boolean;
  onClose: () => void;
  wallet: Wallet | null;
  profile: Profile | null;
  radiusMeters: number;
};

export default function HowItWorks({ visible, onClose, wallet, profile, radiusMeters }: Props) {
  return (
    <Modal visible={visible} animationType="slide" presentationStyle="pageSheet" onRequestClose={onClose}>
      <ScrollView style={styles.screen} contentContainerStyle={styles.body}>
        <View style={styles.top}>
          <Text style={styles.title}>How it works</Text>
          <CloseButton onPress={onClose} />
        </View>
        {wallet && (
          <View style={styles.now}>
            <Text style={styles.figure}>{wallet.figure.toLocaleString()}</Text>
            <Text style={styles.unit}>
              {wallet.starting ? 'to start' : wallet.figure === 1 ? 'key' : 'keys'}
            </Text>
          </View>
        )}

        {/* Each heading is the rule on its own, the line under it a picture
            or a reason; one number each, said as something you can feel.
            docs/09 part 11 has the research. */}
        <Section title="Stand on a pin to read it">
          Every pin is a memory of something that happened right there. Get within{' '}
          {Math.round(radiusMeters)} m, about the width of a street, and hold the ring.
        </Section>
        {profile?.subscribed ? (
          <Section title="Anything you stand on opens">
            You're subscribed: every pin you reach opens, as many as you like.
          </Section>
        ) : (
          <>
            <Section title="Your first one is on us">
              Pick one and open it from anywhere: the sofa, the bus, the other side of town.
              Just the one.
            </Section>
            <Section title="Today's walk is on us">
              Tap Plan a walk for a loop past a few memories. Every stop on it opens for
              nothing, and finishing it earns a key. One walk a day.
            </Section>
            <Section title="A key opens the rest">
              Wander off the walk and any memory you stand on opens with a key. You still have
              to be standing there.
            </Section>
          </>
        )}

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
