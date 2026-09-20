/** The third tab. No account, so it is about the walking, not the person.
 *
 * There is nothing to log into and nothing synced, which makes this tab two
 * honest jobs: say what this device has done, and be the one place that
 * explains the rule the whole app is built on. Every app with a proximity gate
 * needs somewhere to answer "why can I not read this", and burying that in a
 * sheet that only appears when you are already frustrated is too late.
 */

import { Linking, Pressable, ScrollView, StyleSheet, Text, View } from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';

import { API_BASE } from './api.ts';
import Padlock from './Padlock.tsx';

type Props = {
  unlockedCount: number;
  placeCount: number;
  radiusMeters: number;
  /** 'granted' | 'denied' | 'blocked' | 'unknown', mirrored from App. */
  permission: string;
  onRequestLocation: () => void;
};

export default function Settings({
  unlockedCount,
  placeCount,
  radiusMeters,
  permission,
  onRequestLocation,
}: Props) {
  const insets = useSafeAreaInsets();
  const granted = permission === 'granted';

  return (
    <ScrollView
      style={styles.screen}
      contentContainerStyle={[styles.body, { paddingTop: insets.top + 14 }]}
    >
      <Text style={styles.title}>You</Text>

      <View style={styles.stats}>
        <Stat value={unlockedCount} label={unlockedCount === 1 ? 'memory' : 'memories'} />
        <Stat value={placeCount} label={placeCount === 1 ? 'place' : 'places'} />
      </View>
      <Text style={styles.statsNote}>
        {unlockedCount === 0
          ? 'Nothing unlocked yet.'
          : 'Everything you opened by being there. Yours to reread.'}
      </Text>

      <Section title="How unlocking works">
        <Row>
          <Padlock size={17} color="#a1a1aa" />
          <Text style={styles.rowText}>
            Memories filed at a real address stay shut until you are within{' '}
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
        <Pressable style={styles.action} onPress={onRequestLocation} accessibilityRole="button">
          <Text style={styles.actionText}>
            {granted ? 'Manage in Settings' : 'Turn on location'}
          </Text>
        </Pressable>
      </Section>

      <Section title="About">
        <Pressable
          style={styles.link}
          accessibilityRole="link"
          onPress={() => Linking.openURL(`${API_BASE}/privacy`).catch(() => {})}
        >
          <Text style={styles.linkText}>Privacy policy</Text>
        </Pressable>
        <Text style={styles.note}>
          No account, no sign-in, nothing synced. Your unlocked memories live on this device, which
          also means a new phone starts empty.
        </Text>
      </Section>
    </ScrollView>
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
  screen: { flex: 1, backgroundColor: '#fff' },
  body: { paddingHorizontal: 24, paddingBottom: 40, gap: 6 },
  title: { fontSize: 30, fontWeight: '700', color: '#18181b', letterSpacing: -0.6 },
  stats: { flexDirection: 'row', gap: 32, marginTop: 20 },
  stat: { flexDirection: 'row', alignItems: 'baseline', gap: 7 },
  statValue: { fontSize: 40, fontWeight: '700', color: '#18181b', letterSpacing: -1.2 },
  statLabel: { fontSize: 15, color: '#71717a' },
  statsNote: { fontSize: 14, color: '#a1a1aa', marginTop: 6 },
  section: { marginTop: 34, gap: 10 },
  sectionTitle: {
    fontSize: 12,
    fontWeight: '700',
    letterSpacing: 0.8,
    textTransform: 'uppercase',
    color: '#a1a1aa',
  },
  row: { flexDirection: 'row', alignItems: 'flex-start', gap: 10 },
  rowText: { flex: 1, fontSize: 15, lineHeight: 23, color: '#3f3f46' },
  note: { fontSize: 14, lineHeight: 22, color: '#a1a1aa' },
  action: {
    alignSelf: 'flex-start',
    marginTop: 4,
    borderWidth: 1.5,
    borderColor: '#e4e4e7',
    paddingVertical: 11,
    paddingHorizontal: 20,
    borderRadius: 12,
  },
  actionText: { fontSize: 15, fontWeight: '600', color: '#3f3f46' },
  link: { alignSelf: 'flex-start' },
  linkText: { fontSize: 15, color: '#3f3f46', textDecorationLine: 'underline' },
});
