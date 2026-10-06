/** What the level pill opens: your level, every walk and every memory you
 *  opened, drawn as its locket, on top; then how the app works, in the order
 *  you meet it (docs/10, "Walks earn XP; rare memories wait for a level" and
 *  "No keys; your memories are your lockets"). */

import { useEffect, useState } from 'react';
import {
  Image,
  Modal,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  View,
  useWindowDimensions,
} from 'react-native';

import { fetchWalked, type Profile, type WalkedRoute } from './api.ts';
import CloseButton from './CloseButton.tsx';
import DiamondRule from './DiamondRule.tsx';
import { LOCKETS, locketOf } from './lockets.ts';
import { loadWalked } from './route.ts';
import { color, font, label, radius, screenTitle } from './theme.ts';
import type { UnlockedMemory } from './unlocked.ts';
import WalkCard from './WalkCard.tsx';

type Props = {
  visible: boolean;
  onClose: () => void;
  profile: Profile | null;
  device: string | null;
  /** A card tapped: show that walk on the map. */
  onOpenWalk: (walk: WalkedRoute) => void;
  /** Every memory opened, newest first: the journal's Unlocked list. */
  opened: UnlockedMemory[];
  onOpenMemory: (memory: UnlockedMemory) => void;
  radiusMeters: number;
  /** The memory sheet, so it opens over this one (as the journal does). */
  children?: React.ReactNode;
};

export default function HowItWorks({
  visible,
  onClose,
  profile,
  device,
  radiusMeters,
  onOpenWalk,
  opened,
  onOpenMemory,
  children,
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
  // Two to a row, between the sheet's 24pt margins and one 12pt gap; a
  // memory's locket takes half of that, four to a row.
  const card = (useWindowDimensions().width - 48 - 12) / 2;
  const level = profile?.level ?? 1;
  const xp = profile?.xp ?? 0;
  const next = profile?.xp_next ?? 50;
  return (
    <Modal
      visible={visible}
      animationType="slide"
      presentationStyle="pageSheet"
      onRequestClose={onClose}
    >
      <ScrollView style={styles.screen} contentContainerStyle={styles.body}>
        <View style={styles.top}>
          <Text style={styles.title} accessibilityRole="header">{`Level ${level}`}</Text>
          <CloseButton onPress={onClose} />
        </View>
        <View style={styles.xpRow}>
          <Text style={styles.xp}>{`${xp.toLocaleString()} / ${next.toLocaleString()} XP`}</Text>
          {next > xp && (
            <Text
              style={styles.unit}
            >{`${(next - xp).toLocaleString()} XP to Level ${level + 1}`}</Text>
          )}
        </View>
        <View style={styles.bar}>
          <View style={[styles.fill, { width: `${Math.min(100, (xp / next) * 100)}%` }]} />
        </View>
        <DiamondRule place={styles.rule} />

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

        {/* Every memory opened, as its locket. Extracted memories draw theirs
            at random, so the count of each kind is a detail, not a set to
            finish. */}
        <Text style={styles.shelfTitle}>
          {opened.length
            ? `${opened.length} ${opened.length === 1 ? 'memory' : 'memories'}`
            : 'Your first memory goes here'}
        </Text>
        <View style={[styles.kinds, styles.case]}>
          {LOCKETS.map((locket) => {
            const count = opened.filter((m) => locketOf(m.locket).id === locket.id).length;
            return (
              <View key={locket.id} style={[styles.kind, !count && styles.none]}>
                <Image source={count ? locket.opened : locket.locked} style={styles.kindImage} />
                <Text style={styles.unit}>{count}</Text>
              </View>
            );
          })}
        </View>
        <View style={styles.shelf}>
          {opened.map((memory) => (
            <Pressable
              key={memory.id}
              style={[styles.locket, { width: (card - 12) / 2 }]}
              onPress={() => onOpenMemory(memory)}
              testID="opened-locket"
              accessibilityRole="button"
              accessibilityLabel={memory.place.name}
            >
              <Image source={locketOf(memory.locket).opened} style={styles.locketImage} />
              <Text style={styles.unit} numberOfLines={1}>
                {memory.place.name}
              </Text>
            </Pressable>
          ))}
        </View>

        <Text style={styles.shelfTitle}>How it works</Text>
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
          Every walk is kept above, drawn as its shape, and every memory as its locket.
        </Section>
        <Section title={profile?.subscribed ? 'Walk as much as you like' : 'One walk a day'}>
          {profile?.subscribed
            ? "You're subscribed: plan a new walk whenever you finish one."
            : 'Your first walk each day is free. Subscribe for as many as you like.'}
        </Section>
      </ScrollView>
      {children}
    </Modal>
  );
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <View style={styles.section}>
      <View style={styles.bullet} />
      <View style={styles.sectionText}>
        <Text style={styles.sectionTitle}>{title}</Text>
        <Text style={styles.text}>{children}</Text>
      </View>
    </View>
  );
}

// Settings' sheet, so the two read as one app.
const styles = StyleSheet.create({
  screen: { flex: 1, backgroundColor: color.paper },
  body: { paddingHorizontal: 24, paddingTop: 28, paddingBottom: 72, gap: 6 },
  top: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' },
  title: { ...screenTitle, fontSize: 44, lineHeight: 52 },
  xpRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'baseline',
    marginTop: 8,
  },
  xp: { ...font.uiBold, fontSize: 17, color: color.plum },
  bar: { height: 10, borderRadius: 5, backgroundColor: color.track, marginTop: 10 },
  fill: { height: 10, borderRadius: 5, backgroundColor: color.plum },
  rule: { marginTop: 24 },
  unit: { ...label, fontSize: 12 },
  shelfTitle: { ...label, fontSize: 15, color: color.inkSoft, marginTop: 24 },
  shelf: { flexDirection: 'row', flexWrap: 'wrap', gap: 12, marginTop: 10 },
  kinds: { flexDirection: 'row', justifyContent: 'space-between', marginTop: 10 },
  // The lockets in their case: plum, edged in gold.
  case: {
    padding: 16,
    borderRadius: radius.card,
    borderWidth: 1,
    borderColor: color.goldLine,
    backgroundColor: color.track,
  },
  kind: { alignItems: 'center', gap: 2 },
  none: { opacity: 0.35 },
  kindImage: { width: 40, height: 40, resizeMode: 'contain' },
  locket: { alignItems: 'center', gap: 4 },
  locketImage: { width: 56, height: 56, resizeMode: 'contain' },
  section: { flexDirection: 'row', gap: 14, marginTop: 16 },
  bullet: {
    width: 10,
    height: 10,
    marginTop: 7,
    transform: [{ rotate: '45deg' }],
    backgroundColor: color.seal,
    borderWidth: 1,
    borderColor: color.goldLine,
  },
  sectionText: { flex: 1, gap: 4 },
  // The heading is the rule, so it reads first; the line under it is the why.
  sectionTitle: { ...font.uiBold, fontSize: 18, lineHeight: 24, color: color.ink },
  text: { ...font.prose, fontSize: 16, lineHeight: 25, color: color.inkSoft },
});
