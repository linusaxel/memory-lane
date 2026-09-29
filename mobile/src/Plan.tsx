/** A walk, drawn first and adjusted after. "Plan a walk" (F29) and a pin's
 *  "Walk here" both go straight to a walk on the map; the card under it holds
 *  the length and the shape, and any change redraws the walk. From "Walk here"
 *  every walk passes that memory, and the length starts at the shortest walk
 *  that reaches it. A one-way walk can end at a spot tapped on the map
 *  (EndPick), asked for per walk and stored nowhere. docs/10, "Draw first,
 *  adjust after".
 *
 *  The press that opened it is the location ask: a press with a reason, so the
 *  system dialog it may raise is never cold (UI.md, "Asking for location").
 *  Refused, the walk is planned from central Copenhagen and the card says so -
 *  never a dead end (rule 1).
 */

import Slider from '@react-native-community/slider';
import { useMemo, useRef, useState } from 'react';
import { ActivityIndicator, PanResponder, Pressable, StyleSheet, Text, View } from 'react-native';

import type { WalkAsk } from './api.ts';
import CloseButton from './CloseButton.tsx';
import { distance } from './format.ts';
import { Chip } from './Submit.tsx';
import { button, buttonText, color, dim, font, label, lift, radius } from './theme.ts';

export const WALK_KM = { min: 1, max: 10, step: 0.5, initial: 4 };

/** api/route_solver.py ROUTE_FILL: under this share of the ask, the map ran out. */
const ROUTE_FILL = 0.8;

type LengthProps = { km: number; min: number; onKm: (km: number) => void };

/** Uncontrolled: the library's `value` is write-only, and lifting every tick
 *  re-rendered all of App under the thumb. No `step` either - iOS snaps the
 *  thumb only on release, which read as a jolt - so it rounds here, and the
 *  walk redraws once, on release. */
function LengthSlider({ km, min, onKm }: LengthProps) {
  const [shown, setShown] = useState(km);
  const round = (v: number) => Math.round(v / WALK_KM.step) * WALK_KM.step;
  return (
    <>
      <Text style={styles.value} accessibilityLiveRegion="polite">{`${shown} km`}</Text>
      <Slider
        style={styles.slider}
        minimumValue={min}
        maximumValue={WALK_KM.max}
        value={km}
        onValueChange={(v) => setShown(round(v))}
        onSlidingComplete={(v) => {
          setShown(round(v));
          onKm(round(v));
        }}
        tapToSeek
        // The native component takes any ColorValue (RNCSliderNativeComponent.ts);
        // only the published typings say string.
        minimumTrackTintColor={color.ember as string}
        maximumTrackTintColor={color.rule as string}
        accessibilityLabel="Walk length"
      />
      <View style={styles.ends}>
        <Text style={label}>{`${min} km`}</Text>
        <Text style={label}>{`${WALK_KM.max} km`}</Text>
      </View>
    </>
  );
}

/** Over the map while it waits for the tap that says where the walk ends. */
export function EndPick({ onCancel }: { onCancel: () => void }) {
  return (
    <View style={styles.card} pointerEvents="box-none">
      <Text style={styles.cardTitle}>Where does it end?</Text>
      <Text style={styles.cardBody}>Tap the map where you want to finish.</Text>
      <Pressable
        style={dim(styles.secondary)}
        onPress={onCancel}
        accessibilityRole="button"
        accessibilityLabel="Cancel"
      >
        <Text style={styles.secondaryText}>Cancel</Text>
      </Pressable>
    </View>
  );
}

type PreviewProps = {
  /** Null until the first walk comes back. */
  stops: number | null;
  meters: number;
  /** What the slider asked for. */
  km: number;
  onKm: (km: number) => void;
  ask: WalkAsk;
  onAsk: (ask: WalkAsk) => void;
  /** The shortest walk that reaches the pin and the end; over WALK_KM.max, none does. */
  floorKm: number;
  /** Go to the map to tap where a one-way walk ends. */
  onPickEnd: () => void;
  /** Planned from central Copenhagen because there was no position to plan from. */
  fallback: boolean;
  /** "Walk here": the place on every walk shown, or null. */
  through: string | null;
  busy: boolean;
  error: string | null;
  onAccept: () => void;
  /** Null once no length near this one has another walk. */
  onAnother: (() => void) | null;
  /** Which of the walks this card has shown is on screen; null while only one. */
  position: { at: number; of: number } | null;
  /** -1 back to the walk before, 1 on to the one after. */
  onSwipe: (dir: -1 | 1) => void;
  /** The asked length, when it had no walk and the card moved to the nearest. */
  emptyAt: number | null;
  onMap: () => void;
};

/** Sideways only, and only past a clear drag, so a tap or a scroll is left alone.
 *  Around the words, never the slider: its native drag would fight this one. */
function useSwipe(onSwipe: (dir: -1 | 1) => void) {
  const latest = useRef(onSwipe);
  latest.current = onSwipe;
  return useMemo(
    () =>
      PanResponder.create({
        onMoveShouldSetPanResponder: (_, g) => Math.abs(g.dx) > 24 && Math.abs(g.dx) > 2 * Math.abs(g.dy),
        onPanResponderRelease: (_, g) => {
          if (Math.abs(g.dx) > 60) latest.current(g.dx > 0 ? -1 : 1);
        },
      }).panHandlers,
    [],
  );
}

export function Preview({
  stops,
  meters,
  km,
  onKm,
  ask,
  onAsk,
  floorKm,
  onPickEnd,
  fallback,
  through,
  busy,
  error,
  onAccept,
  onAnother,
  position,
  onSwipe,
  emptyAt,
  onMap,
}: PreviewProps) {
  // Nothing before the first or after the last.
  const step = (dir: -1 | 1) => {
    if (position && position.at + dir >= 1 && position.at + dir <= position.of) onSwipe(dir);
  };
  const swipe = useSwipe(step);
  const found = stops != null && stops > 0;
  const short = found && meters < ROUTE_FILL * km * 1000;
  const unreachable = floorKm > WALK_KM.max;
  // Up to the slider's grid, so a floor of 2.3 km does not shift every step.
  const min = Math.min(Math.ceil(Math.max(WALK_KM.min, floorKm) / WALK_KM.step) * WALK_KM.step, WALK_KM.max);
  return (
    <View style={styles.card}>
      <View
        style={styles.summary}
        testID="walk-summary"
        {...(position ? swipe : {})}
      >
        <View style={[styles.titleRow, styles.besideClose]}>
          <Text style={[styles.cardTitle, styles.shrink]}>
            {through ? `A walk through ${through}` : 'A walk from here'}
          </Text>
          {/* The swipe for VoiceOver: on the count, not the whole zone, which
              would merge the lines under it into one label. */}
          {position && (
            <Text
              style={label}
              accessibilityRole="adjustable"
              accessibilityLabel="Walks shown"
              accessibilityValue={{ text: `${position.at} of ${position.of}` }}
              accessibilityActions={[{ name: 'decrement' }, { name: 'increment' }]}
              onAccessibilityAction={(e) => step(e.nativeEvent.actionName === 'decrement' ? -1 : 1)}
            >
              {`${position.at} of ${position.of}`}
            </Text>
          )}
        </View>
        <Text style={styles.cardBody}>
          {stops == null
            ? 'Finding a walk…'
            : stops === 0
              ? `No walk within ${WALK_KM.max} km from here.`
              : `${stops} ${stops === 1 ? 'stop' : 'stops'} · ${distance(meters)}${ask.loop ? ' loop' : ''}`}
        </Text>
        {found && emptyAt != null && (
          <Text style={styles.cardBody}>{`Nothing at ${emptyAt} km; this is the nearest.`}</Text>
        )}
        {position && (
          <Text style={label} accessibilityElementsHidden importantForAccessibility="no">
            ← swipe for others →
          </Text>
        )}
      </View>
      {short && <Text style={styles.cardBody}>That's the longest walk from here.</Text>}
      {fallback && (
        <Text style={styles.cardBody}>
          Planning from central Copenhagen. Turn on location to plan from where you are.
        </Text>
      )}
      {unreachable ? (
        <Text style={styles.cardBody}>{`The nearest walk from here is over ${WALK_KM.max} km.`}</Text>
      ) : (
        // Keyed, so a length the server lifted resets the label; never mid-drag,
        // since only a release changes km.
        <LengthSlider key={`${min}:${km}`} km={Math.max(km, min)} min={min} onKm={onKm} />
      )}
      <View style={styles.chips}>
        <Chip label="Loop" on={ask.loop} onPress={() => onAsk({ ...ask, loop: true, end: null })} />
        <Chip label="One way" on={!ask.loop} onPress={() => onAsk({ ...ask, loop: false })} />
        {/* A second tap lets the end go. */}
        {!ask.loop && (
          <Chip
            label={ask.end ? 'Ends where you tapped' : 'Pick where it ends'}
            on={!!ask.end}
            onPress={() => (ask.end ? onAsk({ ...ask, end: null }) : onPickEnd())}
          />
        )}
      </View>
      <Pressable
        style={dim(styles.primary)}
        onPress={onAccept}
        disabled={busy || !found}
        accessibilityRole="button"
        accessibilityLabel="Start this walk"
        accessibilityHint="You can end it any time."
      >
        {busy ? (
          <ActivityIndicator color={color.paper} />
        ) : (
          <Text style={styles.primaryText}>Start walk</Text>
        )}
      </Pressable>
      {/* Gone only when no length near this one has another walk either. */}
      {found && onAnother && (
        <Pressable
          style={dim(styles.secondary)}
          onPress={onAnother}
          disabled={busy}
          accessibilityRole="button"
          accessibilityLabel="Show me another"
        >
          <Text style={styles.secondaryText}>Show me another</Text>
        </Pressable>
      )}
      {error && <Text style={styles.error}>{error}</Text>}
      <CloseButton place={styles.close} onPress={onMap} disabled={busy} label="Back to the map" />
    </View>
  );
}

type WalkDoneProps = {
  stops: number;
  meters: number;
  loop: boolean;
  /** First unlock to last, or null when they were not all earned today. */
  minutes: number | null;
  streak: number;
  onDone: () => void;
};

type EndWalkProps = {
  /** Stops not reached yet: they lock again. */
  left: number;
  busy: boolean;
  error: string | null;
  onEnd: () => void;
  onKeep: () => void;
};

/** "Are you sure?" before a walk is ended with stops still to reach. A card,
 *  not a system dialog: this app never raises one of its own. */
export function EndWalk({ left, busy, error, onEnd, onKeep }: EndWalkProps) {
  return (
    <View style={styles.card} accessibilityViewIsModal>
      <Text style={styles.cardTitle} accessibilityRole="header">
        End this walk?
      </Text>
      <Text style={styles.cardBody}>
        {`${
          left === 1
            ? "The stop you haven't reached will lock again."
            : `The ${left} stops you haven't reached will lock again.`
        } Anything you've unlocked stays unlocked.`}
      </Text>
      <Pressable
        style={dim(styles.primary)}
        onPress={onEnd}
        disabled={busy}
        accessibilityRole="button"
        accessibilityLabel="End walk"
      >
        {busy ? (
          <ActivityIndicator color={color.paper} />
        ) : (
          <Text style={styles.primaryText}>End walk</Text>
        )}
      </Pressable>
      <Pressable
        style={dim(styles.secondary)}
        onPress={onKeep}
        disabled={busy}
        accessibilityRole="button"
        accessibilityLabel="Keep walking"
      >
        <Text style={styles.secondaryText}>Keep walking</Text>
      </Pressable>
      {error && <Text style={styles.error}>{error}</Text>}
    </View>
  );
}

/** The day's last card: the walk drawn whole behind it, and what it came to. */
export function WalkDone({ stops, meters, loop, minutes, streak, onDone }: WalkDoneProps) {
  const took =
    minutes === null
      ? ''
      : minutes < 60
        ? ` · ${minutes} min`
        : ` · ${Math.floor(minutes / 60)} h ${minutes % 60} min`;
  return (
    <View style={styles.card} accessibilityViewIsModal>
      <Text style={styles.doneTitle} accessibilityRole="header">
        Nice walk.
      </Text>
      <Text style={styles.cardBody}>
        {`${stops} ${stops === 1 ? 'memory' : 'memories'} · ${distance(meters)}${loop ? ' loop' : ''}${took}`}
      </Text>
      {streak > 1 && <Text style={label}>{`${streak} days in a row`}</Text>}
      <Pressable
        style={dim(styles.primary)}
        onPress={onDone}
        accessibilityRole="button"
        accessibilityLabel="Done"
      >
        <Text style={styles.primaryText}>Done</Text>
      </Pressable>
    </View>
  );
}

const styles = StyleSheet.create({
  value: { ...font.uiBold, fontSize: 22, color: color.ink, marginTop: 4 },
  slider: { height: 40 },
  ends: { flexDirection: 'row', justifyContent: 'space-between' },
  chips: { flexDirection: 'row', flexWrap: 'wrap', gap: 8, marginTop: 4 },
  primary: { ...button.solid, marginTop: 14 },
  primaryText: { ...buttonText, color: color.paper },
  secondary: button.quiet,
  secondaryText: { ...buttonText, color: color.ink },
  error: { ...font.prose, fontSize: 14, color: color.inkSoft, textAlign: 'center' },
  // Paper floating over the map: the card corner and the one shadow.
  card: {
    position: 'absolute',
    left: 16,
    right: 16,
    bottom: 26,
    backgroundColor: color.paperRaised,
    borderRadius: radius.card,
    padding: 24,
    gap: 10,
    ...lift,
  },
  cardTitle: { ...font.display, fontSize: 23, lineHeight: 30, color: color.ink },
  cardBody: { ...font.prose, fontSize: 16, lineHeight: 25, color: color.inkSoft },
  // Apple's close: top trailing on the card, on the title line (UI.md, rule 12).
  close: { position: 'absolute', top: 20, right: 20 },
  besideClose: { paddingRight: 36 },
  summary: { gap: 10 },
  shrink: { flexShrink: 1 },
  titleRow: { flexDirection: 'row', alignItems: 'baseline', justifyContent: 'space-between', gap: 8 },
  doneTitle: { ...font.display, fontSize: 34, lineHeight: 40, color: color.ink },
});
