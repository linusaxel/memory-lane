/** Settings: a sheet of its own, opened from the cog on the map.
 *
 * The account, and the answer to "why can I not read this". Every app with a
 * proximity gate needs somewhere to answer that, and a sheet you only see once
 * you are already frustrated is too late. Who you are (the photo, the name,
 * the numbers) is the journal's header, not here.
 */

import {
  Linking,
  Modal,
  Pressable,
  ScrollView,
  StyleSheet,
  Switch,
  Text,
  View,
} from 'react-native';

import { API_BASE, type Profile } from './api.ts';
import { manage } from './purchases.ts';
import CloseButton from './CloseButton.tsx';
import SignIn from './SignIn.tsx';
import Glyph from './Glyph.tsx';
import type { Permission } from './types.ts';
import { button, buttonText, color, dim, font, label } from './theme.ts';

type Props = {
  visible: boolean;
  onClose: () => void;
  /** Close this and open the paywall: one sheet at a time. */
  onSubscribe: () => void;
  device: string | null;
  profile: Profile | null;
  onProfile: (next: Profile) => void;
  radiusMeters: number;
  permission: Permission;
  onRequestLocation: () => void;
  /** Off until chosen. Turning it on asks for background location, which is
   *  the one permission this screen has to explain before the OS prompt does. */
  notifyNearby: boolean;
  onNotifyNearby: (next: boolean) => void;
};

export default function Settings({
  visible,
  onClose,
  device,
  profile,
  onProfile,
  radiusMeters,
  permission,
  onRequestLocation,
  notifyNearby,
  onNotifyNearby,
  onSubscribe,
}: Props) {
  const granted = permission === 'granted';

  return (
    <Modal visible={visible} animationType="slide" presentationStyle="pageSheet" onRequestClose={onClose}>
      <ScrollView style={styles.screen} contentContainerStyle={styles.body}>
        <View style={styles.top}>
          <Text style={styles.title}>Settings</Text>
          <CloseButton onPress={onClose} label="Close settings" />
        </View>
        <Section title="Account">
          <SignIn device={device} profile={profile} onProfile={onProfile} />
          {profile?.subscribed ? (
            <>
              <Text style={styles.note}>
                Subscribed until{' '}
                {new Date(`${profile.subscribed_until}Z`).toLocaleDateString()}. Open any memory
                you stand on without spending a key.
              </Text>
              <Pressable
                style={dim(styles.action)}
                onPress={() => manage().catch(() => {})}
                accessibilityRole="button"
              >
                <Text style={styles.actionText}>Manage subscription</Text>
              </Pressable>
            </>
          ) : (
            profile?.user_id && (
              <Pressable style={dim(styles.action)} onPress={onSubscribe} accessibilityRole="button">
                <Text style={styles.actionText}>Subscribe</Text>
              </Pressable>
            )
          )}
        </Section>

        <Section title="How unlocking works">
          <Row>
            <Glyph name="lock.fill" size={15} color={color.faded} />
            <Text style={styles.rowText}>
              Memories stay locked until you're within {Math.round(radiusMeters)} m of them.
            </Text>
          </Row>
          <Text style={styles.note}>
            Your first one opens from anywhere. After that you have to be standing there:
            today's walk opens for nothing, and anywhere else costs a key. Finishing a walk
            earns one.
          </Text>
          <Text style={styles.note}>
            A few are only pinned to a city, not a spot. Those are open to everyone.
          </Text>
        </Section>

        <Section title="Location">
          <Text style={styles.rowText}>
            {granted
              ? "On. Used to tell when you're close to a memory, and never stored."
              : "Off. You'll need it to unlock anything."}
          </Text>
          <Pressable style={dim(styles.action)} onPress={onRequestLocation} accessibilityRole="button">
            <Text style={styles.actionText}>
              {granted ? 'Manage in Settings' : 'Turn on location'}
            </Text>
          </Pressable>
        </Section>

        <Section title="Notifications">
          <Row>
            <Text style={styles.rowText}>Tell me when a memory I haven't unlocked is nearby.</Text>
            <Switch
              value={notifyNearby}
              onValueChange={onNotifyNearby}
              accessibilityLabel="Notify me when a memory is nearby"
            />
          </Row>
          <Text style={styles.note}>
            This needs location in the background, only to check whether you're near a memory you
            haven't unlocked. Your position is never stored.
          </Text>
        </Section>

        <Section title="About">
          <Pressable
            style={dim(styles.link)}
            accessibilityRole="link"
            onPress={() => Linking.openURL(`${API_BASE}/privacy`).catch(() => {})}
          >
            <Text style={styles.linkText}>Privacy policy</Text>
          </Pressable>
          <Pressable
            style={dim(styles.link)}
            accessibilityRole="link"
            onPress={() => Linking.openURL(`${API_BASE}/privacy#contact`).catch(() => {})}
          >
            <Text style={styles.linkText}>Contact us</Text>
          </Pressable>
          <Pressable
            style={dim(styles.link)}
            accessibilityRole="link"
            onPress={() => Linking.openURL('https://www.openstreetmap.org/copyright').catch(() => {})}
          >
            <Text style={styles.linkText}>Places © OpenStreetMap contributors</Text>
          </Pressable>
        </Section>
      </ScrollView>
    </Modal>
  );
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <View style={styles.section}>
      <Text style={styles.sectionTitle}>{title}</Text>
      {children}
    </View>
  );
}

function Row({ children }: { children: React.ReactNode }) {
  return <View style={styles.row}>{children}</View>;
}

const styles = StyleSheet.create({
  screen: { flex: 1, backgroundColor: color.paper },
  body: { paddingHorizontal: 24, paddingTop: 28, paddingBottom: 72, gap: 6 },
  // The journal's title bar, so the two sheets read as one app.
  top: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' },
  title: { ...font.display, fontSize: 34, color: color.ink },
  section: { marginTop: 38, gap: 12, borderTopWidth: 1, borderTopColor: color.rule, paddingTop: 18 },
  sectionTitle: { ...label },
  row: { flexDirection: 'row', alignItems: 'flex-start', gap: 12 },
  rowText: { flex: 1, ...font.prose, fontSize: 17, lineHeight: 27, color: color.ink },
  note: { ...font.prose, fontSize: 15, lineHeight: 24, color: color.inkFaint },
  action: { ...button.outline, alignSelf: 'flex-start', marginTop: 6 },
  actionText: { ...buttonText, color: color.ink },
  link: { alignSelf: 'flex-start' },
  linkText: {
    ...font.uiMedium,
    fontSize: 13,
    color: color.ink,
    textDecorationLine: 'underline',
  },
});
