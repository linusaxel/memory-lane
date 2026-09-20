import { useEffect, useRef, useState } from 'react';
import {
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
} from 'react-native';

import type { Coordinates, LocatedMemory } from './api.ts';
import MemoryMedia from './MemoryMedia.tsx';
import Padlock from './Padlock.tsx';
import SourceLine from './SourceLine.tsx';
import { FALLBACK_RADIUS_M } from './reach.ts';
import { metersBetween } from './region.ts';
import { color, font, label } from './theme.ts';
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
  /** Absent when the sheet is already over the map. */
  onShowOnMap?: (memory: LocatedMemory) => void;
  /** Absent for extracted memories: there is nobody to report a podcast to. */
  onReport?: (memory: LocatedMemory) => void;
  /** Already reported by this device, so the control says so instead of
   *  pretending a second press does anything. */
  reported?: boolean;
};

function formatDistance(meters: number | null): string | null {
  if (meters == null) return null;
  return meters < 1000
    ? `${Math.round(meters)} m away`
    : `${(meters / 1000).toFixed(1)} km away`;
}

/** Walking directions to a coordinate, in whatever maps app the phone has. */
function walkingDirectionsUrl(lat: number, lng: number): string {
  return Platform.OS === 'ios'
    ? `https://maps.apple.com/?daddr=${lat},${lng}&dirflg=w`
    : `https://www.google.com/maps/dir/?api=1&destination=${lat},${lng}&travelmode=walking`;
}

function formatTimestamp(seconds: number): string {
  const total = Math.floor(seconds);
  const h = Math.floor(total / 3600);
  const m = Math.floor((total % 3600) / 60);
  const s = total % 60;
  const mm = h > 0 ? String(m).padStart(2, '0') : String(m);
  return `${h > 0 ? `${h}:` : ''}${mm}:${String(s).padStart(2, '0')}`;
}

export default function MemorySheet({
  memories,
  index,
  onIndex,
  onClose,
  position,
  onUnlock,
  unlocking,
  unlockError,
  onShowOnMap,
  onReport,
  reported,
}: Props) {
  const memory = memories[index] ?? null;
  const many = memories.length > 1;
  // openURL rejects when nothing can handle the link - no browser, no maps app,
  // a locked-down device. Both links here can hit it, so both say so instead of
  // appearing to do nothing.
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

  const revealed = {
    opacity: reveal,
    transform: [{ translateY: reveal.interpolate({ inputRange: [0, 1], outputRange: [16, 0] }) }],
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
                <Text style={[styles.meta, withinReach && locked && styles.reachable]}>
                  {formatDistance(fromHere ?? memory.distance_meters)}
                </Text>
              )}
              {locked ? (
                <Text style={[styles.meta, withinReach ? styles.reachable : styles.sealed]}>
                  {withinReach ? 'within reach' : 'locked'}
                </Text>
              ) : (
                memory.confidence === 'high' && (
                  <Text style={[styles.meta, styles.confident]}>high confidence</Text>
                )
              )}
            </View>
          </View>

          {/* Two different screens, not one screen with the middle deleted. A
              locked memory has nothing to scroll, so it gets a centred
              composition; an open one is a story and gets the reading column. */}
          {locked ? (
            <View style={styles.gate}>
              {withinReach ? (
                <>
                  <UnlockButton onUnlock={() => onUnlock(memory)} busy={unlocking} />
                  <Text style={styles.gateNote}>
                    {unlockError ?? 'You are standing close enough to open this one.'}
                  </Text>
                </>
              ) : (
                <>
                  <Padlock size={34} color="#d4d4d8" />
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
                  {/* Knowing a photograph is waiting is the pull. Handing it
                      over would be the leak, so only the count travels. */}
                  {memory.media_count > 0 && (
                    <Text style={styles.waiting}>
                      {memory.media_count === 1
                        ? '1 attachment waiting'
                        : `${memory.media_count} attachments waiting`}
                    </Text>
                  )}
                  {/* Knowing it is 412m away and having no idea which way is
                      most of a dead end. The distance is the ask; this is the
                      answer. */}
                  <Pressable
                    style={styles.walk}
                    accessibilityRole="button"
                    onPress={() =>
                      open(
                        walkingDirectionsUrl(
                          memory.place.coordinates.lat,
                          memory.place.coordinates.lng,
                        ),
                        'No maps app to open directions in.',
                      )
                    }
                  >
                    <Text style={styles.walkText}>Walk there</Text>
                  </Pressable>
                </>
              )}
            </View>
          ) : (
            <ScrollView contentContainerStyle={styles.body}>
              {/* The summary carries the sheet when nothing is attached, which
                  is every extracted memory; a submission usually brings a
                  photograph and the weight shifts to it. */}
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

                {/* A memory somebody filed has no channel to credit - the
                    person is the credit, and the app must not leave it off any
                    more than the server would. */}
                {memory.author ? (
                  <View style={styles.byline}>
                    <Text style={styles.bylineLabel}>Filed by</Text>
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

                {!locked && onReport && (
                  <Pressable
                    style={styles.report}
                    accessibilityRole="button"
                    disabled={reported}
                    onPress={() => onReport(memory)}
                  >
                    <Text style={styles.reportText}>
                      {reported ? 'Reported' : 'Report this memory'}
                    </Text>
                  </Pressable>
                )}
              </Animated.View>
            </ScrollView>
          )}

          <View style={styles.actions}>
            {/* Without this, every memory but the first at a stacked point is
                unreachable - and 60% of this corpus sits on a shared point. */}
            {many && (
              <View style={styles.pager}>
                <Pressable
                  accessibilityRole="button"
                  accessibilityLabel="Previous memory here"
                  style={[styles.step, index === 0 && styles.stepOff]}
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
                  style={[styles.step, index === memories.length - 1 && styles.stepOff]}
                  disabled={index === memories.length - 1}
                  onPress={() => onIndex(index + 1)}
                >
                  <Text style={styles.stepText}>›</Text>
                </Pressable>
              </View>
            )}
            {/* Opened from the collection, the sheet is a page in a list and
                the place is a name. This is the only route back to where it
                actually is. */}
            {onShowOnMap && (
              <Pressable
                style={styles.secondary}
                accessibilityRole="button"
                onPress={() => onShowOnMap(memory)}
              >
                <Text style={styles.secondaryText}>Show on map</Text>
              </Pressable>
            )}
            {!locked && memory.content && (
              <Pressable
                style={styles.watch}
                // timestamp_url already points at the right second.
                onPress={() =>
                  open(memory.content!.timestamp_url, 'Nothing here can open that video.')
                }
              >
                <Text style={styles.watchText}>
                  Watch at {formatTimestamp(memory.content.timestamp_start)}
                </Text>
              </Pressable>
            )}
            {linkFailed && <Text style={styles.linkFailed}>{linkFailed}</Text>}
            <Pressable style={styles.close} onPress={onClose}>
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
  confident: { color: '#5C7A4A' },
  reachable: { color: color.seal },
  sealed: { color: color.inkFaint },
  gate: { flex: 1, alignItems: 'center', justifyContent: 'center', paddingHorizontal: 40, gap: 16 },
  gateFigure: { fontFamily: font.display, fontSize: 52, color: color.ink, letterSpacing: -1 },
  gateNote: {
    fontFamily: font.prose,
    fontSize: 16,
    lineHeight: 25,
    color: color.inkSoft,
    textAlign: 'center',
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
  byline: {
    marginTop: 26,
    paddingTop: 18,
    borderTopWidth: 1,
    borderTopColor: color.rule,
    gap: 2,
  },
  bylineLabel: { ...label, fontSize: 9 },
  bylineName: { fontFamily: font.displaySemi, fontSize: 16, color: color.ink },
  // Quiet on purpose. It has to be findable and must not be the thing the eye
  // lands on under somebody's story.
  report: { marginTop: 28, alignSelf: 'flex-start', paddingVertical: 8 },
  reportText: { ...label, fontSize: 9, color: color.inkFaint },
  source: {
    fontFamily: font.mono,
    fontSize: 12,
    lineHeight: 19,
    color: color.inkFaint,
    marginTop: 26,
  },
  actions: { padding: 20, gap: 12, borderTopWidth: 1, borderTopColor: color.rule },
  // Ink, not red. The seal is the unlock and nothing else gets to wear it.
  watch: { backgroundColor: color.ink, paddingVertical: 16, borderRadius: 4, alignItems: 'center' },
  watchText: {
    color: color.paper,
    fontFamily: font.monoBold,
    fontSize: 12,
    letterSpacing: 1.2,
    textTransform: 'uppercase',
  },
  walk: {
    marginTop: 8,
    borderWidth: 1,
    borderColor: color.ink,
    paddingVertical: 13,
    paddingHorizontal: 26,
    borderRadius: 4,
  },
  walkText: {
    fontFamily: font.monoBold,
    fontSize: 12,
    letterSpacing: 1.2,
    textTransform: 'uppercase',
    color: color.ink,
  },
  linkFailed: { fontFamily: font.mono, fontSize: 12, color: color.inkFaint, textAlign: 'center' },
  secondary: {
    borderWidth: 1,
    borderColor: color.rule,
    paddingVertical: 15,
    borderRadius: 4,
    alignItems: 'center',
  },
  secondaryText: {
    fontFamily: font.monoBold,
    fontSize: 12,
    letterSpacing: 1.2,
    textTransform: 'uppercase',
    color: color.inkSoft,
  },
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
