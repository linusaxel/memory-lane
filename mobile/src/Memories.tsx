/** The "Memories" tab. Unlocking and filing are two different ways of ending
 *  up with a memory that is yours, and this is the one screen that shows
 *  both - as two subtabs behind a segmented control, not stacked on one
 *  scroll. They used to be stacked; at a handful of memories that read as
 *  "both, always," but at the hundreds this app is meant to hold, one
 *  section only pushed the other further down the screen. Replaces what
 *  were `Collection.tsx` (the old "Unlocked" tab) and the modal `Manage`
 *  opened from Settings.
 *
 * A memory you file still shows up under both - filing unlocks it too - it
 * now just takes a tab switch to see the second copy instead of a scroll.
 *
 * **Unlocked** is local-first and cannot fail - it is exactly what
 * `unlocked.ts` holds, so it works on a train. **My memories** always asks
 * the server, because it has to show two things the local cache was never
 * told about: a memory still sealed (shut, seal included) and one enough
 * people reported (flagged, not dropped).
 *
 * Both subtabs render through one `FlatList`: a row only costs a mount once
 * it scrolls into view, so this holds up past the hundreds a `ScrollView` +
 * `.map()` started struggling with. My memories also pages - the server caps
 * a single answer at `MINE_PAGE_SIZE`, so scrolling near the bottom asks for
 * the next page instead of silently stopping at the cap.
 */

import { useCallback, useEffect, useState } from 'react';
import {
  ActivityIndicator,
  FlatList,
  Pressable,
  RefreshControl,
  StyleSheet,
  Text,
  View,
} from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';

import {
  fetchMine,
  fetchWalked,
  MINE_PAGE_SIZE,
  type Coordinates,
  type LocatedMemory,
  type WalkedRoute,
} from './api.ts';
import Padlock from './Padlock.tsx';
import { distance, walkDate, when } from './format.ts';
import { metersBetween } from './region.ts';
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
  /** Shows that walk on the map, read-only. */
  onOpenWalk: (walk: WalkedRoute) => void;
  /** Where the person is standing, or null if they said no to location - the
   *  same source MemorySheet.tsx reads for its own distance. Rows show
   *  nothing in that slot rather than a stale figure when this is null. */
  position: Coordinates | null;
};

type MineStatus = 'loading' | 'ready' | 'failed';
type Section = 'unlocked' | 'mine' | 'walks';

export default function Memories({
  unlocked,
  unlockedReady,
  onOpenUnlocked,
  device,
  focused,
  refreshKey,
  onOpenMine,
  onOpenWalk,
  position,
}: Props) {
  const insets = useSafeAreaInsets();
  const [section, setSection] = useState<Section>('unlocked');
  const [mine, setMine] = useState<LocatedMemory[]>([]);
  const [mineTotal, setMineTotal] = useState(0);
  const [mineStatus, setMineStatus] = useState<MineStatus>('loading');
  const [loadingMore, setLoadingMore] = useState(false);
  const [refreshing, setRefreshing] = useState(false);
  const [walks, setWalks] = useState<WalkedRoute[]>([]);
  const [walksStatus, setWalksStatus] = useState<MineStatus>('loading');

  // Always the server's, like My memories: a walk finished on another phone
  // of the same account belongs here too. A failed refetch keeps the last list.
  useEffect(() => {
    if (!focused || !device || section !== 'walks') return;
    let cancelled = false;
    fetchWalked(device)
      .then((next) => {
        if (cancelled) return;
        setWalks(next);
        setWalksStatus('ready');
      })
      .catch(() => {
        if (!cancelled) setWalksStatus((current) => (current === 'ready' ? current : 'failed'));
      });
    return () => {
      cancelled = true;
    };
  }, [focused, device, section]);

  const load = useCallback(() => {
    if (!device) return Promise.resolve();
    return fetchMine(device).then((page) => {
      setMine(page.memories);
      setMineTotal(page.total);
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

  // The server hands back MINE_PAGE_SIZE rows at a time. Scrolling near the
  // bottom of what's loaded asks for the next page; mineTotal (from that same
  // response) says when to stop asking.
  const loadMore = useCallback(() => {
    if (!device || loadingMore || mineStatus !== 'ready' || mine.length >= mineTotal) return;
    setLoadingMore(true);
    fetchMine(device, mine.length)
      .then((page) => {
        setMine((current) => [...current, ...page.memories]);
        setMineTotal(page.total);
      })
      .catch(() => {
        // A failed page-two stays retryable: scrolling away and back triggers
        // onEndReached again, same as a failed pull-to-refresh stays retryable.
      })
      .finally(() => setLoadingMore(false));
  }, [device, loadingMore, mineStatus, mine.length, mineTotal]);

  const unlockedNote = !unlockedReady
    ? ''
    : unlocked.length === 0
      ? 'Nothing yet.'
      : `${unlocked.length} ${unlocked.length === 1 ? 'memory' : 'memories'} you walked to`;

  const mineNote =
    mineStatus !== 'ready' || mine.length === 0
      ? ''
      : mine.length === mineTotal
        ? `${mineTotal} ${mineTotal === 1 ? 'memory' : 'memories'} you filed`
        : `${mine.length} of ${mineTotal} you filed, so far`;

  const walksNote =
    walksStatus !== 'ready' || walks.length === 0
      ? ''
      : `${walks.length} ${walks.length === 1 ? 'walk' : 'walks'}`;

  const data: (LocatedMemory | WalkedRoute)[] =
    section === 'unlocked' ? unlocked : section === 'mine' ? mine : walks;

  // Live, not stored: neither /v1/unlocks nor /v1/me/memories ever carries a
  // meaningful distance_meters (both force it null server-side), so this is
  // computed the same way MemorySheet.tsx computes its own - from wherever the
  // device is right now, not from anything the row itself remembers.
  const distanceTo = (item: LocatedMemory) =>
    position ? distance(metersBetween(position.lat, position.lng, item.place.coordinates.lat, item.place.coordinates.lng)) : undefined;

  return (
    <FlatList<LocatedMemory | WalkedRoute>
      style={styles.screen}
      contentContainerStyle={[styles.body, { paddingTop: insets.top + 14 }]}
      data={data}
      // Two walks can share a date: one per device, and an account has several.
      keyExtractor={(item, index) => ('id' in item ? String(item.id) : `walk-${index}`)}
      renderItem={({ item }) =>
        !('id' in item) ? (
          <Row
            place={walkDate(item.route_date)}
            summary={item.memories.map((memory) => memory.place.name).join(' · ')}
            meta={`${item.earned} of ${item.size} · ${distance(item.budget_meters)}`}
            onPress={() => onOpenWalk(item)}
          />
        ) : section === 'unlocked' ? (
          <Row
            place={item.place.name}
            summary={item.summary}
            distance={distanceTo(item)}
            meta={when((item as UnlockedMemory).unlocked_at) ?? undefined}
            onPress={() => onOpenUnlocked(item as UnlockedMemory)}
          />
        ) : (
          <Row
            place={item.place.name}
            summary={item.locked ? `Sealed until ${item.opens_at?.slice(0, 4)}` : item.summary}
            distance={distanceTo(item)}
            badge={item.hidden ? 'Reported' : undefined}
            onPress={() => onOpenMine(item)}
          />
        )
      }
      ListHeaderComponent={
        <>
          <Text style={styles.title}>Memories</Text>
          <Switcher section={section} onSelect={setSection} />
          <Header
            note={section === 'unlocked' ? unlockedNote : section === 'mine' ? mineNote : walksNote}
          />
        </>
      }
      ListEmptyComponent={
        section === 'unlocked' ? (
          // No spinner: this is a disk read that resolves in a frame, and a
          // spinner that flashes is worse than a beat of nothing.
          !unlockedReady ? null : (
            <Empty text="Memories open when you stand where they happened. Whatever you open stays here." />
          )
        ) : section === 'walks' ? (
          walksStatus === 'loading' ? (
            <ActivityIndicator style={styles.spinner} color={color.inkFaint} />
          ) : walksStatus === 'failed' ? (
            <Empty text="Can't reach Memory Lane right now." />
          ) : (
            <Empty text="No walks yet. Every walk you accept stays here." />
          )
        ) : mineStatus === 'loading' ? (
          <ActivityIndicator style={styles.spinner} color={color.inkFaint} />
        ) : mineStatus === 'failed' ? (
          <Empty text="Can't reach Memory Lane right now." />
        ) : (
          <Empty text="Nothing filed yet." />
        )
      }
      ListFooterComponent={
        section === 'mine' && loadingMore ? (
          <ActivityIndicator style={styles.spinner} color={color.inkFaint} />
        ) : null
      }
      onEndReached={section === 'mine' ? loadMore : undefined}
      onEndReachedThreshold={0.5}
      refreshControl={
        section === 'mine' ? (
          <RefreshControl
            refreshing={refreshing}
            onRefresh={onRefresh}
            tintColor={color.inkFaint}
            colors={[color.inkFaint]}
            progressBackgroundColor={color.paper}
          />
        ) : undefined
      }
    />
  );
}

function Switcher({
  section,
  onSelect,
}: {
  section: Section;
  onSelect: (section: Section) => void;
}) {
  return (
    <View style={styles.switcher}>
      <SwitcherItem label="Unlocked" active={section === 'unlocked'} onPress={() => onSelect('unlocked')} />
      <SwitcherItem label="My memories" active={section === 'mine'} onPress={() => onSelect('mine')} />
      <SwitcherItem label="Walks" active={section === 'walks'} onPress={() => onSelect('walks')} />
    </View>
  );
}

function SwitcherItem({
  label,
  active,
  onPress,
}: {
  label: string;
  active: boolean;
  onPress: () => void;
}) {
  return (
    <Pressable
      style={dim(styles.switcherItem)}
      onPress={onPress}
      accessibilityRole="tab"
      accessibilityState={{ selected: active }}
    >
      <Text style={[styles.switcherLabel, active && styles.switcherLabelActive]}>{label}</Text>
      <View style={[styles.switcherRule, active && styles.switcherRuleActive]} />
    </Pressable>
  );
}

function Header({ note }: { note: string }) {
  return (
    <View style={[styles.header, !!note && styles.headerWithNote]}>
      {!!note && <Text style={styles.sectionNote}>{note}</Text>}
    </View>
  );
}

function Row({
  place,
  summary,
  distance,
  meta,
  badge,
  onPress,
}: {
  place: string;
  summary: string;
  distance?: string;
  meta?: string;
  badge?: string;
  onPress: () => void;
}) {
  return (
    <Pressable
      style={dim(styles.row)}
      onPress={onPress}
      accessibilityRole="button"
      accessibilityLabel={[place, distance, meta].filter(Boolean).join(', ')}
    >
      <Text style={styles.place} numberOfLines={1}>
        {place}
      </Text>
      <Text style={styles.summary} numberOfLines={2}>
        {summary}
      </Text>
      {(distance || meta) && (
        <View style={styles.metaRow}>
          {distance && <Text style={styles.when}>{distance}</Text>}
          {meta && <Text style={styles.when}>{meta}</Text>}
        </View>
      )}
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
  switcher: { flexDirection: 'row', marginTop: 22, paddingHorizontal: 24, gap: 24 },
  switcherItem: { gap: 8 },
  switcherLabel: { ...label, color: color.inkFaint },
  switcherLabelActive: { color: color.ink },
  switcherRule: { height: 2, backgroundColor: 'transparent' },
  switcherRuleActive: { backgroundColor: color.ink },
  header: {
    marginTop: 30,
    paddingHorizontal: 24,
    borderTopWidth: 1,
    borderTopColor: color.rule,
    paddingTop: 18,
  },
  headerWithNote: { marginBottom: 12 },
  sectionNote: { fontFamily: font.prose, fontSize: 15, color: color.inkFaint },
  // A ruled entry, like a catalogue card. No nested card, no shadow - the
  // same row both sections used before the merge.
  row: { gap: 6, paddingHorizontal: 24, borderTopWidth: 1, borderTopColor: color.rule, paddingTop: 16 },
  place: { fontFamily: font.displaySemi, fontSize: 19, lineHeight: 26, color: color.ink },
  summary: { fontFamily: font.prose, fontSize: 16, lineHeight: 25, color: color.inkSoft },
  metaRow: { flexDirection: 'row', gap: 10 },
  when: { ...label, fontSize: 10, marginTop: 2 },
  badge: { ...label, fontSize: 10, color: color.seal, marginTop: 2 },
  spinner: { marginTop: 12 },
  empty: { alignItems: 'flex-start', paddingHorizontal: 24, paddingVertical: 12, gap: 14 },
  emptyText: {
    fontFamily: font.prose,
    fontSize: 16,
    lineHeight: 26,
    color: color.inkFaint,
  },
});
