/** The journal: the one screen besides the map, opened from its corner.
 *  The streak on top, then three sections behind a segmented control:
 *
 * **Walks** - every walk this account accepted, newest first. A row opens in
 * place to the memories it earned; the row's "2 of 5" counts the rest. Cached (route.ts
 * `loadWalked`), so it reads on a train (F16).
 * **Filed** - what you filed. Always the server's, because it has to show two
 * things no local cache was told about: a memory still sealed and one enough
 * people reported. Pages at `MINE_PAGE_SIZE`.
 * **You** - Settings, passed in.
 *
 * There is no "Unlocked" list any more: every unlock is a walk's stop or
 * something you filed, and both are here already.
 */

import { type ReactNode, useCallback, useEffect, useState } from 'react';
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
  type Coordinates,
  type LocatedMemory,
  type WalkedRoute,
} from './api.ts';
import Padlock from './Padlock.tsx';
import { distance, walkDate } from './format.ts';
import { metersBetween } from './region.ts';
import { loadWalked, saveWalked } from './route.ts';
import { attention, loadSeen, saveSeen, type Seen } from './seen.ts';
import { color, dim, font, label } from './theme.ts';

type Props = {
  device: string | null;
  streak: number;
  /** Refetches each time this turns true: the journal stays mounted. */
  focused: boolean;
  /** Bumped by App.tsx after a save or a delete, which happen without
   *  `focused` re-firing. */
  refreshKey: number;
  onOpenMine: (memory: LocatedMemory) => void;
  /** An earned stop of a past walk. */
  onOpenStop: (memory: LocatedMemory) => void;
  onClose: () => void;
  /** Where the person is standing, or null - rows show no distance then. */
  position: Coordinates | null;
  you: ReactNode;
};

type Status = 'loading' | 'ready' | 'failed';
type Section = 'walks' | 'mine' | 'you';
type Item =
  | { kind: 'walk'; walk: WalkedRoute; index: number }
  | { kind: 'stop'; memory: LocatedMemory; walk: number }
  | { kind: 'mine'; memory: LocatedMemory };

export default function Memories({
  device,
  streak,
  focused,
  refreshKey,
  onOpenMine,
  onOpenStop,
  onClose,
  position,
  you,
}: Props) {
  const insets = useSafeAreaInsets();
  const [section, setSection] = useState<Section>('walks');
  const [mine, setMine] = useState<LocatedMemory[]>([]);
  const [mineTotal, setMineTotal] = useState(0);
  const [mineStatus, setMineStatus] = useState<Status>('loading');
  const [loadingMore, setLoadingMore] = useState(false);
  const [refreshing, setRefreshing] = useState(false);
  const [walks, setWalks] = useState<WalkedRoute[]>([]);
  const [walksStatus, setWalksStatus] = useState<Status>('loading');
  const [openWalk, setOpenWalk] = useState<number | null>(null);
  // The baseline as it was when the journal opened, so a row stays "new" for
  // the whole look; the look itself is what moves the baseline on.
  const [seen, setSeen] = useState<Seen | null>(null);
  const [looked, setLooked] = useState(false);

  useEffect(() => {
    if (!focused) return;
    setLooked(false);
    loadSeen().then(setSeen);
  }, [focused]);

  useEffect(() => {
    if (!seen || section !== 'mine' || mineStatus !== 'ready') return;
    saveSeen(seen, mine);
    setLooked(true);
  }, [seen, section, mineStatus, mine]);

  const isNew = (m: LocatedMemory) => !!seen && attention(m) > (seen[m.id] ?? 0);
  const anyNew = !looked && mine.some(isNew);

  useEffect(() => {
    loadWalked().then((cached) => {
      if (cached.length === 0) return;
      setWalks((current) => (current.length ? current : cached));
      setWalksStatus((current) => (current === 'loading' ? 'ready' : current));
    });
  }, []);

  // Always asked again: a walk finished on another phone of the same account
  // belongs here too. A failed refetch keeps the last list.
  useEffect(() => {
    if (!focused || !device) return;
    let cancelled = false;
    fetchWalked(device)
      .then((next) => {
        if (cancelled) return;
        setWalks(next);
        setWalksStatus('ready');
        saveWalked(next);
      })
      .catch(() => {
        if (!cancelled) setWalksStatus((current) => (current === 'ready' ? current : 'failed'));
      });
    return () => {
      cancelled = true;
    };
  }, [focused, device, refreshKey]);
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

  const mineNote =
    mineStatus !== 'ready' || mine.length === 0
      ? ''
      : mine.length === mineTotal
        ? `${mineTotal} ${mineTotal === 1 ? 'memory' : 'memories'} of yours`
        : `${mine.length} of your ${mineTotal}, so far`;

  const walksNote =
    walksStatus !== 'ready' || walks.length === 0
      ? ''
      : `${walks.length} ${walks.length === 1 ? 'walk' : 'walks'}`;

  const data: Item[] =
    section === 'mine'
      ? mine.map((memory) => ({ kind: 'mine', memory }))
      : walks.flatMap((walk, index): Item[] => [
          { kind: 'walk', walk, index },
          ...(openWalk === index
            ? walk.memories
                .filter((memory) => !memory.locked)
                .map((memory): Item => ({ kind: 'stop', memory, walk: index }))
            : []),
        ]);

  // Live, not stored: neither list carries a meaningful distance_meters.
  const distanceTo = (item: LocatedMemory) =>
    position ? distance(metersBetween(position.lat, position.lng, item.place.coordinates.lat, item.place.coordinates.lng)) : undefined;

  return (
    <View style={[styles.screen, { paddingTop: insets.top + 14 }]}>
      <View style={styles.top}>
        <Text style={styles.title}>Journal</Text>
        <Pressable style={dim()} onPress={onClose} accessibilityRole="button" accessibilityLabel="Close journal">
          <Text style={styles.close}>Close</Text>
        </Pressable>
      </View>
      {/* The only number in the app that goes up because you went outside. */}
      <View style={styles.streak} accessible accessibilityLabel={`${streak} day streak`}>
        <Text style={styles.streakValue}>{streak}</Text>
        <Text style={styles.streakLabel}>
          {streak === 0 ? 'Walk today to start a streak' : streak === 1 ? 'day' : 'days in a row'}
        </Text>
      </View>
      <Switcher section={section} onSelect={setSection} filedNew={anyNew} />

      {section === 'you' ? (
        <View style={styles.you}>{you}</View>
      ) : (
        <FlatList<Item>
          style={styles.list}
          contentContainerStyle={styles.body}
          data={data}
          // Two walks can share a date: one per device, and an account has several.
          keyExtractor={(item) =>
            item.kind === 'walk'
              ? `walk-${item.index}`
              : item.kind === 'stop'
                ? `walk-${item.walk}-${item.memory.id}`
                : String(item.memory.id)
          }
          renderItem={({ item }) =>
            item.kind === 'walk' ? (
              <Row
                place={walkDate(item.walk.route_date)}
                summary={item.walk.memories.map((memory) => memory.place.name).join(' · ')}
                meta={`${item.walk.earned} of ${item.walk.size} · ${distance(item.walk.budget_meters)}`}
                onPress={() => setOpenWalk((open) => (open === item.index ? null : item.index))}
              />
            ) : item.kind === 'stop' ? (
              <Row
                inset
                place={item.memory.place.name}
                summary={item.memory.summary}
                distance={distanceTo(item.memory)}
                onPress={() => onOpenStop(item.memory)}
              />
            ) : (
              <Row
                place={item.memory.place.name}
                summary={item.memory.locked ? `Sealed until ${item.memory.opens_at?.slice(0, 4)}` : item.memory.summary}
                distance={distanceTo(item.memory)}
                meta={reach(item.memory)}
                badge={item.memory.hidden ? 'Reported' : isNew(item.memory) ? 'New' : undefined}
                onPress={() => onOpenMine(item.memory)}
              />
            )
          }
          ListHeaderComponent={<Header note={section === 'mine' ? mineNote : walksNote} />}
          ListEmptyComponent={
            section === 'walks' ? (
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
              <Empty text="Nothing of yours yet. + Add leaves one where you stand." />
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
      )}
    </View>
  );
}

function Switcher({
  section,
  onSelect,
  filedNew,
}: {
  section: Section;
  onSelect: (section: Section) => void;
  /** Someone hearted or left a note on something you filed since you last looked. */
  filedNew: boolean;
}) {
  return (
    <View style={styles.switcher}>
      <SwitcherItem label="Walks" active={section === 'walks'} onPress={() => onSelect('walks')} />
      <SwitcherItem
        label={filedNew ? 'Memories ·' : 'Memories'}
        active={section === 'mine'}
        onPress={() => onSelect('mine')}
      />
      <SwitcherItem label="You" active={section === 'you'} onPress={() => onSelect('you')} />
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

/** "3 hearts · 1 note": what came back for something you filed. */
function reach(m: LocatedMemory): string | undefined {
  const parts = [
    m.heart_count > 0 && (m.heart_count === 1 ? '1 heart' : `${m.heart_count} hearts`),
    m.note_count > 0 && (m.note_count === 1 ? '1 note' : `${m.note_count} notes`),
  ].filter(Boolean);
  return parts.length ? parts.join(' · ') : undefined;
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
  inset,
  onPress,
}: {
  place: string;
  summary: string;
  distance?: string;
  meta?: string;
  badge?: string;
  /** A stop, under its walk. */
  inset?: boolean;
  onPress?: () => void;
}) {
  return (
    <Pressable
      style={dim([styles.row, inset && styles.inset])}
      onPress={onPress}
      disabled={!onPress}
      accessibilityRole="button"
      accessibilityLabel={[place, distance, meta, badge].filter(Boolean).join(', ')}
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
  list: { flex: 1 },
  body: { paddingBottom: 72 },
  top: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'baseline',
    paddingHorizontal: 24,
  },
  title: { fontFamily: font.display, fontSize: 34, color: color.ink },
  close: { ...label, color: color.ink },
  streak: { flexDirection: 'row', alignItems: 'baseline', gap: 10, marginTop: 18, paddingHorizontal: 24 },
  streakValue: { fontFamily: font.display, fontSize: 46, color: color.ink, letterSpacing: -1 },
  streakLabel: { ...label, fontSize: 10 },
  you: { flex: 1, marginTop: 12 },
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
  inset: { paddingLeft: 44 },
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
