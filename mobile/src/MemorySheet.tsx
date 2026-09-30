import { useEffect, useRef, useState } from 'react';
import {
  ActionSheetIOS,
  Alert,
  Animated,
  Easing,
  Linking,
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

import CloseButton from './CloseButton.tsx';
import type { Coordinates, LocatedMemory } from './api.ts';
import MemoryMedia from './MemoryMedia.tsx';
import Approach from './Approach.tsx';
import HeartGlyph from './HeartGlyph.tsx';
import Notes from './Notes.tsx';
import SourceLine from './SourceLine.tsx';
import { FALLBACK_RADIUS_M } from './reach.ts';
import { distance, duration } from './format.ts';
import { summaryParts } from './hashtags.ts';
import { metersBetween } from './region.ts';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { Circle, Svg } from 'react-native-svg';
import {
  button,
  buttonText,
  buttonTextSmall,
  color,
  dim,
  figure,
  figureSmall,
  floating as floatingCard,
  font,
  label,
  lift,
  radius as corner,
} from './theme.ts';
import YouGlyph from './YouGlyph.tsx';

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
  /** Present only for a memory this account filed. */
  onEdit?: (memory: LocatedMemory) => void;
  /** Say this one mattered. Absent while locked - there is nothing to react
   *  to yet, and the server never sees a heart request the client didn't ask
   *  for. */
  onHeart?: (memory: LocatedMemory) => void;
  /** This device already hearted it, one-way and permanent - the glyph fills
   *  and stays filled. */
  hearted?: boolean;
  /** Present only on the map before a walk: a walk through a locked memory,
   *  a side way to it now (F29). */
  onWalkHere?: () => void;
  /** Today's free unlocks left, and opening this one with one, from wherever
   *  you are (docs/10, "Three free a day, then steps where you stand"). */
  freeLeft?: number;
  onOpenFree?: () => void;
  /** A free open is in flight: one tap spends one. */
  opening?: boolean;
  /** What standing on it costs once the free ones are gone; absent for a
   *  subscriber, who pays nothing there. */
  stepPrice?: number;
  /** Steps still to walk before standing here opens it; 0 when it can. */
  stepsShort?: number;
  /** Over the map, in any stage: a card. Over the journal: a page. */
  compact?: boolean;
  /** Absent for extracted memories, and for your own: there is nobody to
   *  report a podcast to, and reporting yourself is not a real control. */
  onReport?: (memory: LocatedMemory) => void;
  /** Already reported from this device, so the control says so instead of
   *  offering a second press that does nothing. */
  reported?: boolean;
  /** Present exactly when onReport is: blocking hides everything its author
   *  posted, on every phone on this account. */
  onBlock?: (memory: LocatedMemory) => void;
};

/** Report and block, behind ⋯ the way a post does it: App Store 1.2 wants both
 *  reachable, not on show. There is no unblock, so block asks first. */
function moreActions(
  memory: LocatedMemory,
  reported: boolean | undefined,
  onReport: (memory: LocatedMemory) => void,
  onBlock?: (memory: LocatedMemory) => void,
) {
  const who = memory.author?.name === 'Anonymous' ? 'this person' : memory.author?.name;
  const actions = [
    reported ? null : { label: 'Report this memory', run: () => onReport(memory) },
    onBlock && who
      ? {
          label: `Block ${who}`,
          destructive: true,
          run: () =>
            Alert.alert(`Block ${who}?`, 'You will not see anything they post.', [
              { text: 'Cancel', style: 'cancel' },
              { text: 'Block', style: 'destructive', onPress: () => onBlock(memory) },
            ]),
        }
      : null,
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
  onHeart,
  hearted,
  onEdit,
  onWalkHere,
  freeLeft = 0,
  onOpenFree,
  opening = false,
  stepPrice,
  stepsShort = 0,
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
  // openURL rejects when nothing can handle the link - no browser, a
  // locked-down device. The source link says so instead of appearing to do
  // nothing.
  const [linkFailed, setLinkFailed] = useState<string | null>(null);

  const open = (url: string, whenNothingOpens: string) => {
    setLinkFailed(null);
    Linking.openURL(url).catch(() => setLinkFailed(whenNothingOpens));
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
  const openFree = peeking && !withinReach && freeLeft > 0 && !!onOpenFree;
  const shortNote = `You're ${stepsShort.toLocaleString()} steps short.`;
  const peekNote = withinReach
    ? stepsShort > 0
      ? `You're right here. ${shortNote}`
      : "You're right here. Hold the ring on the map to open it."
    : fromHere == null
      ? 'Turn on location to see how far.'
      : openFree
        ? null
        : stepPrice && stepsShort > 0
          ? `Walk within ${Math.round(radius)} m. ${shortNote}`
          : stepPrice
          ? `Walk within ${Math.round(radius)} m, then open it for ${stepPrice.toLocaleString()} steps.`
          : `Get within ${Math.round(radius)} m to unlock it.`;
  const hearts = memory?.heart_count ?? 0;
  const heartsText = hearts === 1 ? '1 heart' : `${hearts} hearts`;
  // Your own memory: you see that it mattered, you cannot say so (api/write.py
  // heart_memory refuses it too). onEdit is only passed for your own.
  const heart =
    !memory || locked || !onHeart ? null : onEdit ? (
      hearts > 0 && (
        <View style={styles.heart}>
          <HeartGlyph size={18} color={color.inkSoft} filled />
          <Text style={styles.heartText}>{heartsText}</Text>
        </View>
      )
    ) : (
      <Pressable
        style={dim(styles.heart)}
        hitSlop={8}
        accessibilityRole="button"
        accessibilityLabel={(hearted ? 'Hearted' : 'Heart this memory') + (hearts > 0 ? `, ${heartsText}` : '')}
        onPress={() => onHeart(memory)}
      >
        <HeartGlyph size={18} color={color.inkSoft} filled={hearted} />
        {hearts > 0 && <Text style={styles.heartText}>{heartsText}</Text>}
      </Pressable>
    );

  // The reveal is the payoff. Swapping the text in place would throw away the
  // only moment the product has - so the content arrives, once, as the sheet
  // opens on what the hold unlocked.
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

  useEffect(() => {
    if (!memory || memory.locked || memory.id !== revealId || arrived.current === revealId) return;
    arrived.current = revealId;

    reveal.setValue(0);
    Animated.timing(reveal, {
      toValue: 1,
      duration: 420,
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

  const revealed = {
    opacity: reveal,
    transform: [{ translateY: reveal.interpolate({ inputRange: [0, 1], outputRange: [16, 0] }) }],
  };

  return (
    <Modal
      visible={!!memory}
      animationType="slide"
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
                  ? [styles.card, styles.floating, { maxHeight: screenHeight * 0.6, marginBottom: 16 + insets.bottom }]
                  : [styles.card, styles.tall, { height: screenHeight * 0.92 }]),
            ]}
          >
            <View style={styles.grabberRow}>
              <View style={styles.grabber} />
            </View>
            <CloseButton place={styles.close} onPress={onClose} />
            {!locked && onReport && (
              <Pressable
                style={dim(styles.more)}
                hitSlop={7}
                accessibilityRole="button"
                accessibilityLabel="More"
                onPress={() => moreActions(memory, reported, onReport, onBlock)}
              >
                <Svg width={14} height={4} viewBox="0 0 14 4">
                  {[2, 7, 12].map((cx) => (
                    <Circle key={cx} cx={cx} cy={2} r={1.6} fill={color.inkSoft} />
                  ))}
                </Svg>
              </Pressable>
            )}

            <View style={styles.heading}>
              <Text style={[styles.place, !locked && onReport && styles.placeBesideMore]}>
                {memory.place.name}
              </Text>
              {peeking && (memory.author || memory.source_name) && (
                <View style={styles.peekFrom}>
                  {memory.author && <YouGlyph size={13} color={color.inkFaint} />}
                  <Text style={styles.meta} numberOfLines={1}>
                    {memory.author
                      ? `Left by ${memory.author.name}`
                      : `From ${memory.source_name}`}
                  </Text>
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
              <View style={styles.metaRow}>
                {!locked && formatDistance(fromHere ?? memory.distance_meters) && (
                  <Text style={styles.meta}>
                    {formatDistance(fromHere ?? memory.distance_meters)}
                  </Text>
                )}
                {/* The server already sorted it to the top; this says why. No
                    accent - the seal means openable and nothing else gets it. */}
                {memory.anniversary && <Text style={styles.meta}>on this day</Text>}
              </View>
            </View>

            {/* Two different screens, not one screen with the middle deleted. A
                locked memory has nothing to scroll, so it gets a centred
                composition; an open one is a story and gets the reading column. */}
            {peeking ? (
              <View style={styles.peek}>
                {/* The lock is the ring you will hold, drawn as how far there is
                    still to go: a condition to meet, not a badge. */}
                <View style={styles.approach}>
                  <Approach meters={fromHere} radius={radius} />
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
                <Approach meters={fromHere} radius={radius} />
                <Text style={styles.gateFigure}>
                  {position == null
                    ? '—'
                    : formatDistance(fromHere)?.replace(' away', '')}
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
                  contentContainerStyle={styles.body}
                  keyboardShouldPersistTaps="handled"
                  automaticallyAdjustKeyboardInsets
                >
                  {/* The summary carries the sheet when nothing is attached, which
                      is every extracted memory; a submission usually brings a
                      photograph and the weight shifts to it. */}
                  <Animated.View style={revealed}>
                    {/* The #words are the tags (hashtags.ts): set in the
                        semibold, not a colour, since every colour here already
                        means something (UI.md, "One accent"). Not tappable.
                        A linked name is underlined, like every text link. */}
                    <Text style={styles.summary}>
                      {summaryParts(memory.summary, memory.links).map((part, i) =>
                        part.url ? (
                          <Text
                            key={i}
                            style={styles.nameLink}
                            accessibilityRole="link"
                            onPress={() => open(part.url!, "Couldn't open that link.")}
                          >
                            {part.text}
                          </Text>
                        ) : part.tag ? (
                          <Text key={i} style={styles.hashtag}>
                            {part.text}
                          </Text>
                        ) : (
                          part.text
                        ),
                      )}
                    </Text>

                    <MemoryMedia media={memory.media} />

                    <Notes memoryId={memory.id} isAuthor={!!onEdit} />

                    {!locked && onEdit && (
                      <Pressable
                        style={dim(styles.report)}
                        hitSlop={4}
                        accessibilityRole="button"
                        onPress={() => onEdit(memory)}
                      >
                        <Text style={styles.reportText}>Edit this memory</Text>
                      </Pressable>
                    )}
                  </Animated.View>
                </ScrollView>

                {/* Pinned, not scrolled. A screenshot is the only way geo-gated
                    content travels - you cannot share it by linking to it,
                    because you had to be there - and until now a long story
                    pushed the credit off the bottom of the frame. The place name
                    was already fixed above the scroll; this is the other half of
                    the same rule, and it is the legal posture as much as the
                    design one. The three variants gave up their own top rules to
                    the strip, which now carries the one hairline - so the strip
                    is skipped entirely when there is nothing to credit, rather
                    than leaving a stray rule above the buttons. */}
                {(memory.author || memory.content?.source || memory.content?.title || heart) && (
                  <Animated.View style={[styles.credit, revealed]}>
                    <View style={styles.creditText}>
                      {memory.author ? (
                        <View style={styles.byline}>
                          <Text style={styles.bylineLabel}>Left by</Text>
                          <Text style={styles.bylineName}>{memory.author.name}</Text>
                        </View>
                      ) : memory.content?.source ? (
                        <SourceLine source={memory.content.source} title={memory.content.title} />
                      ) : (
                        memory.content?.title && (
                          <Text style={styles.source} numberOfLines={2}>
                            {memory.content.title}
                          </Text>
                        )
                      )}
                    </View>
                    {heart}
                  </Animated.View>
                )}
              </>
            )}

            {(many ||
              (peeking && (onWalkHere || openFree)) ||
              (!locked && memory.content) ||
              linkFailed) && (
              <View style={[styles.actions, compact && !peeking && { paddingBottom: 20 + insets.bottom }]}>
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
                      <Text style={styles.stepText}>‹</Text>
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
                      <Text style={styles.stepText}>›</Text>
                    </Pressable>
                  </View>
                )}
                {openFree && (
                  <Pressable
                    style={dim(styles.watch)}
                    accessibilityRole="button"
                    accessibilityLabel={`Open it now, ${freeLeft} free today`}
                    accessibilityState={{ busy: opening }}
                    disabled={opening}
                    onPress={onOpenFree}
                  >
                    <Text style={styles.watchText}>Open it now · {freeLeft} free today</Text>
                  </Pressable>
                )}
                {peeking && onWalkHere && (
                  <Pressable
                    style={dim(styles.secondary)}
                    accessibilityRole="button"
                    accessibilityLabel="Walk here"
                    onPress={onWalkHere}
                  >
                    <Text style={styles.secondaryText}>Walk here</Text>
                  </Pressable>
                )}
                {!locked && memory.content && (
                  <Pressable
                    style={dim(styles.watch)}
                    accessibilityRole="button"
                    // Says where it goes, not what it reads. "Watch at 12:04" out of
                    // context is a time of day.
                    accessibilityLabel={
                      memory.content.timestamp_start === null
                        ? 'Open the source'
                        : `Watch this moment, ${formatTimestamp(memory.content.timestamp_start)} into the video`
                    }
                    accessibilityHint={
                      memory.content.timestamp_start === null
                        ? 'Opens the source this memory came from'
                        : 'Opens the source video at that second'
                    }
                    // url is already resolved - a document, or the video at the
                    // right second.
                    onPress={() => open(memory.content!.url, "Couldn't open that link.")}
                  >
                    <Text style={styles.watchText}>
                      {/* An offset only exists when the source is a recording. An
                          archival document has none, and "Watch at 0:00" against a
                          newspaper is a time the source never had. */}
                      {memory.content.timestamp_start === null
                        ? 'Open the source'
                        : `Watch at ${formatTimestamp(memory.content.timestamp_start)}`}
                    </Text>
                  </Pressable>
                )}
                {linkFailed && <Text style={styles.linkFailed}>{linkFailed}</Text>}
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
  body: { paddingHorizontal: 24, paddingTop: 22, paddingBottom: 12 },
  place: { ...font.display, fontSize: 30, lineHeight: 36, color: color.ink, paddingRight: 30 },
  metaRow: { flexDirection: 'row', alignItems: 'center', gap: 14, marginTop: 10 },
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
  summary: { ...font.prose, fontSize: 19, lineHeight: 31, color: color.ink },
  hashtag: { ...font.displaySemi },
  nameLink: { textDecorationLine: 'underline' },
  waiting: { ...label, color: color.sealDeep },
  // The strip carries the hairline now, so the three credit variants are just
  // their lines. Pinned above the actions, it is in every screenshot.
  credit: {
    paddingHorizontal: 24,
    paddingTop: 16,
    paddingBottom: 4,
    borderTopWidth: 1,
    borderTopColor: color.rule,
    flexDirection: 'row',
    alignItems: 'center',
    gap: 16,
  },
  creditText: { flex: 1 },
  byline: { gap: 2 },
  bylineLabel: { ...label, fontSize: 12 },
  bylineName: { ...font.displaySemi, fontSize: 16, color: color.ink },
  // Quiet on purpose. It has to be findable and must not be the thing the eye
  // lands on under somebody's story.
  report: { ...button.outline, ...button.small, marginTop: 28, alignSelf: 'flex-start' },
  reportText: { ...buttonTextSmall, color: color.ink },
  source: { ...font.ui, fontSize: 12, lineHeight: 19, color: color.inkFaint },
  actions: { padding: 20, gap: 12, borderTopWidth: 1, borderTopColor: color.rule },
  // Ember, not seal: the seal is the unlock and nothing else gets to wear it.
  watch: button.solid,
  watchText: { ...buttonText, color: color.paper },
  linkFailed: { ...font.ui, fontSize: 12, color: color.inkFaint, textAlign: 'center' },
  secondary: button.quiet,
  secondaryText: { ...buttonText, color: color.ink },
  heart: { flexDirection: 'row', alignItems: 'center', gap: 6, paddingVertical: 8 },
  heartText: { ...label, color: color.inkSoft },
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
    borderColor: color.rule,
    alignItems: 'center',
    justifyContent: 'center',
  },
  stepOff: { opacity: 0.3 },
  stepText: { ...font.ui, fontSize: 22, color: color.inkSoft, lineHeight: 26 },
  close: { position: 'absolute', top: 20, right: 20, zIndex: 1 },
  // CloseButton's circle, one along.
  more: {
    position: 'absolute',
    top: 20,
    right: 58,
    zIndex: 1,
    width: 30,
    height: 30,
    borderRadius: 15,
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: color.rule,
  },
  placeBesideMore: { paddingRight: 68 },
});
