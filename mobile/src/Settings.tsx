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
import { color, font, label } from './theme.ts';

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
          <Padlock size={17} color={color.faded} />
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
  screen: { flex: 1, backgroundColor: color.paper },
  body: { paddingHorizontal: 24, paddingBottom: 72, gap: 6 },
  title: { fontFamily: font.display, fontSize: 34, color: color.ink },
  stats: { flexDirection: 'row', gap: 36, marginTop: 24 },
  stat: { flexDirection: 'row', alignItems: 'baseline', gap: 8 },
  statValue: { fontFamily: font.display, fontSize: 46, color: color.ink, letterSpacing: -1 },
  statLabel: { ...label, fontSize: 10 },
  statsNote: { fontFamily: font.prose, fontSize: 15, color: color.inkFaint, marginTop: 10 },
  section: { marginTop: 38, gap: 12, borderTopWidth: 1, borderTopColor: color.rule, paddingTop: 18 },
  sectionTitle: { ...label },
  row: { flexDirection: 'row', alignItems: 'flex-start', gap: 12 },
  rowText: { flex: 1, fontFamily: font.prose, fontSize: 17, lineHeight: 27, color: color.ink },
  note: { fontFamily: font.prose, fontSize: 15, lineHeight: 24, color: color.inkFaint },
  action: {
    alignSelf: 'flex-start',
    marginTop: 6,
    borderWidth: 1,
    borderColor: color.ink,
    paddingVertical: 12,
    paddingHorizontal: 22,
    borderRadius: 4,
  },
  actionText: {
    fontFamily: font.monoBold,
    fontSize: 11,
    letterSpacing: 1.2,
    textTransform: 'uppercase',
    color: color.ink,
  },
  link: { alignSelf: 'flex-start' },
  linkText: {
    fontFamily: font.monoMedium,
    fontSize: 13,
    color: color.ink,
    textDecorationLine: 'underline',
  },
});
