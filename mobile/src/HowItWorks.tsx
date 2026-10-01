/** What the steps pill opens: how the app works, in the words of what you
 *  can see on the map. The balance on top, then the four rules under it. */

import { Modal, Pressable, ScrollView, StyleSheet, Text, View } from 'react-native';

import type { Profile } from './api.ts';
import CloseButton from './CloseButton.tsx';
import { count } from './format.ts';
import { button, buttonText, color, dim, figure, font, label } from './theme.ts';
import type { Wallet } from './wallet.ts';

type Props = {
  visible: boolean;
  onClose: () => void;
  wallet: Wallet | null;
  profile: Profile | null;
  radiusMeters: number;
  /** Close this and open the paywall: one sheet at a time. */
  onSubscribe: () => void;
};

export default function HowItWorks({ visible, onClose, wallet, profile, radiusMeters, onSubscribe }: Props) {
  const free = profile?.free_per_day ?? 3;
  const price = (profile?.steps_per_unlock ?? 1000).toLocaleString();
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
            <Text style={styles.unit}>{wallet.unit}</Text>
          </View>
        )}

        <Section title="Every pin is a story">
          Something happened right there. It stays locked until you stand within{' '}
          {Math.round(radiusMeters)} m of it.
        </Section>
        <Section title="Opening one">
          {profile?.subscribed
            ? "You're subscribed: anything you stand on opens."
            : `Each day, ${count(free)} open free, from anywhere. After that, each costs ${price} steps, and you have to be standing there.`}
        </Section>
        <Section title="Your steps">
          Your phone counts them, even with the app closed, and they land here when you open
          it. Only walking counts.
        </Section>
        <Section title="Wander, or take a walk">
          Walk anywhere and open what you pass. Or Plan a walk: a route past a few stories, in
          order.
        </Section>

        {profile && !profile.subscribed && (
          <Pressable style={dim(styles.action)} accessibilityRole="button" onPress={onSubscribe}>
            <Text style={styles.actionText}>Open everything you stand on</Text>
          </Pressable>
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
  sectionTitle: { ...label },
  text: { ...font.prose, fontSize: 17, lineHeight: 27, color: color.ink },
  action: { ...button.outline, alignSelf: 'flex-start', marginTop: 30 },
  actionText: { ...buttonText, color: color.ink },
});
