/** The journal: a pageSheet from the map's Journal button. It is you as
 *  well: your photo, name, numbers and level on top (tap them for Edit
 *  profile), the cog for Settings beside ×, then three sections of what you
 *  did behind a segmented control (docs/10-decisions.md, "The journal is
 *  you").
 *
 * **Walks** - every walk this account took that opened something, newest
 * first (a walk that opened nothing is deleted, docs/10). As a list, a row
 * opens in place to the memories it earned, strung on a rail in walking
 * order; as cards, each walk is drawn as its shape and a tap shows it on the
 * map. Cached
 * (route.ts `loadWalked`), so it reads on a train (F16).
 * **Unlocked** - everything earned, newest first, from App.tsx's
 * local copy (unlocked.ts), so it too reads on a train. Your own are left out.
 * **Mine** - what you filed. Always the server's, because it has to
 * show a thing no local cache was told about: one enough people reported.
 * Pages at `MINE_PAGE_SIZE`.
 */

import { useCallback, useEffect, useRef, useState } from 'react';
import {
  AccessibilityInfo,
  ActivityIndicator,
  Animated,
  FlatList,
  Pressable,
  RefreshControl,
  StyleSheet,
  Text,
  View,
  useWindowDimensions,
} from 'react-native';
import * as Haptics from 'expo-haptics';

import {
  fetchMine,
  fetchWalked,
  type Coordinates,
  type LocatedMemory,
  type Profile,
  type WalkedRoute,
} from './api.ts';
import Avatar from './Avatar.tsx';
import CloseButton from './CloseButton.tsx';
import DiamondRule from './DiamondRule.tsx';
import Glyph from './Glyph.tsx';
import { distance, walkDate, when } from './format.ts';
import { metersBetween } from './region.ts';
import { loadWalked, saveWalked } from './route.ts';
import WalkCard, { WalkShape, walkPath } from './WalkCard.tsx';
import { roll } from './countUp.ts';
import {
  attention,
  loadCounted,
  loadSeen,
  loadUnlocksShown,
  saveCounted,
  saveSeen,
  saveUnlocksShown,
  type Counted,
  type Seen,
} from './seen.ts';
import { color, dim, font, label, lift, screenTitle } from './theme.ts';
import { useReduceMotion } from './useBreath.ts';

type Props = {
  device: string | null;
  profile: Profile | null;
  /** As typed, ahead of the profile coming back. */
  displayName: string;
  /** Everything earned, your own included, as against `unlocked`. */
  unlockedCount: number;
  placeCount: number;
  onEditProfile: () => void;
  onSettings: () => void;
  /** A walk card tapped: show that walk on the map. */
  onOpenWalk: (walk: WalkedRoute) => void;
  /** Refetches each time this turns true: the journal stays mounted. */
  focused: boolean;
  /** Bumped by App.tsx after a save or a delete, which happen without
   *  `focused` re-firing. */
  refreshKey: number;
  /** Everything this device has earned, newest first, minus what you filed. */
  unlocked: LocatedMemory[];
  /** What this device hearted: Unlocked can show only those. */
  hearted: Set<number>;
  onOpenMine: (memory: LocatedMemory) => void;
  /** An earned stop of a past walk. */
  onOpenStop: (memory: LocatedMemory) => void;
  onClose: () => void;
  /** Where the person is standing, or null - rows show no distance then. */
  position: Coordinates | null;
};

type Status = 'loading' | 'ready' | 'failed';
type Section = 'walks' | 'unlocked' | 'mine';
type Item =
  | { kind: 'walk'; walk: WalkedRoute; index: number }
  | { kind: 'cards' }
  | { kind: 'stop'; memory: LocatedMemory; walk: number; stop: number }
  | { kind: 'unlocked'; memory: LocatedMemory }
  | { kind: 'mine'; memory: LocatedMemory };

export default function Memories({
  device,
  profile,
  displayName,
  unlockedCount,
  placeCount,
  onEditProfile,
  onSettings,
  onOpenWalk,
  focused,
  refreshKey,
  unlocked,
  hearted,
  onOpenMine,
  onOpenStop,
  onClose,
  position,
}: Props) {
  const [section, setSection] = useState<Section>('walks');
  const [mine, setMine] = useState<LocatedMemory[]>([]);
  const [mineTotal, setMineTotal] = useState(0);
  const [mineStatus, setMineStatus] = useState<Status>('loading');
  const [loadingMore, setLoadingMore] = useState(false);
  const [refreshing, setRefreshing] = useState(false);
  const [walks, setWalks] = useState<WalkedRoute[]>([]);
  const [walksStatus, setWalksStatus] = useState<Status>('loading');
  const [openWalk, setOpenWalk] = useState<number | null>(null);
  const [heartedOnly, setHeartedOnly] = useState(false);
  const [walkCards, setWalkCards] = useState(false);
  // Two to a row, between the sheet's 24pt margins and one 12pt gap.
  const card = (useWindowDimensions().width - 48 - 12) / 2;
  // The baseline as it was when the journal opened, so a row stays "new" for
  // the whole look; the look itself is what moves the baseline on.
  const [seen, setSeen] = useState<Seen | null>(null);
  const [looked, setLooked] = useState(false);
  // The same for what you unlocked: undefined while it loads, null before the
  // first look. A row pulses once a look, the first time it is drawn.
  const [unlocksShown, setUnlocksShown] = useState<Set<number> | null>();
  const pulsed = useRef(new Set<number>());
  // Header, sections, list: each slides in a beat after the one above it as
  // the sheet opens, so it arrives rather than appears.
  const enter = useRef([0, 1, 2].map(() => new Animated.Value(1))).current;
  // The header's numbers mid-roll; null shows the real ones.
  const [rolling, setRolling] = useState<Counted | null>(null);
  const counted = useRef<Counted>({ memories: 0, places: 0 });
  counted.current = { memories: unlockedCount, places: placeCount };

  useEffect(() => {
    if (!focused) return;
    setLooked(false);
    loadSeen().then(setSeen);
    setUnlocksShown(undefined);
    pulsed.current.clear();
    loadUnlocksShown().then(setUnlocksShown);
    const now = counted.current;
    const timers: ReturnType<typeof setTimeout>[] = [];
    let closed = false;
    Promise.all([loadCounted(), AccessibilityInfo.isReduceMotionEnabled()]).then(
      ([before, still]) => {
        saveCounted(now);
        if (!before || still || closed) return;
        const keys = ['memories', 'places'] as const;
        const tracks = keys.map((k) => roll(before[k], now[k]));
        const ticks = Math.max(...tracks.map((t) => t.length));
        if (!ticks) return;
        const at = (t: number) =>
          Object.fromEntries(
            keys.map((k, i) => [k, t < 0 ? Math.min(before[k], now[k]) : (tracks[i][t] ?? now[k])]),
          ) as Counted;
        setRolling(at(-1));
        // After the sheet lands and the header has arrived, ~600 ms of ticks.
        for (let t = 0; t < ticks; t++) {
          timers.push(
            setTimeout(
              () => {
                setRolling(at(t));
                Haptics.selectionAsync().catch(() => {});
              },
              350 + ((t + 1) * 600) / ticks,
            ),
          );
        }
        timers.push(setTimeout(() => setRolling(null), 350 + 650));
      },
    );
    return () => {
      closed = true;
      timers.forEach(clearTimeout);
      setRolling(null);
    };
  }, [focused]);

  useEffect(() => {
    if (!focused) return;
    AccessibilityInfo.isReduceMotionEnabled().then((still) => {
      if (still) return;
      enter.forEach((value) => value.setValue(0));
      Animated.stagger(
        50,
        enter.map((value) =>
          Animated.spring(value, { toValue: 1, tension: 80, friction: 10, useNativeDriver: true }),
        ),
      ).start();
    });
  }, [focused, enter]);

  const arrive = (index: number) => ({
    opacity: enter[index],
    transform: [
      { translateX: enter[index].interpolate({ inputRange: [0, 1], outputRange: [-24, 0] }) },
    ],
  });

  useEffect(() => {
    if (!seen || section !== 'mine' || mineStatus !== 'ready') return;
    saveSeen(seen, mine);
    setLooked(true);
  }, [seen, section, mineStatus, mine]);

  useEffect(() => {
    if (unlocksShown === undefined || section !== 'unlocked') return;
    saveUnlocksShown(unlocked.map((m) => m.id));
  }, [unlocksShown, section, unlocked]);

  const isNew = (m: LocatedMemory) => !!seen && attention(m) > (seen[m.id] ?? 0);
  const fresh = (m: LocatedMemory) => {
    if (!unlocksShown || unlocksShown.has(m.id) || pulsed.current.has(m.id)) return false;
    pulsed.current.add(m.id);
    return true;
  };
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

  const shown = heartedOnly ? unlocked.filter((memory) => hearted.has(memory.id)) : unlocked;
  const unlockedNote = !unlocked.length
    ? ''
    : heartedOnly
      ? `${shown.length} hearted`
      : `${unlocked.length} unlocked`;

  const data: Item[] =
    section === 'mine'
      ? mine.map((memory) => ({ kind: 'mine', memory }))
      : section === 'unlocked'
        ? shown.map((memory) => ({ kind: 'unlocked', memory }))
        : walkCards
          ? walks.length
            ? [{ kind: 'cards' }]
            : []
          : walks.flatMap((walk, index): Item[] => [
              { kind: 'walk', walk, index },
              ...(openWalk === index
                ? walk.memories
                    .map((memory, at): Item => ({
                      kind: 'stop',
                      memory,
                      walk: index,
                      stop: at + 1,
                    }))
                    .filter((item) => item.kind === 'stop' && !item.memory.locked)
                : []),
            ]);

  // Live, not stored: neither list carries a meaningful distance_meters.
  const distanceTo = (item: LocatedMemory) =>
    position
      ? distance(
          metersBetween(
            position.lat,
            position.lng,
            item.place.coordinates.lat,
            item.place.coordinates.lng,
          ),
        )
      : undefined;

  return (
    <View style={styles.screen}>
      <Animated.View style={[styles.top, arrive(0)]}>
        <Pressable
          style={dim(styles.who)}
          onPress={onEditProfile}
          accessibilityRole="button"
          accessibilityLabel="Edit profile"
        >
          <Avatar url={profile?.avatar_url} name={displayName} size={44} />
          <View style={styles.whoText}>
            <Text style={styles.title} numberOfLines={1}>
              {displayName.trim() || 'Journal'}
            </Text>
            <Text style={styles.stats} numberOfLines={1}>
              {rolling
                ? stats(rolling.memories, rolling.places, profile)
                : stats(unlockedCount, placeCount, profile)}
            </Text>
            <Level profile={profile} />
          </View>
        </Pressable>
        <Pressable
          style={dim(styles.cog)}
          hitSlop={8}
          onPress={onSettings}
          accessibilityRole="button"
          accessibilityLabel="Settings"
        >
          <Glyph name="gearshape" size={20} color={color.inkSoft} />
        </Pressable>
        <CloseButton onPress={onClose} label="Close journal" />
      </Animated.View>
      <Animated.View style={arrive(1)}>
        <Switcher
          section={section}
          onSelect={(next) => {
            if (next !== section) Haptics.selectionAsync().catch(() => {});
            setSection(next);
          }}
          filedNew={anyNew}
        />
      </Animated.View>

      <Animated.View style={[styles.list, arrive(2)]}>
        <FlatList<Item>
          contentContainerStyle={styles.body}
          data={data}
          // Two walks can share a date: one per device, and an account has several.
          keyExtractor={(item) =>
            item.kind === 'cards'
              ? 'cards'
              : item.kind === 'walk'
                ? `walk-${item.index}`
                : item.kind === 'stop'
                  ? `walk-${item.walk}-${item.memory.id}`
                  : String(item.memory.id)
          }
          renderItem={({ item }) =>
            item.kind === 'cards' ? (
              <View style={styles.shelf}>
                {walks.map((walk, i) => (
                  <WalkCard key={i} walk={walk} size={card} onPress={() => onOpenWalk(walk)} />
                ))}
              </View>
            ) : item.kind === 'walk' ? (
              <Row
                place={walkDate(item.walk.route_date)}
                summary={item.walk.memories.map((memory) => memory.place.name).join(' · ')}
                shape={walkPath(item.walk)}
                // What it opened, never what it missed: every walk here opened something.
                meta={`${item.walk.earned} ${item.walk.earned === 1 ? 'memory' : 'memories'} · ${distance(item.walk.budget_meters)}`}
                onPress={() => setOpenWalk((open) => (open === item.index ? null : item.index))}
              />
            ) : item.kind === 'stop' || item.kind === 'unlocked' ? (
              <Row
                stop={item.kind === 'stop' ? item.stop : undefined}
                place={item.memory.place.name}
                summary={item.memory.summary}
                distance={distanceTo(item.memory)}
                fresh={item.kind === 'unlocked' && fresh(item.memory)}
                onPress={() => onOpenStop(item.memory)}
              />
            ) : (
              <Row
                place={item.memory.place.name}
                summary={item.memory.summary}
                distance={distanceTo(item.memory)}
                meta={reach(item.memory)}
                badge={item.memory.hidden ? 'Reported' : isNew(item.memory) ? 'New' : undefined}
                onPress={() => onOpenMine(item.memory)}
              />
            )
          }
          // Between rows only, never above the first. A stop's rail is its own
          // delimiter, so nothing is drawn above one.
          // FlatList can render one with no trailingItem at all.
          ItemSeparatorComponent={({ trailingItem }: { trailingItem?: Item }) =>
            trailingItem?.kind === 'stop' ? null : <View style={styles.separator} />
          }
          ListHeaderComponent={
            <Header
              note={
                section === 'mine' ? mineNote : section === 'unlocked' ? unlockedNote : walksNote
              }
              filter={
                section === 'unlocked' && unlocked.length > 0
                  ? { on: heartedOnly, toggle: () => setHeartedOnly((on) => !on) }
                  : undefined
              }
              cards={
                section === 'walks' && walks.length > 0
                  ? { on: walkCards, toggle: () => setWalkCards((on) => !on) }
                  : undefined
              }
            />
          }
          ListEmptyComponent={
            section === 'unlocked' ? (
              <Empty
                text={
                  heartedOnly
                    ? 'Nothing hearted yet. Heart a memory and it waits here.'
                    : 'Nothing unlocked yet. Walk to a stop and it opens here.'
                }
              />
            ) : section === 'walks' ? (
              walksStatus === 'loading' ? (
                <ActivityIndicator style={styles.spinner} color={color.inkFaint} />
              ) : walksStatus === 'failed' ? (
                <Empty text="Can't reach Memory Lane right now." />
              ) : (
                <Empty text="No walks yet. Unlock a stop and your walk lands here." />
              )
            ) : mineStatus === 'loading' ? (
              <ActivityIndicator style={styles.spinner} color={color.inkFaint} />
            ) : mineStatus === 'failed' ? (
              <Empty text="Can't reach Memory Lane right now." />
            ) : (
              <Empty text="You haven't left a memory yet. Tap the pin up top to leave one right where you are." />
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
      </Animated.View>
    </View>
  );
}

/** Your numbers in one line under the name. A count that is still zero says
 *  nothing, bar the first. */
function stats(unlocked: number, places: number, profile: Profile | null): string {
  const parts = [`${unlocked} ${unlocked === 1 ? 'memory' : 'memories'}`];
  const streak = profile?.streak ?? 0;
  if (streak > 0) parts.unshift(`${streak}-day streak`);
  if (places > 0) parts.push(`${places} ${places === 1 ? 'place' : 'places'}`);
  const added = profile?.submitted ?? 0;
  if (added > 0) parts.push(`${added} added`);
  const hearts = profile?.hearts_received ?? 0;
  if (hearts > 0) parts.push(`${hearts} ${hearts === 1 ? 'heart' : 'hearts'}`);
  return parts.join(' · ');
}

/** Your level and how far into it, as a thin bar: finished walks fill it. */
function Level({ profile }: { profile: Profile | null }) {
  const level = profile?.level ?? 1;
  const into = (profile?.xp ?? 0) - (profile?.xp_level ?? 0);
  const span = (profile?.xp_next ?? 50) - (profile?.xp_level ?? 0);
  return (
    <View
      style={styles.level}
      accessible
      accessibilityLabel={`Level ${level}, ${Math.max(0, span - into)} XP to the next`}
    >
      <Text style={styles.levelText}>{`Level ${level}`}</Text>
      <View style={styles.bar}>
        <View style={[styles.fill, { width: `${Math.min(100, (into / span) * 100)}%` }]} />
      </View>
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
  /** Someone read, hearted or left a note on something you filed since you last looked. */
  filedNew: boolean;
}) {
  return (
    <View style={styles.switcher}>
      <SwitcherItem label="Walks" active={section === 'walks'} onPress={() => onSelect('walks')} />
      <SwitcherItem
        label="Unlocked"
        active={section === 'unlocked'}
        onPress={() => onSelect('unlocked')}
      />
      <SwitcherItem
        label={filedNew ? 'Mine ·' : 'Mine'}
        active={section === 'mine'}
        onPress={() => onSelect('mine')}
      />
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
      style={dim([styles.switcherItem, active && styles.switcherItemActive])}
      onPress={onPress}
      accessibilityRole="tab"
      accessibilityState={{ selected: active }}
    >
      <Text style={[styles.switcherLabel, active && styles.switcherLabelActive]}>{label}</Text>
    </Pressable>
  );
}

/** "Read on the spot by 14 walkers · 3 hearts · 1 note · last heart yesterday": what
 *  came back for something you filed. Never who: a heart is anonymous. */
function reach(m: LocatedMemory): string | undefined {
  const last = m.last_hearted_at ? when(Date.parse(m.last_hearted_at)) : null;
  const readers = m.opened_by ?? 0;
  const parts = [
    readers > 0 && `Read on the spot by ${readers} ${readers === 1 ? 'walker' : 'walkers'}`,
    m.heart_count > 0 && (m.heart_count === 1 ? '1 heart' : `${m.heart_count} hearts`),
    m.note_count > 0 && (m.note_count === 1 ? '1 note' : `${m.note_count} notes`),
    last && `last heart ${last}`,
  ].filter(Boolean);
  return parts.length ? parts.join(' · ') : undefined;
}

type Toggle = { on: boolean; toggle: () => void };

function Header({ note, filter, cards }: { note: string; filter?: Toggle; cards?: Toggle }) {
  return (
    <View style={styles.header}>
      <Text style={styles.sectionNote}>{note}</Text>
      {cards && (
        <Pressable
          style={dim(styles.filter)}
          hitSlop={8}
          onPress={cards.toggle}
          accessibilityRole="button"
          accessibilityLabel={cards.on ? 'Show as a list' : 'Show as cards'}
          testID="walks-view"
        >
          <Glyph
            name={cards.on ? 'list.bullet' : 'square.grid.2x2'}
            size={15}
            color={color.inkSoft}
          />
          <Text style={styles.filterText}>{cards.on ? 'List' : 'Cards'}</Text>
        </Pressable>
      )}
      {filter && (
        <Pressable
          style={dim(styles.filter)}
          hitSlop={8}
          onPress={filter.toggle}
          accessibilityRole="button"
          accessibilityLabel="Hearted only"
          accessibilityState={{ selected: filter.on }}
        >
          <Glyph
            name={filter.on ? 'heart.fill' : 'heart'}
            size={15}
            color={filter.on ? color.ink : color.inkFaint}
          />
          <Text style={[styles.filterText, filter.on && styles.filterTextOn]}>Hearted</Text>
        </Pressable>
      )}
    </View>
  );
}

function Row({
  place,
  summary,
  distance,
  meta,
  badge,
  stop,
  shape,
  fresh,
  onPress,
}: {
  place: string;
  summary: string;
  distance?: string;
  meta?: string;
  badge?: string;
  /** A stop, under its walk: its place in the walk, on the rail. */
  stop?: number;
  /** A walk: its shape, drawn small at the right. */
  shape?: Coordinates[];
  /** Unlocked since the last look: it scales in once, 0.8 → 1.08 → 1. */
  fresh?: boolean;
  onPress?: () => void;
}) {
  const reduceMotion = useReduceMotion();
  const pop = useRef(new Animated.Value(fresh ? 0.8 : 1)).current;
  // On mount only: the list draws a row the first time it scrolls into view.
  useEffect(() => {
    if (!fresh) return;
    Haptics.selectionAsync().catch(() => {});
    Animated.sequence([
      Animated.spring(pop, { toValue: 1.08, tension: 120, friction: 6, useNativeDriver: true }),
      Animated.spring(pop, { toValue: 1, tension: 80, friction: 8, useNativeDriver: true }),
    ]).start();
  }, []); // eslint-disable-line react-hooks/exhaustive-deps
  return (
    <Animated.View style={{ transform: [{ scale: reduceMotion ? 1 : pop }] }}>
      <Pressable
        style={dim([styles.row, stop !== undefined && styles.stop, shape && styles.withShape])}
        onPress={onPress}
        disabled={!onPress}
        accessibilityRole="button"
        accessibilityLabel={[stop && `Stop ${stop}`, place, distance, meta, badge]
          .filter(Boolean)
          .join(', ')}
      >
        {shape && (
          <View style={styles.shape}>
            <WalkShape path={shape} size={52} />
          </View>
        )}
        {stop !== undefined && (
          <>
            <View style={styles.rail} />
            <View style={styles.dot}>
              <Glyph name="checkmark" size={11} weight="bold" color={color.paper} />
            </View>
          </>
        )}
        <Text style={styles.place} numberOfLines={1}>
          {stop !== undefined && <Text style={styles.stopNumber}>{stop} </Text>}
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
    </Animated.View>
  );
}

function Empty({ text }: { text: string }) {
  return (
    <View style={styles.empty}>
      <DiamondRule />
      <Text style={styles.emptyText}>{text}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  screen: { flex: 1, paddingTop: 28, backgroundColor: color.paper },
  list: { flex: 1 },
  body: { paddingBottom: 72 },
  top: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    gap: 10,
    paddingHorizontal: 24,
  },
  who: { flex: 1, flexDirection: 'row', alignItems: 'center', gap: 12 },
  whoText: { flex: 1 },
  title: { ...screenTitle, fontSize: 28, lineHeight: 34 },
  stats: { ...label, fontSize: 12, marginTop: 2 },
  level: { flexDirection: 'row', alignItems: 'center', gap: 8, marginTop: 6 },
  levelText: { ...font.uiBold, fontSize: 12, color: color.plum },
  bar: { flex: 1, height: 4, borderRadius: 2, backgroundColor: color.track },
  fill: { height: 4, borderRadius: 2, backgroundColor: color.plum },
  cog: { padding: 6 },
  shelf: { flexDirection: 'row', flexWrap: 'wrap', gap: 12, paddingHorizontal: 24, paddingTop: 16 },
  // A capsule with the open tab raised in it, like the planner's Mode row.
  switcher: {
    flexDirection: 'row',
    marginTop: 22,
    marginHorizontal: 24,
    padding: 4,
    borderRadius: 999,
    backgroundColor: color.quiet,
    borderWidth: 1,
    borderColor: color.quietEdge,
  },
  switcherItem: {
    flex: 1,
    alignItems: 'center',
    paddingVertical: 10,
    borderRadius: 999,
    borderWidth: 1,
    borderColor: 'transparent',
  },
  switcherItemActive: {
    backgroundColor: color.paperRaised,
    borderColor: color.goldLine,
    ...lift,
    shadowOpacity: 0.08,
  },
  switcherLabel: { ...label, color: color.inkSoft },
  switcherLabelActive: { ...font.uiBold, color: color.ink },
  // Space, not a rule, sets the list off from the switcher: a rule here and
  // another between rows read as a double line.
  header: {
    marginTop: 32,
    paddingHorizontal: 24,
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  filter: { flexDirection: 'row', alignItems: 'center', gap: 6 },
  filterText: { ...label, color: color.inkFaint },
  filterTextOn: { color: color.ink },
  sectionNote: { ...font.prose, fontSize: 15, color: color.inkFaint },
  // A ruled entry, like a catalogue card. No nested card, no shadow. The rule
  // sits between rows (`separator`), inset to the text like iOS's own lists,
  // and the padding is even so it belongs to neither row.
  row: { gap: 6, paddingHorizontal: 24, paddingVertical: 18 },
  withShape: { paddingRight: 24 + 52 + 12 },
  shape: { position: 'absolute', right: 24, top: 18 },
  separator: {
    height: StyleSheet.hairlineWidth,
    marginHorizontal: 24,
    backgroundColor: color.rule,
  },
  // A walk's stops hang off one rail, numbered like the map's route badges,
  // instead of each being ruled off as its own entry. Rows sit edge to edge,
  // so the rail runs unbroken from the first stop to the last.
  stop: { paddingLeft: 60, paddingTop: 16, paddingBottom: 10 },
  rail: {
    position: 'absolute',
    left: 33,
    top: 0,
    bottom: 0,
    width: 1,
    backgroundColor: color.goldLine,
  },
  // Every stop here was opened: the walk card's done circle.
  dot: {
    position: 'absolute',
    left: 23,
    top: 19,
    width: 22,
    height: 22,
    borderRadius: 11,
    backgroundColor: color.gold,
    alignItems: 'center',
    justifyContent: 'center',
  },
  stopNumber: { color: color.gold },
  place: { ...font.title, fontSize: 20, lineHeight: 26, color: color.ink },
  summary: { ...font.prose, fontSize: 16, lineHeight: 25, color: color.inkSoft },
  metaRow: { flexDirection: 'row', gap: 10 },
  when: { ...label, fontSize: 12, marginTop: 2 },
  badge: { ...label, fontSize: 12, color: color.seal, marginTop: 2 },
  spinner: { marginTop: 12 },
  empty: { paddingHorizontal: 24, paddingVertical: 12, gap: 16 },
  emptyText: {
    ...font.storyItalic,
    fontSize: 18,
    lineHeight: 26,
    color: color.inkSoft,
    textAlign: 'center',
  },
});
