/** You: a sheet of its own, opened from the map's top-right corner.
 *
 * Three jobs: say what this device has done, hold the name submissions are
 * signed with, and answer "why can I not read this". Every app with a proximity
 * gate needs somewhere to answer that, and a sheet you only see once you are
 * already frustrated is too late.
 */

import {
  Linking,
  Modal,
  Pressable,
  ScrollView,
  StyleSheet,
  Switch,
  Text,
  TextInput,
  View,
} from 'react-native';

import { API_BASE, type Profile } from './api.ts';
import { manage } from './purchases.ts';
import CloseButton from './CloseButton.tsx';
import { count } from './format.ts';
import SignIn from './SignIn.tsx';
import Glyph from './Glyph.tsx';
import type { Permission } from './types.ts';
import { button, buttonText, color, dim, figure, font, input, label } from './theme.ts';

type Props = {
  visible: boolean;
  onClose: () => void;
  /** Close this and open the paywall: one sheet at a time. */
  onSubscribe: () => void;
  unlockedCount: number;
  placeCount: number;
  submittedCount: number;
  /** Every heart on what you filed, all time. */
  heartsReceived: number;
  /** Empty means Anonymous. Saved as it is typed, so there is no Save button
   *  to forget to press. */
  displayName: string;
  onDisplayName: (next: string) => void;
  /** Set when the last save did not land. The field keeps the typed value
   *  either way, so without this the name looks saved and is not. */
  nameError: string | null;
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
  unlockedCount,
  placeCount,
  submittedCount,
  heartsReceived,
  displayName,
  onDisplayName,
  nameError,
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
          <Text style={styles.title}>You</Text>
          <CloseButton onPress={onClose} />
        </View>
        <View style={styles.stats}>
          <Stat value={unlockedCount} label={unlockedCount === 1 ? 'memory' : 'memories'} />
          <Stat value={placeCount} label={placeCount === 1 ? 'place' : 'places'} />
          {submittedCount > 0 && <Stat value={submittedCount} label="added" />}
          {heartsReceived > 0 && (
            <Stat value={heartsReceived} label={heartsReceived === 1 ? 'heart' : 'hearts'} />
          )}
        </View>
        <Text style={styles.statsNote}>
          {unlockedCount === 0
            ? 'Nothing unlocked yet. Your first walk fixes that.'
            : 'Everything you unlock stays readable, even back home.'}
        </Text>

        <Section title="Your name">
          <Text style={styles.note}>
            Shown on the memories you leave. Leave it blank to stay anonymous.
          </Text>
          <TextInput
            style={styles.input}
            value={displayName}
            onChangeText={onDisplayName}
            placeholder="Anonymous"
            placeholderTextColor={color.inkFaint}
            maxLength={60}
            autoCapitalize="words"
            accessibilityLabel="The name your memories are signed with"
          />
          {nameError && <Text style={styles.saveFailed}>{nameError}</Text>}
        </Section>

        <Section title="Account">
          <SignIn device={device} profile={profile} onProfile={onProfile} />
          {profile?.subscribed ? (
            <>
              <Text style={styles.note}>
                Subscribed until{' '}
                {new Date(`${profile.subscribed_until}Z`).toLocaleDateString()}. Open any memory
                you stand on without spending steps.
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
            Each day, {count(profile?.free_per_day ?? 3)} open from anywhere. After that, each
            costs {(profile?.steps_per_unlock ?? 1000).toLocaleString()} steps, and you have to be
            standing there.
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

function Stat({ value, label }: { value: number; label: string }) {
  return (
    <View style={styles.stat}>
      <Text style={styles.statValue}>{value}</Text>
      <Text style={styles.statLabel}>{label}</Text>
    </View>
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
  stats: { flexDirection: 'row', flexWrap: 'wrap', columnGap: 36, rowGap: 16, marginTop: 12 },
  stat: { flexDirection: 'row', alignItems: 'baseline', gap: 8 },
  statValue: figure,
  statLabel: { ...label, fontSize: 12 },
  statsNote: { ...font.prose, fontSize: 15, color: color.inkFaint, marginTop: 10 },
  section: { marginTop: 38, gap: 12, borderTopWidth: 1, borderTopColor: color.rule, paddingTop: 18 },
  sectionTitle: { ...label },
  row: { flexDirection: 'row', alignItems: 'flex-start', gap: 12 },
  rowText: { flex: 1, ...font.prose, fontSize: 17, lineHeight: 27, color: color.ink },
  note: { ...font.prose, fontSize: 15, lineHeight: 24, color: color.inkFaint },
  action: { ...button.outline, alignSelf: 'flex-start', marginTop: 6 },
  actionText: { ...buttonText, color: color.ink },
  input: {
    ...input,
  },
  // Seal, matching Submit's error line. The accent is spoken for by the unlock
  // everywhere else; an error that failed to save is the one other thing the
  // app says in red, and splitting that across two treatments would be worse.
  saveFailed: { ...font.ui, fontSize: 13, lineHeight: 20, color: color.ember },
  link: { alignSelf: 'flex-start' },
  linkText: {
    ...font.uiMedium,
    fontSize: 13,
    color: color.ink,
    textDecorationLine: 'underline',
  },
});
