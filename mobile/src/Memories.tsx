/** The "Memories" tab. Two sections, not two tabs: unlocking and filing are
 *  two different ways of ending up with a memory that is yours, and this is
 *  the one screen that shows both. Replaces what were `Collection.tsx` (the
 *  old "Unlocked" tab) and the modal `Manage` opened from Settings.
 *
 * **Unlocked** is local-first and cannot fail - it is exactly what
 * `unlocked.ts` holds, so it works on a train. **My memories** always asks
 * the server, because it has to show two things the local cache was never
 * told about: a memory still sealed (shut, seal included) and one enough
 * people reported (flagged, not dropped).
 */

import { useCallback, useEffect, useState } from 'react';
import {
  ActivityIndicator,
  Pressable,
  RefreshControl,
  ScrollView,
  StyleSheet,
  Text,
  View,
} from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';

import { fetchMine, type LocatedMemory } from './api.ts';
import Padlock from './Padlock.tsx';
import { when } from './format.ts';
import { color, dim, font, label } from './theme.ts';
import type { UnlockedMemory } from './unlocked.ts';

type Props = {
  unlocked: UnlockedMemory[];
  /** False until the local store has been read - see the old Collection's
   *  same-named prop. It is one boolean and not a `Status` because
   *  `loadUnlocked` cannot fail: it returns {} instead. */
  unlockedReady: boolean;
  onOpenUnlocked: (memory: UnlockedMemory) => void;

  device: string | null;
  /** Refetches My memories each time this turns true - the section has no
   *  other way to know the tab was left and come back to. */
  focused: boolean;
  /** Bumped by App.tsx after a save or a delete. The screen never unmounts,
   *  so those happen without `focused` re-firing - without this the section
   *  would go on showing what was filed until the tab was left and reopened. */
  refreshKey: number;
  onOpenMine: (memory: LocatedMemory) => void;
};

type MineStatus = 'loading' | 'ready' | 'failed';

export default function Memories({
  unlocked,
  unlockedReady,
  onOpenUnlocked,
  device,
  focused,
  refreshKey,
  onOpenMine,
}: Props) {
  const insets = useSafeAreaInsets();
  const [mine, setMine] = useState<LocatedMemory[]>([]);
  const [mineStatus, setMineStatus] = useState<MineStatus>('loading');
  const [refreshing, setRefreshing] = useState(false);

  const load = useCallback(() => {
    if (!device) return Promise.resolve();
    return fetchMine(device).then((rows) => {
      setMine(rows);
      setMineStatus('ready');
    });
  }, [device]);

  useEffect(() => {
    if (!focused || !device) return;
    let cancelled = false;
    setMineStatus('loading');
    load().catch(() => {
      if (!cancelled) setMineStatus('failed');
    });
    return () => {
      cancelled = true;
    };
  }, [focused, device, refreshKey, load]);

  // A pull down asks again without disturbing what's already on screen: a
  // failed pull leaves `mine`/`mineStatus` alone rather than swapping a
  // populated list for the "can't reach" empty state, same as a failed map
  // refresh keeps the last good pins (UI.md).
  const onRefresh = useCallback(() => {
    setRefreshing(true);
    load()
      .catch(() => {})
      .then(() => setRefreshing(false));
  }, [load]);

  return (
    <ScrollView
      style={styles.screen}
      contentContainerStyle={[styles.body, { paddingTop: insets.top + 14 }]}
      refreshControl={
        <RefreshControl
          refreshing={refreshing}
          onRefresh={onRefresh}
          tintColor={color.inkFaint}
          colors={[color.inkFaint]}
          progressBackgroundColor={color.paper}
        />
      }
    >
      <Text style={styles.title}>Memories</Text>

      <Section
        title="Unlocked"
        note={
          !unlockedReady
            ? ''
            : unlocked.length === 0
              ? 'Nothing yet.'
              : `${unlocked.length} ${unlocked.length === 1 ? 'memory' : 'memories'} you walked to`
        }
      >
        {/* No spinner: this is a disk read that resolves in a frame, and a
            spinner that flashes is worse than a beat of nothing. */}
        {!unlockedReady ? null : unlocked.length === 0 ? (
          <Empty text="Memories open when you stand where they happened. Whatever you open stays here." />
        ) : (
          unlocked.map((item) => (
            <Row
              key={item.id}
              place={item.place.name}
              summary={item.summary}
              meta={when(item.unlocked_at) ?? undefined}
              onPress={() => onOpenUnlocked(item)}
            />
          ))
        )}
      </Section>

      <Section
        title="My memories"
        note={
          mineStatus === 'ready' && mine.length > 0
            ? `${mine.length} ${mine.length === 1 ? 'memory' : 'memories'} you filed`
            : ''
        }
      >
        {mineStatus === 'loading' ? (
          <ActivityIndicator style={styles.spinner} color={color.inkFaint} />
        ) : mineStatus === 'failed' ? (
          <Empty text="Can't reach Memory Lane right now." />
        ) : mine.length === 0 ? (
          <Empty text="Nothing filed yet." />
        ) : (
          mine.map((item) => (
            <Row
              key={item.id}
              place={item.place.name}
              summary={item.locked ? `Sealed until ${item.opens_at?.slice(0, 4)}` : item.summary}
              badge={item.hidden ? 'Reported' : undefined}
              onPress={() => onOpenMine(item)}
            />
          ))
        )}
      </Section>
    </ScrollView>
  );
}

function Section({
  title,
  note,
  children,
}: {
  title: string;
  note: string;
  children: React.ReactNode;
}) {
  return (
    <View style={styles.section}>
      <Text style={styles.sectionTitle}>{title}</Text>
      {!!note && <Text style={styles.sectionNote}>{note}</Text>}
      {children}
    </View>
  );
}

function Row({
  place,
  summary,
  meta,
  badge,
  onPress,
}: {
  place: string;
  summary: string;
  meta?: string;
  badge?: string;
  onPress: () => void;
}) {
  return (
    <Pressable
      style={dim(styles.row)}
      onPress={onPress}
      accessibilityRole="button"
      accessibilityLabel={[place, meta].filter(Boolean).join(', ')}
    >
      <Text style={styles.place} numberOfLines={1}>
        {place}
      </Text>
      <Text style={styles.summary} numberOfLines={2}>
        {summary}
      </Text>
      {meta && <Text style={styles.when}>{meta}</Text>}
      {badge && <Text style={styles.badge}>{badge}</Text>}
    </Pressable>
  );
}

function Empty({ text }: { text: string }) {
  return (
    <View style={styles.empty}>
      <Padlock size={32} color={color.rule} />
      <Text style={styles.emptyText}>{text}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  screen: { flex: 1, backgroundColor: color.paper },
  body: { paddingBottom: 72 },
  title: { fontFamily: font.display, fontSize: 34, color: color.ink, paddingHorizontal: 24 },
  section: {
    marginTop: 30,
    gap: 12,
    paddingHorizontal: 24,
    borderTopWidth: 1,
    borderTopColor: color.rule,
    paddingTop: 18,
  },
  sectionTitle: { ...label },
  sectionNote: { fontFamily: font.prose, fontSize: 15, color: color.inkFaint },
  // A ruled entry, like a catalogue card. No nested card, no shadow - the
  // same row both sections used before the merge.
  row: { gap: 6, borderTopWidth: 1, borderTopColor: color.rule, paddingTop: 16 },
  place: { fontFamily: font.displaySemi, fontSize: 19, lineHeight: 26, color: color.ink },
  summary: { fontFamily: font.prose, fontSize: 16, lineHeight: 25, color: color.inkSoft },
  when: { ...label, fontSize: 10, marginTop: 2 },
  badge: { ...label, fontSize: 10, color: color.seal, marginTop: 2 },
  spinner: { marginTop: 12 },
  empty: { alignItems: 'flex-start', paddingVertical: 12, gap: 14 },
  emptyText: {
    fontFamily: font.prose,
    fontSize: 16,
    lineHeight: 26,
    color: color.inkFaint,
  },
});
