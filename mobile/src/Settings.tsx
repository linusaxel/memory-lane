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
import Padlock from './Padlock.tsx';
import SignIn from './SignIn.tsx';
import type { Permission } from './types.ts';
import { button, buttonText, color, dim, font, input, label } from './theme.ts';

type Props = {
  visible: boolean;
  onClose: () => void;
  /** Close this and open the paywall: one sheet at a time. */
  onSubscribe: () => void;
  unlockedCount: number;
  placeCount: number;
  submittedCount: number;
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
          <Pressable style={dim()} onPress={onClose} accessibilityRole="button" accessibilityLabel="Close">
            <Text style={styles.close}>Close</Text>
          </Pressable>
        </View>
        <View style={styles.stats}>
          <Stat value={unlockedCount} label={unlockedCount === 1 ? 'memory' : 'memories'} />
          <Stat value={placeCount} label={placeCount === 1 ? 'place' : 'places'} />
          {submittedCount > 0 && <Stat value={submittedCount} label="added" />}
        </View>
        <Text style={styles.statsNote}>
          {unlockedCount === 0
            ? 'Nothing unlocked yet.'
            : 'Everything you opened by being there. Yours to reread.'}
        </Text>

        <Section title="Your name">
          <Text style={styles.note}>
            What your own memories are signed with, and the only thing here anybody else sees. Leave
            it blank to post as Anonymous.
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
                {new Date(`${profile.subscribed_until}Z`).toLocaleDateString()}. Any memory you
                stand on opens, walk or no walk.
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
            <Padlock size={17} color={color.faded} />
            <Text style={styles.rowText}>
              Memories added at a real address stay shut until you are within{' '}
              {Math.round(radiusMeters)} m of them.
            </Text>
          </Row>
          <Text style={styles.note}>
            The server withholds the text, not the app — so there is no way to read one from your
            sofa, and no reason to pretend otherwise.
          </Text>
          <Text style={styles.note}>
            Memories the source could only place by city are open to everyone. Asking you to walk to
            a guess would be a lie.
          </Text>
        </Section>

        <Section title="Location">
          <Text style={styles.rowText}>
            {granted
              ? 'On. Used to work out which memories are in reach, and never stored.'
              : 'Off. Nothing can unlock without it.'}
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
            Off by default. Turning it on asks for location in the background, which is more than
            the map needs — used only to check your position against memories you haven't reached
            yet, on this device, and never for anything else.
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
            onPress={() => Linking.openURL('https://www.openstreetmap.org/copyright').catch(() => {})}
          >
            <Text style={styles.linkText}>Places © OpenStreetMap contributors</Text>
          </Pressable>
          <Text style={styles.note}>
            Signed out, your collection is tied to this installation rather than to you. Signing in
            with Google or Apple is the only thing that changes that.
          </Text>
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
  top: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'baseline' },
  title: { fontFamily: font.display, fontSize: 34, color: color.ink },
  close: { ...label, color: color.ink },
  stats: { flexDirection: 'row', gap: 36, marginTop: 12 },
  stat: { flexDirection: 'row', alignItems: 'baseline', gap: 8 },
  statValue: { fontFamily: font.display, fontSize: 46, color: color.ink, letterSpacing: -1 },
  statLabel: { ...label, fontSize: 10 },
  statsNote: { fontFamily: font.prose, fontSize: 15, color: color.inkFaint, marginTop: 10 },
  section: { marginTop: 38, gap: 12, borderTopWidth: 1, borderTopColor: color.rule, paddingTop: 18 },
  sectionTitle: { ...label },
  row: { flexDirection: 'row', alignItems: 'flex-start', gap: 12 },
  rowText: { flex: 1, fontFamily: font.prose, fontSize: 17, lineHeight: 27, color: color.ink },
  note: { fontFamily: font.prose, fontSize: 15, lineHeight: 24, color: color.inkFaint },
  action: { ...button.outline, alignSelf: 'flex-start', marginTop: 6 },
  actionText: { ...buttonText, color: color.ink },
  input: {
    ...input,
  },
  // Seal, matching Submit's error line. The accent is spoken for by the unlock
  // everywhere else; an error that failed to save is the one other thing the
  // app says in red, and splitting that across two treatments would be worse.
  saveFailed: { fontFamily: font.mono, fontSize: 13, lineHeight: 20, color: color.seal },
  link: { alignSelf: 'flex-start' },
  linkText: {
    fontFamily: font.monoMedium,
    fontSize: 13,
    color: color.ink,
    textDecorationLine: 'underline',
  },
});
