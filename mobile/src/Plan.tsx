/** The first thing the app asks: how far today. Then the walk it would be, on
 *  the map, to accept or change. A walk can be ended any time and another
 *  planned (EndWalk); the preview is still the look before you commit.
 *
 *  It opens from the map's "Plan a walk" (F29) and goes back to it. From a
 *  pin's "Walk here" it plans a walk through that memory, and the slider
 *  starts at the shortest walk that reaches it. A one-way walk can end at a
 *  spot tapped on the map (EndPick), asked for per walk and stored nowhere.
 *
 *  The page is also the location primer. "Show me the walk" is a press, so the
 *  system dialog it may raise has the context the old card over the map gave
 *  it (UI.md, "Asking for location"). Refused, the walk is planned from
 *  central Copenhagen and the preview says so - never a dead end (rule 1).
 */

import Slider from '@react-native-community/slider';
import { ActivityIndicator, Pressable, StyleSheet, Text, View } from 'react-native';

import { SUBMISSION_TAGS, type WalkAsk } from './api.ts';
import { distance } from './format.ts';
import { Chip } from './Submit.tsx';
import { button, buttonText, color, dim, font, label } from './theme.ts';

export const WALK_KM = { min: 1, max: 10, step: 0.5, initial: 4 };

/** api/route_solver.py ROUTE_FILL: under this share of the ask, the map ran out. */
const ROUTE_FILL = 0.8;

type PlanProps = {
  km: number;
  onKm: (km: number) => void;
  ask: WalkAsk;
  onAsk: (ask: WalkAsk) => void;
  onGo: () => void;
  onBack: () => void;
  busy: boolean;
  error: string | null;
  /** "Walk here": the place every walk passes, or null. */
  through: string | null;
  /** The shortest walk that reaches it; over WALK_KM.max, none does. */
  floorKm: number;
  /** Go to the map to tap where a one-way walk ends. */
  onPickEnd: () => void;
};

export function Plan({
  km,
  onKm,
  ask,
  onAsk,
  onGo,
  onBack,
  busy,
  error,
  through,
  floorKm,
  onPickEnd,
}: PlanProps) {
  const unreachable = floorKm > WALK_KM.max;
  const min = Math.min(Math.max(WALK_KM.min, floorKm), WALK_KM.max);
  return (
    <View style={styles.page}>
      <Text style={styles.title}>How far today?</Text>
      <Text style={styles.value} accessibilityLiveRegion="polite">{`${km} km`}</Text>
      <Slider
        style={styles.slider}
        minimumValue={min}
        maximumValue={WALK_KM.max}
        step={WALK_KM.step}
        value={km}
        onValueChange={onKm}
        tapToSeek
        // The native component takes any ColorValue (RNCSliderNativeComponent.ts);
        // only the published typings say string.
        minimumTrackTintColor={color.ink as string}
        maximumTrackTintColor={color.rule as string}
        thumbTintColor={color.ink as string}
        accessibilityLabel="Walk length"
      />
      <View style={styles.ends}>
        <Text style={label}>{`${min} km`}</Text>
        <Text style={label}>{`${WALK_KM.max} km`}</Text>
      </View>
      <View style={styles.chips}>
        <Chip label="Loop" on={ask.loop} onPress={() => onAsk({ ...ask, loop: true, end: null })} />
        <Chip label="One way" on={!ask.loop} onPress={() => onAsk({ ...ask, loop: false })} />
      </View>
      {/* Like the theme: a second tap lets the end go. */}
      {!ask.loop && (
        <View style={styles.chips}>
          <Chip
            label={ask.end ? 'Ends where you tapped' : 'Pick where it ends'}
            on={!!ask.end}
            onPress={() => (ask.end ? onAsk({ ...ask, end: null }) : onPickEnd())}
          />
        </View>
      )}
      {/* One theme or none: a second tap on the chosen one lets it go. */}
      <View style={styles.chips}>
        {SUBMISSION_TAGS.map((tag) => (
          <Chip
            key={tag}
            label={tag}
            on={ask.tag === tag}
            onPress={() => onAsk({ ...ask, tag: ask.tag === tag ? null : tag })}
          />
        ))}
      </View>
      <Text style={styles.note}>
        {`Five${ask.tag ? ` ${ask.tag}` : ''} memories${through ? `, through ${through}` : ''}, ${
          ask.loop
            ? 'looping back to where you start'
            : ask.end
              ? 'ending where you tapped'
              : 'ending somewhere new'
        }.`}
      </Text>
      {unreachable && (
        <Text style={styles.note}>{`Too far for a walk from here: at least ${floorKm} km.`}</Text>
      )}

      <Pressable
        style={dim(styles.primary)}
        onPress={onGo}
        disabled={busy || unreachable}
        accessibilityRole="button"
        accessibilityLabel="Show me the walk"
      >
        {busy ? (
          <ActivityIndicator color={color.paper} />
        ) : (
          <Text style={styles.primaryText}>Show me the walk</Text>
        )}
      </Pressable>
      <Pressable
        style={dim(styles.secondary)}
        onPress={onBack}
        disabled={busy}
        accessibilityRole="button"
        accessibilityLabel="Back to the map"
      >
        <Text style={styles.secondaryText}>Back to the map</Text>
      </Pressable>
      {error && <Text style={styles.error}>{error}</Text>}
    </View>
  );
}

/** Over the map while it waits for the tap that says where the walk ends. */
export function EndPick({ onCancel }: { onCancel: () => void }) {
  return (
    <View style={styles.card} pointerEvents="box-none">
      <Text style={styles.cardTitle}>Where does it end?</Text>
      <Text style={styles.cardBody}>Tap the map where the walk should finish.</Text>
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
  stops: number;
  meters: number;
  /** What the slider asked for, in meters. */
  asked: number;
  loop: boolean;
  /** Planned from central Copenhagen because there was no position to plan from. */
  fallback: boolean;
  /** "Walk here": the place on every walk shown, or null. */
  through: string | null;
  busy: boolean;
  error: string | null;
  onAccept: () => void;
  /** Null once a re-roll came back with the same walk: it is the only one. */
  onAnother: (() => void) | null;
  onBack: () => void;
};

export function Preview({
  stops,
  meters,
  asked,
  loop,
  fallback,
  through,
  busy,
  error,
  onAccept,
  onAnother,
  onBack,
}: PreviewProps) {
  const short = stops > 0 && meters < ROUTE_FILL * asked;
  return (
    <View style={styles.card}>
      {stops === 0 ? (
        <Text style={styles.cardTitle}>No walk that long from here</Text>
      ) : (
        <Text style={styles.cardTitle}>
          {`${stops} ${stops === 1 ? 'stop' : 'stops'} · ${distance(meters)}${loop ? ' loop' : ''}`}
        </Text>
      )}
      {stops > 0 && through && <Text style={styles.cardBody}>{`Through ${through}.`}</Text>}
      {short && <Text style={styles.cardBody}>The longest from here.</Text>}
      {fallback && (
        <Text style={styles.cardBody}>
          Planning from central Copenhagen. Turn on location to plan from where you are.
        </Text>
      )}
      {stops > 0 && (
        <Pressable
          style={dim(styles.primary)}
          onPress={onAccept}
          disabled={busy}
          accessibilityRole="button"
          accessibilityLabel="Accept this walk"
          accessibilityHint="Starts this walk. You can end it any time."
        >
          {busy ? (
            <ActivityIndicator color={color.paper} />
          ) : (
            <Text style={styles.primaryText}>Accept</Text>
          )}
        </Pressable>
      )}
      {stops > 0 &&
        (onAnother ? (
          <Pressable
            style={dim(styles.secondary)}
            onPress={onAnother}
            disabled={busy}
            accessibilityRole="button"
            accessibilityLabel="Show me another"
          >
            <Text style={styles.secondaryText}>Show me another</Text>
          </Pressable>
        ) : (
          <Text style={styles.cardBody}>
            {short ? 'The only walk from here.' : 'The only walk that long from here.'}
          </Text>
        ))}
      <Pressable
        style={dim(styles.secondary)}
        onPress={onBack}
        disabled={busy}
        accessibilityRole="button"
        accessibilityLabel="Change length"
      >
        <Text style={styles.secondaryText}>Change length</Text>
      </Pressable>
      {error && <Text style={styles.error}>{error}</Text>}
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
            ? "The stop you haven't reached locks again."
            : `The ${left} stops you haven't reached lock again.`
        } What you opened stays yours.`}
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
        Walk done.
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
  page: {
    position: 'absolute',
    top: 0,
    right: 0,
    bottom: 0,
    left: 0,
    backgroundColor: color.paper,
    paddingHorizontal: 24,
    justifyContent: 'center',
    gap: 8,
  },
  title: { fontFamily: font.display, fontSize: 34, lineHeight: 40, color: color.ink },
  value: { fontFamily: font.monoBold, fontSize: 30, color: color.ink, marginTop: 16 },
  slider: { marginTop: 8, height: 40 },
  ends: { flexDirection: 'row', justifyContent: 'space-between' },
  chips: { flexDirection: 'row', flexWrap: 'wrap', gap: 8, marginTop: 16 },
  note: { fontFamily: font.prose, fontSize: 16, lineHeight: 25, color: color.inkSoft, marginTop: 16 },
  primary: { ...button.solid, marginTop: 14 },
  primaryText: { ...buttonText, color: color.paper },
  secondary: button.quiet,
  secondaryText: { ...buttonText, color: color.ink },
  error: { fontFamily: font.prose, fontSize: 14, color: color.inkSoft, textAlign: 'center' },
  // The primer card's shape and shadow, in its slot: UI.md allows that one.
  card: {
    position: 'absolute',
    left: 16,
    right: 16,
    bottom: 26,
    backgroundColor: color.paper,
    borderWidth: 1,
    borderColor: color.rule,
    borderRadius: 6,
    padding: 24,
    gap: 10,
    shadowColor: color.shadow,
    shadowOpacity: 0.14,
    shadowRadius: 18,
    shadowOffset: { width: 0, height: 8 },
    elevation: 6,
  },
  cardTitle: { fontFamily: font.display, fontSize: 23, lineHeight: 30, color: color.ink },
  cardBody: { fontFamily: font.prose, fontSize: 16, lineHeight: 25, color: color.inkSoft },
  doneTitle: { fontFamily: font.display, fontSize: 34, lineHeight: 40, color: color.ink },
});
