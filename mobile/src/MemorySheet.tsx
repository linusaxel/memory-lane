import { useEffect, useRef, useState } from 'react';
import {
  Animated,
  Easing,
  Linking,
  Modal,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  View,
} from 'react-native';

import type { Coordinates, LocatedMemory } from './api.ts';
import MemoryMedia from './MemoryMedia.tsx';
import Approach from './Approach.tsx';
import HeartGlyph from './HeartGlyph.tsx';
import Notes from './Notes.tsx';
import Padlock from './Padlock.tsx';
import SourceLine from './SourceLine.tsx';
import { FALLBACK_RADIUS_M } from './reach.ts';
import { distance, duration } from './format.ts';
import { metersBetween } from './region.ts';
import { buttonText, color, dim, font, label } from './theme.ts';
import UnlockButton from './UnlockButton.tsx';

type Props = {
  /** Everything at the tapped point. One marker can hide a dozen memories. */
  memories: LocatedMemory[];
  index: number;
  onIndex: (next: number) => void;
  onClose: () => void;
  /** Where the person is standing, or null if they said no to location. */
  position: Coordinates | null;
  onUnlock: (memory: LocatedMemory) => void;
  unlocking: boolean;
  unlockError: string | null;
  /** Present only for a memory this account filed, and only while it is open -
   *  a sealed one shows the locked composition instead, which has no room for
   *  this. */
  onEdit?: (memory: LocatedMemory) => void;
  /** This device walked here and opened it. Not the same as "unlocked": most of
   *  this corpus sits on city centroids and was never gated, and a stamp on one
   *  of those would claim a walk that never happened. */
  earned?: boolean;
  /** Say this one mattered. Absent while locked - there is nothing to react
   *  to yet, and the server never sees a heart request the client didn't ask
   *  for. */
  onHeart?: (memory: LocatedMemory) => void;
  /** This device already hearted it, one-way and permanent - the glyph fills
   *  and stays filled. */
  hearted?: boolean;
};

function formatDistance(meters: number | null): string | null {
  return meters == null ? null : distance(meters, { suffix: 'away' });
}

const MONTHS = [
  'January',
  'February',
  'March',
  'April',
  'May',
  'June',
  'July',
  'August',
  'September',
  'October',
  'November',
  'December',
];

/** "3 May 2031", the same wording api/card.py renders.
 *
 *  Parsed by hand rather than through `new Date(iso)`, which reads a bare ISO
 *  date as UTC midnight and then prints the day before it anywhere west of
 *  Greenwich. A seal that says the wrong day is a seal nobody trusts. */
function formatSealDate(iso: string): string {
  const [year, month, day] = iso.split('-').map(Number);
  return `${day} ${MONTHS[month - 1]} ${year}`;
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
  onUnlock,
  onHeart,
  hearted,
  unlocking,
  unlockError,
  onEdit,
  earned,
}: Props) {
  const memory = memories[index] ?? null;
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
  // A different refusal, and the app must not confuse them: walking to a time
  // capsule does nothing, so it never gets the unlock control or the word
  // "within reach". The server sends the date only while it still means
  // something, so this is false the moment it opens.
  const sealed = !!memory?.opens_at;

  // The reveal is the payoff. Swapping the text in place would throw away the
  // only moment the product has - so the content arrives, once, on the frame
  // after a memory stops being locked.
  const reveal = useRef(new Animated.Value(1)).current;
  const seen = useRef<string | null>(null);

  useEffect(() => {
    if (!memory) return;
    const justOpened = seen.current === `${memory.id}:true` && !memory.locked;
    seen.current = `${memory.id}:${memory.locked}`;
    if (!justOpened) return;

    reveal.setValue(0);
    Animated.timing(reveal, {
      toValue: 1,
      duration: 420,
      easing: Easing.out(Easing.cubic),
      useNativeDriver: true,
    }).start();
  }, [memory, reveal]);

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

  // The same value, read as a press rather than a rise: the wax comes down onto
  // the page. This is the only place the stamp is allowed to move - the pin on
  // the map carries it afterwards, and markers do not animate.
  const pressed = {
    opacity: reveal,
    transform: [{ scale: reveal.interpolate({ inputRange: [0, 1], outputRange: [2.4, 1] }) }],
  };

  return (
    <Modal
      visible={!!memory}
      animationType="slide"
      presentationStyle="pageSheet"
      // Required, or the Android back button does nothing.
      onRequestClose={onClose}
    >
      {memory && (
        <View style={styles.sheet}>
          <View style={styles.grabberRow}>
            <View style={styles.grabber} />
          </View>

          <View style={styles.heading}>
            <Text style={styles.place}>{memory.place.name}</Text>
            <View style={styles.metaRow}>
              {(!locked || withinReach) && formatDistance(fromHere ?? memory.distance_meters) && (
                <Text style={[styles.meta, withinReach && locked && !sealed && styles.reachable]}>
                  {formatDistance(fromHere ?? memory.distance_meters)}
                </Text>
              )}
              {/* The server already sorted it to the top; this says why. No
                  accent - the seal means openable and nothing else gets it. */}
              {memory.anniversary && <Text style={styles.meta}>on this day</Text>}
              {locked && (
                <Text style={[styles.meta, withinReach && !sealed ? styles.reachable : styles.sealed]}>
                  {sealed ? 'sealed' : withinReach ? 'within reach' : 'locked'}
                </Text>
              )}
            </View>
          </View>

          {/* Two different screens, not one screen with the middle deleted. A
              locked memory has nothing to scroll, so it gets a centred
              composition; an open one is a story and gets the reading column. */}
          {locked ? (
            <View style={styles.gate}>
              {sealed ? (
                <>
                  <Padlock size={34} color={color.faded} />
                  <Text style={[styles.gateFigure, styles.sealDate]}>
                    {formatSealDate(memory.opens_at!)}
                  </Text>
                  <Text style={styles.gateNote}>
                    Sealed until then. Standing here does not open it any sooner.
                  </Text>
                </>
              ) : withinReach ? (
                <>
                  <UnlockButton onUnlock={() => onUnlock(memory)} busy={unlocking} />
                  <Text style={styles.gateNote}>
                    {unlockError ?? 'You are standing close enough to open this one.'}
                  </Text>
                  {/* The pull belongs here most of all. It was shown only to
                      people too far away to act on it, and withheld from the
                      one person who is about to hold the ring - so the second
                      before the hold, which is the whole of the suspense, said
                      less than the minute before the walk. Still only the
                      count: handing the photograph over is the leak. */}
                  {waiting}
                </>
              ) : (
                <>
                  <Approach meters={fromHere} radius={radius} />
                  <Text style={styles.gateFigure}>
                    {position == null
                      ? '—'
                      : formatDistance(fromHere)?.replace(' away', '')}
                  </Text>
                  <Text style={styles.gateNote}>
                    {position == null
                      ? 'Turn on location to unlock memories by standing near them.'
                      : `Get within ${Math.round(radius)} m and you can open it.`}
                  </Text>
                  {waiting}
                </>
              )}
            </View>
          ) : (
            <>
              <ScrollView contentContainerStyle={styles.body}>
                {/* The summary carries the sheet when nothing is attached, which
                    is every extracted memory; a submission usually brings a
                    photograph and the weight shifts to it. */}
                {earned && (
                  <Animated.View style={[styles.stamp, pressed]}>
                    <View style={styles.stampMark} />
                  </Animated.View>
                )}

                <Animated.View style={revealed}>
                  <Text style={styles.summary}>{memory.summary}</Text>

                  <MemoryMedia media={memory.media} />

                  {memory.tags?.length > 0 && (
                    <View style={styles.tags}>
                      {memory.tags.map((tag) => (
                        <Text key={tag} style={styles.tag}>
                          {tag}
                        </Text>
                      ))}
                    </View>
                  )}

                  <Notes memoryId={memory.id} isAuthor={!!onEdit} />

                  {!locked && onEdit && (
                    <Pressable
                      style={dim(styles.report)}
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
              {(memory.author || memory.content?.source || memory.content?.title) && (
                <Animated.View style={[styles.credit, revealed]}>
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
                </Animated.View>
              )}
            </>
          )}

          <View style={styles.actions}>
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
            {!locked && onHeart && (
              <Pressable
                style={dim(styles.heart)}
                accessibilityRole="button"
                accessibilityLabel={
                  (hearted ? 'Hearted' : 'Heart this memory') +
                  (memory.heart_count === 1
                    ? ', 1 heart'
                    : memory.heart_count > 1
                      ? `, ${memory.heart_count} hearts`
                      : '')
                }
                onPress={() => onHeart(memory)}
              >
                <HeartGlyph size={18} color={color.inkSoft} filled={hearted} />
                {memory.heart_count > 0 && (
                  <Text style={styles.heartText}>
                    {memory.heart_count === 1 ? '1 heart' : `${memory.heart_count} hearts`}
                  </Text>
                )}
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
                onPress={() => open(memory.content!.url, 'Nothing here can open that source.')}
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
            <Pressable
              style={dim(styles.close)}
              accessibilityRole="button"
              accessibilityLabel="Close"
              onPress={onClose}
            >
              <Text style={styles.closeText}>Close</Text>
            </Pressable>
          </View>
        </View>
      )}
    </Modal>
  );
}

const styles = StyleSheet.create({
  sheet: { flex: 1, backgroundColor: color.paper },
  grabberRow: { alignItems: 'center', paddingTop: 10 },
  grabber: { width: 40, height: 4, borderRadius: 2, backgroundColor: color.rule },
  heading: { paddingHorizontal: 24, paddingTop: 26 },
  body: { paddingHorizontal: 24, paddingTop: 22, paddingBottom: 12 },
  // The serif is the point: these are stories somebody told, not table rows.
  place: { fontFamily: font.display, fontSize: 30, lineHeight: 36, color: color.ink },
  // The apparatus speaks in mono. Distances are measurements, so they look like
  // measurements rather than like more prose.
  metaRow: { flexDirection: 'row', gap: 14, marginTop: 10 },
  meta: { ...label },
  reachable: { color: color.seal },
  sealed: { color: color.inkFaint },
  gate: { flex: 1, alignItems: 'center', justifyContent: 'center', paddingHorizontal: 40, gap: 16 },
  gateFigure: { fontFamily: font.display, fontSize: 52, color: color.ink, letterSpacing: -1 },
  // A date is not a number. 52px fits "412 m" and wraps "3 May 2031".
  sealDate: { fontSize: 34, letterSpacing: 0, textAlign: 'center' },
  gateNote: {
    fontFamily: font.prose,
    fontSize: 16,
    lineHeight: 25,
    color: color.inkSoft,
    textAlign: 'center',
  },
  // The impression, on the page this time: the same ring the pin wears once
  // this is earned, inked the other way round because the ground is paper.
  stamp: { alignSelf: 'flex-start', marginBottom: 18 },
  stampMark: {
    width: 22,
    height: 22,
    borderRadius: 11,
    borderWidth: 2,
    borderColor: color.ink,
  },
  summary: { fontFamily: font.prose, fontSize: 19, lineHeight: 31, color: color.ink },
  tags: { flexDirection: 'row', flexWrap: 'wrap', gap: 8, marginTop: 24 },
  tag: {
    ...label,
    fontSize: 10,
    color: color.inkSoft,
    borderWidth: 1,
    borderColor: color.rule,
    paddingHorizontal: 9,
    paddingVertical: 4,
    borderRadius: 3,
    overflow: 'hidden',
  },
  waiting: { ...label, color: color.seal },
  // The strip carries the hairline now, so the three credit variants are just
  // their lines. Pinned above the actions, it is in every screenshot.
  credit: {
    paddingHorizontal: 24,
    paddingTop: 16,
    paddingBottom: 4,
    borderTopWidth: 1,
    borderTopColor: color.rule,
  },
  byline: { gap: 2 },
  bylineLabel: { ...label, fontSize: 9 },
  bylineName: { fontFamily: font.displaySemi, fontSize: 16, color: color.ink },
  // Quiet on purpose. It has to be findable and must not be the thing the eye
  // lands on under somebody's story.
  report: { marginTop: 28, alignSelf: 'flex-start', paddingVertical: 8 },
  reportText: { ...label, fontSize: 9, color: color.inkFaint },
  source: { fontFamily: font.mono, fontSize: 12, lineHeight: 19, color: color.inkFaint },
  actions: { padding: 20, gap: 12, borderTopWidth: 1, borderTopColor: color.rule },
  // Ink, not red. The seal is the unlock and nothing else gets to wear it.
  watch: { backgroundColor: color.ink, paddingVertical: 16, borderRadius: 4, alignItems: 'center' },
  watchText: { ...buttonText, color: color.paper },
  linkFailed: { fontFamily: font.mono, fontSize: 12, color: color.inkFaint, textAlign: 'center' },
  secondary: {
    borderWidth: 1,
    borderColor: color.rule,
    paddingVertical: 15,
    borderRadius: 4,
    alignItems: 'center',
  },
  secondaryText: { ...buttonText, color: color.inkSoft },
  heart: { flexDirection: 'row', alignItems: 'center', alignSelf: 'flex-start', gap: 8, paddingVertical: 8 },
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
  stepText: { fontSize: 22, color: color.inkSoft, lineHeight: 26 },
  close: { paddingVertical: 12, alignItems: 'center' },
  closeText: { ...label, color: color.inkFaint },
});
