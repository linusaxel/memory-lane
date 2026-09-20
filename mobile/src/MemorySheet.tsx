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
import Padlock from './Padlock.tsx';
import { metersBetween } from './region.ts';
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
};

/** Only used if a memory somehow arrives without the server's radius. */
const FALLBACK_RADIUS_M = 150;

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
              {/* No images exist anywhere in the schema, so the summary carries
                  the whole sheet - it gets the typographic weight. */}
              <Animated.View style={revealed}>
                <Text style={styles.summary}>{memory.summary}</Text>

                {memory.tags?.length > 0 && (
                  <View style={styles.tags}>
                    {memory.tags.map((tag) => (
                      <Text key={tag} style={styles.tag}>
                        {tag}
                      </Text>
                    ))}
                  </View>
                )}

                {memory.content?.title && (
                  <Text style={styles.source} numberOfLines={2}>
                    {memory.content.title}
                  </Text>
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
  sheet: { flex: 1, backgroundColor: '#fff' },
  grabberRow: { alignItems: 'center', paddingTop: 10 },
  grabber: { width: 40, height: 5, borderRadius: 3, backgroundColor: '#d4d4d8' },
  heading: { paddingHorizontal: 24, paddingTop: 24 },
  body: { paddingHorizontal: 24, paddingTop: 20, paddingBottom: 12 },
  place: { fontSize: 26, fontWeight: '700', color: '#18181b', letterSpacing: -0.5 },
  metaRow: { flexDirection: 'row', gap: 12, marginTop: 6 },
  meta: { fontSize: 13, color: '#71717a' },
  confident: { color: '#15803d' },
  reachable: { color: '#b45309', fontWeight: '600' },
  sealed: { color: '#a1a1aa' },
  // The locked half owns the empty space instead of leaving it lying around.
  gate: { flex: 1, alignItems: 'center', justifyContent: 'center', paddingHorizontal: 40, gap: 14 },
  gateFigure: { fontSize: 44, fontWeight: '700', color: '#18181b', letterSpacing: -1 },
  gateNote: { fontSize: 15, lineHeight: 22, color: '#71717a', textAlign: 'center' },
  walk: {
    marginTop: 10,
    borderWidth: 1.5,
    borderColor: '#d4d4d8',
    paddingVertical: 12,
    paddingHorizontal: 26,
    borderRadius: 12,
  },
  walkText: { fontSize: 15, fontWeight: '600', color: '#3f3f46' },
  linkFailed: { fontSize: 13, color: '#a1a1aa', textAlign: 'center' },
  summary: { fontSize: 17, lineHeight: 26, color: '#27272a' },
  tags: { flexDirection: 'row', flexWrap: 'wrap', gap: 8, marginTop: 22 },
  tag: {
    fontSize: 12,
    color: '#3f3f46',
    backgroundColor: '#f4f4f5',
    paddingHorizontal: 10,
    paddingVertical: 5,
    borderRadius: 12,
    overflow: 'hidden',
  },
  source: { fontSize: 13, color: '#a1a1aa', marginTop: 24, fontStyle: 'italic' },
  actions: { padding: 20, gap: 10, borderTopWidth: 1, borderTopColor: '#f4f4f5' },
  watch: { backgroundColor: '#dc2626', paddingVertical: 15, borderRadius: 12, alignItems: 'center' },
  watchText: { color: '#fff', fontSize: 16, fontWeight: '600' },
  pager: { flexDirection: 'row', alignItems: 'center', justifyContent: 'center', gap: 16 },
  pagerText: { fontSize: 13, color: '#71717a', minWidth: 96, textAlign: 'center' },
  step: {
    width: 40,
    height: 40,
    borderRadius: 20,
    backgroundColor: '#f4f4f5',
    alignItems: 'center',
    justifyContent: 'center',
  },
  stepOff: { opacity: 0.35 },
  stepText: { fontSize: 22, color: '#3f3f46', lineHeight: 26 },
  close: { paddingVertical: 12, alignItems: 'center' },
  closeText: { color: '#71717a', fontSize: 15 },
});
