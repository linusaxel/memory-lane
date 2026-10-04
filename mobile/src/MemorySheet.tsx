import { useEffect, useRef, useState } from 'react';
import {
  ActionSheetIOS,
  Alert,
  Animated,
  Easing,
  Modal,
  Platform,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  View,
  useWindowDimensions,
  type NativeScrollEvent,
  type NativeSyntheticEvent,
} from 'react-native';

import * as Haptics from 'expo-haptics';

import CloseButton from './CloseButton.tsx';
import type { Coordinates, LocatedMemory, ReportReason } from './api.ts';
import MemoryMedia from './MemoryMedia.tsx';
import Approach from './Approach.tsx';
import Notes from './Notes.tsx';
import SourceLine from './SourceLine.tsx';
import { openLink } from './link.ts';
import Avatar from './Avatar.tsx';
import Flourish from './Flourish.tsx';
import Glyph from './Glyph.tsx';
import { FALLBACK_RADIUS_M } from './reach.ts';
import { distance, duration, happened, sourceAction } from './format.ts';
import { photoIds } from './story.ts';
import StoryBody from './StoryBody.tsx';
import { useReduceMotion } from './useBreath.ts';
import { metersBetween } from './region.ts';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import {
  color,
  dim,
  figure,
  figureSmall,
  floating as floatingCard,
  font,
  label,
  lift,
  radius as corner,
  story,
} from './theme.ts';

type Props = {
  /** Everything at the tapped point. One marker can hide a dozen memories. */
  memories: LocatedMemory[];
  index: number;
  onIndex: (next: number) => void;
  onClose: () => void;
  /** Where the person is standing, or null if they said no to location. */
  position: Coordinates | null;
  /** The memory a hold on the map just opened: its story arrives animated. */
  revealId?: number | null;
  /** The sheet is up: a hold's dive hands over to it here. */
  onShow?: () => void;
  /** Present only for a memory this account filed. */
  onEdit?: (memory: LocatedMemory) => void;
  /** Say this one mattered. Absent while locked - there is nothing to react
   *  to yet, and the server never sees a heart request the client didn't ask
   *  for. */
  onHeart?: (memory: LocatedMemory) => void;
  /** This account hearted it: the glyph is filled, and a tap takes it back. */
  hearted?: boolean;
  /** Over the map, in any stage: a card. Over the journal: a page. */
  compact?: boolean;
  /** Absent only for your own: reporting yourself is not a real control.
   *  A retold story is reportable too (DSA Arts 16/17). */
  onReport?: (memory: LocatedMemory, reason: ReportReason) => void;
  /** Already reported from this device, so the control says so instead of
   *  offering a second press that does nothing. */
  reported?: boolean;
  /** Only for what a person filed: blocking hides everything its author
   *  posted, on every phone on this account. */
  onBlock?: (memory: LocatedMemory) => void;
};

/** What a report says. The first three hide it at once (docs/10, "A legal
 *  report hides at once"). */
const REASONS: { reason: ReportReason; label: string }[] = [
  { reason: 'privacy', label: 'It shares private information' },
  { reason: 'defamation', label: "It's false or defamatory" },
  { reason: 'copyright', label: 'It uses my work without permission' },
  { reason: 'other', label: "It shouldn't be here for another reason" },
];

function blockee(memory: LocatedMemory) {
  return memory.author?.name === 'Anonymous' ? 'this person' : memory.author?.name;
}

/** Edit, report and block, behind ⋯ the way a post does it: App Store 1.2
 *  wants report and block reachable, not on show, and an owner's edit is
 *  there in every app that has one. Report and block go on in the sheet,
 *  not a dialog: this app raises none of its own. */
function moreActions(
  memory: LocatedMemory,
  reported: boolean | undefined,
  ask: (what: 'report' | 'block') => void,
  canReport: boolean,
  canBlock: boolean,
  onEdit?: (memory: LocatedMemory) => void,
) {
  const who = blockee(memory);
  const actions = [
    onEdit ? { label: 'Edit this memory', run: () => onEdit(memory) } : null,
    reported || !canReport ? null : { label: 'Report this memory', run: () => ask('report') },
    canBlock && who ? { label: `Block ${who}`, destructive: true, run: () => ask('block') } : null,
  ].filter((a) => a !== null);
  if (actions.length === 0) return;
  if (Platform.OS === 'ios') {
    ActionSheetIOS.showActionSheetWithOptions(
      {
        options: [...actions.map((a) => a.label), 'Cancel'],
        cancelButtonIndex: actions.length,
        destructiveButtonIndex: actions.findIndex((a) => 'destructive' in a),
      },
      (i) => actions[i]?.run(),
    );
  } else {
    Alert.alert('', undefined, [
      ...actions.map((a) => ({ text: a.label, onPress: a.run })),
      { text: 'Cancel', style: 'cancel' as const },
    ]);
  }
}

function formatDistance(meters: number | null): string | null {
  return meters == null ? null : distance(meters, { suffix: 'away' });
}

/** An open memory's card, as a share of the screen's height. */
export const TALL = 0.92;

const RISE_MS = 360;
const BEAT_MS = 90;
const REVEAL_MS = RISE_MS + 3 * BEAT_MS;

function formatTimestamp(seconds: number): string {
  return duration(seconds, { hours: true });
}

export default function MemorySheet({
  memories,
  index,
  onIndex,
  onClose,
  position,
  revealId,
  onShow,
  onHeart,
  hearted,
  onEdit,
  compact = false,
  onReport,
  reported,
  onBlock,
}: Props) {
  const memory = memories[index] ?? null;
  const insets = useSafeAreaInsets();
  // Over the map, before or on a walk: a card sized to what it holds, not a
  // page (docs/10, "An open memory is a card too").
  const many = memories.length > 1;
  // openLink rejects when nothing can show the link - no browser, a
  // locked-down device. The source link says so instead of appearing to do
  // nothing.
  const [linkFailed, setLinkFailed] = useState<string | null>(null);
  // Report or block, asked in the sheet. Another memory asks afresh.
  const [asking, setAsking] = useState<'report' | 'block' | null>(null);
  useEffect(() => setAsking(null), [memory?.id]);

  const open = (url: string, whenNothingOpens: string) => {
    setLinkFailed(null);
    openLink(url).catch(() => setLinkFailed(whenNothingOpens));
  };

  // distance_meters is measured from the map centre, which is not where the
  // person is. Only their own distance decides whether the gate can open.
  const fromHere =
    memory && position
      ? metersBetween(
          position.lat,
          position.lng,
          memory.place.coordinates.lat,
          memory.place.coordinates.lng,
        )
      : null;
  const radius = memory?.unlock_radius_meters ?? FALLBACK_RADIUS_M;
  const withinReach = fromHere != null && fromHere <= radius;
  const locked = !!memory?.locked;
  // A locked memory over the map. Standing on it, the ring is on the map.
  const peeking = locked && compact;
  const peekNote = withinReach
    ? "You're right here. Hold the ring on the map to open it."
    : fromHere == null
      ? 'Turn on location to see how far.'
      : `Get within ${Math.round(radius)} m to unlock it.`;
  const hasMore = !locked && !!(onReport || onEdit);
  const hearts = memory?.heart_count ?? 0;
  const heartsText = hearts === 1 ? '1 heart' : `${hearts} hearts`;
  // Your own memory: you see that it mattered, you cannot say so (api/write.py
  // heart_memory refuses it too). onEdit is only passed for your own.
  // The glyph first and the count after it, so the glyph never moves when the
  // count changes. It heads the notes: what walkers gave back, under the
  // second flourish (docs/10, "The heart heads the notes").
  const countIn = useRef(new Animated.Value(1)).current;
  const still = useReduceMotion();
  const shownHearts = useRef(hearts);
  useEffect(() => {
    if (shownHearts.current === hearts) return;
    shownHearts.current = hearts;
    if (still) return;
    countIn.setValue(0);
    Animated.timing(countIn, { toValue: 1, duration: 250, useNativeDriver: true }).start();
  }, [hearts, still, countIn]);
  const heartCount = (
    <Animated.Text
      style={[
        styles.heartText,
        {
          opacity: hearts > 0 ? countIn : 0,
          transform: [
            { translateY: countIn.interpolate({ inputRange: [0, 1], outputRange: [4, 0] }) },
          ],
        },
      ]}
    >
      {hearts}
    </Animated.Text>
  );
  const heart =
    !memory || locked || !onHeart ? null : onEdit ? (
      <View
        style={styles.heart}
        accessible
        accessibilityLabel="Hearts"
        accessibilityValue={{ text: heartsText }}
      >
        <Glyph name="heart.fill" size={17} color={color.inkSoft} />
        {heartCount}
      </View>
    ) : (
      <Pressable
        style={dim(styles.heart)}
        hitSlop={8}
        accessibilityRole="button"
        accessibilityLabel="Heart"
        accessibilityState={{ selected: !!hearted }}
        accessibilityValue={hearts > 0 ? { text: heartsText } : undefined}
        onPress={() => onHeart(memory)}
      >
        <Glyph
          name={hearted ? 'heart.fill' : 'heart'}
          size={17}
          color={color.inkSoft}
          bounce={hearted}
        />
        {heartCount}
      </Pressable>
    );

  // The reveal is the payoff. Swapping the text in place would throw away the
  // only moment the product has - so the content arrives, once, as the sheet
  // opens on what the hold unlocked: the year, the lede, the rest, their
  // words, then what stands here now, each a beat after the last.
  const reveal = useRef(new Animated.Value(1)).current;

  // Swipe the card down to close it, as a page sheet does. The card sits at
  // the foot of a transparent scroll view, so pulling it down is the native
  // rubber band - UIKit's own gesture, which a JS pan responder could not get
  // the moves of here - and letting go far enough down closes it.
  const pulled = (e: NativeSyntheticEvent<NativeScrollEvent>) => {
    if (e.nativeEvent.contentOffset.y < -70) onClose();
  };
  const { height: screenHeight } = useWindowDimensions();

  // Once per hold: paging away and back is rereading, not arriving.
  const arrived = useRef<number | null>(null);
  // The hold's dive has already grown paper to this card's frame (IrisGrow),
  // so it appears in place instead of sliding up.
  const arriving =
    !!memory && !memory.locked && memory.id === revealId && arrived.current !== revealId;

  useEffect(() => {
    if (!memory || memory.locked || memory.id !== revealId || arrived.current === revealId) return;
    arrived.current = revealId;
    // Quiet by default, loud only here: an epic one arrives with its own haptic.
    if (memory.epic)
      Haptics.notificationAsync(Haptics.NotificationFeedbackType.Success).catch(() => {});

    reveal.setValue(0);
    Animated.timing(reveal, {
      toValue: 1,
      duration: REVEAL_MS,
      easing: Easing.out(Easing.cubic),
      useNativeDriver: true,
    }).start();
  }, [memory, revealId, reveal]);

  /** Knowing a photograph or a note is waiting is the pull. Handing it over is the
   *  leak, so only the count travels. */
  const waitingParts = memory
    ? [
        memory.media_count === 1
          ? '1 attachment'
          : memory.media_count > 1 && `${memory.media_count} attachments`,
        memory.note_count === 1 ? '1 note' : memory.note_count > 1 && `${memory.note_count} notes`,
      ].filter(Boolean)
    : [];
  const waiting =
    waitingParts.length > 0 ? (
      <Text style={styles.waiting}>{waitingParts.join(' · ')} waiting</Text>
    ) : null;

  /** The kth beat of the reveal: it rises and fades in RISE_MS, BEAT_MS after
   *  the one before. With Reduce Motion on, it only fades. */
  const rise = (k: number) => {
    const inputRange = [(k * BEAT_MS) / REVEAL_MS, (k * BEAT_MS + RISE_MS) / REVEAL_MS];
    return {
      opacity: reveal.interpolate({ inputRange, outputRange: [0, 1], extrapolate: 'clamp' }),
      transform: [
        {
          translateY: reveal.interpolate({
            inputRange,
            outputRange: [still ? 0 : 12, 0],
            extrapolate: 'clamp',
          }),
        },
      ],
    };
  };

  const placed = photoIds(memory?.summary ?? '');
  const when = happened(memory?.happened_at, memory?.happened_precision);
  const started = memory?.content?.timestamp_start ?? null;
  // When it happened, not when it was posted: its own line under the title,
  // never in the byline. No distance: an open story is one you stand on
  // (docs/10, "The date is the story's, the byline the source's").
  const dateLine = [
    when && [when.within, when.year].filter(Boolean).join(' '),
    memory?.anniversary && 'on this day',
  ]
    .filter(Boolean)
    .join(' · ');
  const quoteBy = [memory?.quote_by, started != null && `at ${formatTimestamp(started)}`]
    .filter(Boolean)
    .join(', ');

  return (
    <Modal
      visible={!!memory}
      animationType={arriving ? (still ? 'fade' : 'none') : 'slide'}
      onShow={onShow}
      presentationStyle={compact ? 'overFullScreen' : 'pageSheet'}
      transparent={compact}
      // Required, or the Android back button does nothing.
      onRequestClose={onClose}
    >
      {memory && (
        <ScrollView
          style={styles.fill}
          // The page sheet is held to the screen, or a long story pushes the
          // pinned credit and heart off it with no scroll to get them back.
          contentContainerStyle={compact ? styles.over : styles.page}
          // Close answers the first tap while a note's keyboard is up.
          keyboardShouldPersistTaps="handled"
          scrollEnabled={compact}
          alwaysBounceVertical={compact}
          showsVerticalScrollIndicator={false}
          onScrollEndDrag={pulled}
        >
          {compact && (
            // Not "Close": that is the X, and one label on two controls reads
            // twice to VoiceOver and sends a flow's tap to the status bar.
            <Pressable style={styles.fill} accessibilityLabel="Dismiss" onPress={onClose} />
          )}
          <View
            style={[
              styles.sheet,
              compact &&
                (peeking
                  ? [
                      styles.card,
                      styles.floating,
                      { maxHeight: screenHeight * 0.6, marginBottom: 16 + insets.bottom },
                    ]
                  : [styles.card, styles.tall, { height: screenHeight * TALL }]),
            ]}
          >
            <View style={styles.grabberRow}>
              <View style={styles.grabber} />
            </View>
            <CloseButton place={styles.close} onPress={onClose} />
            {hasMore && (
              <CloseButton
                place={styles.more}
                icon="ellipsis"
                label="More"
                onPress={() =>
                  moreActions(memory, reported, setAsking, !!onReport, !!onBlock, onEdit)
                }
              />
            )}

            <View style={styles.heading}>
              <Text style={[styles.place, hasMore && styles.placeBesideMore]}>
                {memory.place.name}
              </Text>
              {peeking && (memory.author || memory.source_name) && (
                <View style={styles.peekFrom}>
                  {memory.author &&
                    (memory.author.avatar_url ? (
                      <Avatar url={memory.author.avatar_url} name={memory.author.name} size={16} />
                    ) : (
                      <Glyph name="person" size={12} color={color.inkFaint} />
                    ))}
                  <Text style={styles.meta} numberOfLines={1}>
                    {memory.author ? `Left by ${memory.author.name}` : `From ${memory.source_name}`}
                  </Text>
                </View>
              )}
              {/* "On this day" has no accent - the seal means openable and
                  nothing else gets it. */}
              {!locked && dateLine !== '' && <Text style={styles.date}>{dateLine}</Text>}
              {/* Who told it, under the name: in every screenshot, and the
                  first thing seen with an AI-written story, which is where
                  the AI Act wants it said (UI.md rule 11). */}
              {!locked &&
                (memory.author ? (
                  <View style={[styles.byline, styles.bylineRow]}>
                    <Avatar url={memory.author.avatar_url} name={memory.author.name} size={20} />
                    <Text style={styles.bylineText} numberOfLines={2}>
                      Left by <Text style={styles.bylineName}>{memory.author.name}</Text>
                    </Text>
                  </View>
                ) : memory.content?.source ? (
                  <View style={styles.byline}>
                    <SourceLine
                      source={memory.content.source}
                      url={memory.content.url}
                      spoken={sourceAction(memory.content).spoken}
                    />
                  </View>
                ) : memory.content?.title ? (
                  <Pressable
                    style={dim(styles.byline)}
                    accessibilityRole="link"
                    accessibilityLabel={sourceAction(memory.content).spoken}
                    onPress={() => open(memory.content!.url, "Couldn't open that link.")}
                  >
                    <Text style={styles.meta} numberOfLines={2}>
                      Retold by AI from {memory.content.title}
                      <Text style={styles.out}> ↗</Text>
                    </Text>
                  </Pressable>
                ) : null)}
              {linkFailed && <Text style={[styles.meta, styles.byline]}>{linkFailed}</Text>}
              {!locked && (
                <View style={styles.flourish}>
                  <Flourish />
                </View>
              )}
              {/* What it is about, as the #words the open story sets them in
                  (UI.md, "Tags are the #words"): under the name they belong
                  to, not in the apparatus line. Not tappable. */}
              {peeking && memory.tags.length > 0 && (
                <View style={styles.tags}>
                  {memory.tags.map((tag) => (
                    <View key={tag} style={styles.tag}>
                      <Text style={styles.tagText}>#{tag}</Text>
                    </View>
                  ))}
                </View>
              )}
              {locked && memory.anniversary && (
                <Text style={[styles.meta, styles.byline]}>on this day</Text>
              )}
            </View>

            {asking && (
              <View style={styles.ask} testID="ask">
                <Text style={styles.askTitle} accessibilityRole="header">
                  {asking === 'report' ? 'Why should it come down?' : `Block ${blockee(memory)}?`}
                </Text>
                {asking === 'block' && (
                  <Text style={styles.meta}>You will not see anything they post.</Text>
                )}
                {(asking === 'report'
                  ? REASONS.map(({ reason, label: text }) => ({
                      text,
                      run: () => onReport?.(memory, reason),
                    }))
                  : [{ text: 'Block', run: () => onBlock?.(memory) }]
                ).map(({ text, run }) => (
                  <Pressable
                    key={text}
                    style={dim(styles.askChoice)}
                    accessibilityRole="button"
                    onPress={() => {
                      setAsking(null);
                      run();
                    }}
                  >
                    <Text style={[styles.askText, asking === 'block' && styles.askDestructive]}>
                      {text}
                    </Text>
                  </Pressable>
                ))}
                <Pressable
                  style={dim(styles.askChoice)}
                  accessibilityRole="button"
                  onPress={() => setAsking(null)}
                >
                  <Text style={styles.askCancel}>Cancel</Text>
                </Pressable>
              </View>
            )}

            {/* Two different screens, not one screen with the middle deleted. A
                locked memory has nothing to scroll, so it gets a centred
                composition; an open one is a story and gets the reading column. */}
            {peeking ? (
              <View style={styles.peek}>
                {/* The lock is the ring you will hold, drawn as how far there is
                    still to go: a condition to meet, not a badge. */}
                <View style={styles.approach}>
                  <Approach meters={fromHere} radius={radius} locket={memory.locket} />
                  <View style={styles.approachText}>
                    {fromHere != null && (
                      <Text style={styles.peekFigure}>{distance(fromHere)}</Text>
                    )}
                    {peekNote && <Text style={styles.peekNote}>{peekNote}</Text>}
                    {(memory.year != null || hearts > 0) && (
                      <Text style={styles.meta}>
                        {[memory.year, hearts > 0 && heartsText].filter(Boolean).join(' · ')}
                      </Text>
                    )}
                    {waiting}
                  </View>
                </View>
              </View>
            ) : locked ? (
              <View style={styles.gate}>
                {/* In reach, the ring is on the map and this is not open. */}
                <Approach meters={fromHere} radius={radius} locket={memory.locket} />
                <Text style={styles.gateFigure}>
                  {position == null ? '—' : formatDistance(fromHere)?.replace(' away', '')}
                </Text>
                <Text style={styles.gateNote}>
                  {position == null
                    ? 'Turn on location to unlock it when you get here.'
                    : `Get within ${Math.round(radius)} m to unlock it.`}
                </Text>
                {waiting}
              </View>
            ) : (
              <>
                {/* A note's send link sits under its field: "handled" lets the
                    first tap on it send rather than only drop the keyboard, and
                    the insets let it scroll clear of the keyboard. */}
                <ScrollView
                  contentContainerStyle={[styles.body, { paddingBottom: 24 + insets.bottom }]}
                  keyboardShouldPersistTaps="handled"
                  automaticallyAdjustKeyboardInsets
                >
                  {/* The summary carries the sheet when nothing is attached, which
                      is every extracted memory; a submission usually brings a
                      photograph and the weight shifts to it. */}
                  {/* docs/10, "The open story has a shape": when, the peak
                      first, their words, and what you can see now last. */}
                  {/* One sentence is not a lede, it is the story. */}
                  {memory.epic && (
                    <Animated.View style={[rise(0), styles.epic]} testID="epic">
                      <Glyph
                        name="sparkles"
                        size={18}
                        color={color.gold}
                        bounce={memory.id === revealId}
                      />
                      <Text style={styles.epicText}>Epic</Text>
                    </Animated.View>
                  )}
                  {/* The #words are the tags, in the semibold, and a linked
                      name is underlined (StoryBody). */}
                  <StoryBody
                    summary={memory.summary}
                    media={memory.media}
                    links={memory.links}
                    onLink={(url) => open(url, "Couldn't open that link.")}
                    part={(i, node) => (
                      <Animated.View key={i} style={rise(Math.min(i, 1))}>
                        {node}
                      </Animated.View>
                    )}
                  />
                  {memory.quote && (
                    <Animated.View style={rise(2)}>
                      {/* Copied from the source and checked against it
                          (pipeline/extract.py, grounded), never written. A tap
                          goes to where it was said, like the watch button. */}
                      {/* A callout, as GitHub's > [!NOTE] is: the bar, then a
                          title row that says what the box is. No quote marks
                          in a block quote (Butterick). */}
                      <Pressable
                        style={dim([styles.callout, styles.quote])}
                        disabled={!memory.content}
                        accessibilityRole={memory.content ? 'link' : 'text'}
                        onPress={() => open(memory.content!.url, "Couldn't open that link.")}
                      >
                        <View style={styles.calloutTitle}>
                          <Glyph name="quote.opening" size={13} color={color.gold} />
                          <Text style={styles.meta}>{quoteBy || 'In their words'}</Text>
                        </View>
                        <Text style={styles.summary}>{memory.quote}</Text>
                      </Pressable>
                    </Animated.View>
                  )}
                  <Animated.View style={[rise(3), styles.after]}>
                    {/* The same callout, in grey: gold is the source's own voice. */}
                    {memory.contrast_note && (
                      <View style={[styles.callout, styles.calloutQuiet]}>
                        <View style={styles.calloutTitle}>
                          <Glyph name="clock.arrow.circlepath" size={13} color={color.inkFaint} />
                          <Text style={styles.meta}>Then and now</Text>
                        </View>
                        <Text style={styles.summary}>{memory.contrast_note}</Text>
                      </View>
                    )}

                    <MemoryMedia media={memory.media.filter((m) => !placed.includes(m.id))} />

                    <Flourish />
                    <Notes memoryId={memory.id} isAuthor={!!onEdit} heart={heart} />
                  </Animated.View>
                </ScrollView>
              </>
            )}

            {/* Over the story, only what is not the story: the way to the
                others under this pin. */}
            {many && (
              <View
                style={[
                  styles.actions,
                  compact && !peeking && { paddingBottom: 20 + insets.bottom },
                ]}
              >
                {/* Without this, every memory but the first at a stacked point is
                    unreachable - and 60% of this corpus sits on a shared point. */}
                {many && (
                  <View style={styles.pager}>
                    <Pressable
                      accessibilityRole="button"
                      accessibilityLabel="Previous memory here"
                      style={dim([styles.step, index === 0 && styles.stepOff])}
                      disabled={index === 0}
                      onPress={() => onIndex(index - 1)}
                    >
                      <Glyph
                        name="chevron.left"
                        size={17}
                        weight="semibold"
                        color={color.inkSoft}
                      />
                    </Pressable>
                    <Text style={styles.pagerText}>
                      {index + 1} of {memories.length} here
                    </Text>
                    <Pressable
                      accessibilityRole="button"
                      accessibilityLabel="Next memory here"
                      style={dim([styles.step, index === memories.length - 1 && styles.stepOff])}
                      disabled={index === memories.length - 1}
                      onPress={() => onIndex(index + 1)}
                    >
                      <Glyph
                        name="chevron.right"
                        size={17}
                        weight="semibold"
                        color={color.inkSoft}
                      />
                    </Pressable>
                  </View>
                )}
              </View>
            )}
          </View>
        </ScrollView>
      )}
    </Modal>
  );
}

const styles = StyleSheet.create({
  fill: { flex: 1 },
  sheet: { flex: 1, backgroundColor: color.paper },
  // Paper over the live map, not a dimmed one: the pin you tapped stays in
  // view above the card. Locked, it floats in the unlock card's footprint; a
  // story needs the room, so an open one is a tall sheet (docs/10, "Only a
  // locked memory floats").
  over: { flexGrow: 1, justifyContent: 'flex-end' },
  page: { height: '100%' },
  card: { flex: 0, ...lift },
  floating: { ...floatingCard, marginHorizontal: 16 },
  tall: { borderTopLeftRadius: corner.card, borderTopRightRadius: corner.card },
  grabberRow: { alignItems: 'center', paddingTop: 10 },
  grabber: { width: 40, height: 4, borderRadius: 2, backgroundColor: color.rule },
  heading: { paddingHorizontal: 24, paddingTop: 26 },
  body: { paddingHorizontal: 24, paddingTop: 20 },
  place: { ...story.title, paddingRight: 30 },
  meta: { ...label },
  peekFrom: { flexDirection: 'row', alignItems: 'center', gap: 6, marginTop: 4 },
  gate: { flex: 1, alignItems: 'center', justifyContent: 'center', paddingHorizontal: 40, gap: 16 },
  peek: { paddingHorizontal: 24, paddingTop: 20, paddingBottom: 24, gap: 14 },
  tags: { flexDirection: 'row', flexWrap: 'wrap', gap: 6, marginTop: 12 },
  tag: {
    borderWidth: 1,
    borderColor: color.rule,
    borderRadius: corner.pill,
    paddingHorizontal: 10,
    paddingVertical: 4,
  },
  tagText: { ...font.displaySemi, fontSize: 13, color: color.inkSoft },
  approach: { flexDirection: 'row', alignItems: 'center', gap: 18 },
  approachText: { flex: 1, gap: 2 },
  peekFigure: figureSmall,
  gateFigure: figure,
  // A date is not a number. 52px fits "412 m" and wraps "3 May 2031".
  gateNote: {
    ...font.prose,
    fontSize: 16,
    lineHeight: 25,
    color: color.inkSoft,
    textAlign: 'center',
  },
  peekNote: { ...font.prose, fontSize: 16, lineHeight: 25, color: color.inkSoft },
  summary: story.body,
  epic: { flexDirection: 'row', alignItems: 'center', gap: 6, marginBottom: 12 },
  epicText: { ...label, color: color.purple },
  // One rhythm: 8 inside a part, 24 between parts, and no rules between them.
  after: { marginTop: 24, gap: 24 },
  // Gold, not a new colour: it is the memory's own voice (UI.md, "One accent").
  callout: { paddingLeft: 12, borderLeftWidth: 3, borderLeftColor: color.gold, gap: 8 },
  calloutQuiet: { borderLeftColor: color.rule },
  calloutTitle: { flexDirection: 'row', alignItems: 'center', gap: 6 },
  quote: { marginTop: 24 },
  waiting: { ...label, color: color.sealDeep },
  date: { ...story.body, color: color.inkSoft, marginTop: 4 },
  byline: { marginTop: 8 },
  flourish: { marginTop: 20 },
  bylineRow: { flexDirection: 'row', alignItems: 'center', gap: 8 },
  bylineText: { ...story.meta, flexShrink: 1 },
  bylineName: { color: color.ink },
  out: { color: color.gold },
  actions: { padding: 20, gap: 12, borderTopWidth: 1, borderTopColor: color.rule },
  heart: { flexDirection: 'row', alignItems: 'center', gap: 6 },
  heartText: { ...label, color: color.inkSoft, fontVariant: ['tabular-nums'] },
  pager: { flexDirection: 'row', alignItems: 'center', justifyContent: 'center', gap: 16 },
  pagerText: {
    ...label,
    minWidth: 110,
    textAlign: 'center',
  },
  // 44, not 40: this is the control that reaches the other 22 memories under a
  // stacked pin, and it was below the minimum target size.
  step: {
    width: 44,
    height: 44,
    borderRadius: 22,
    borderWidth: 1,
    borderBottomWidth: 3,
    borderColor: color.rule,
    alignItems: 'center',
    justifyContent: 'center',
  },
  stepOff: { opacity: 0.3 },
  ask: {
    marginHorizontal: 24,
    marginTop: 16,
    padding: 16,
    borderWidth: 1,
    borderColor: color.rule,
    borderRadius: corner.card,
    gap: 4,
  },
  askTitle: { ...font.displaySemi, fontSize: 16, color: color.ink, marginBottom: 4 },
  askChoice: { paddingVertical: 10 },
  askText: { ...font.prose, fontSize: 16, color: color.ink },
  askDestructive: { color: color.gold },
  askCancel: { ...font.prose, fontSize: 16, color: color.inkSoft },
  close: { position: 'absolute', top: 20, right: 20, zIndex: 1 },
  // One along from the ×.
  more: { position: 'absolute', top: 20, right: 58, zIndex: 1 },
  placeBesideMore: { paddingRight: 68 },
});
