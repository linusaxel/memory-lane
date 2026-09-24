/** The first thing the app asks: how far today. Then the walk it would be, on
 *  the map, to accept or change. One walk a day - accepting is final until
 *  tomorrow, which is why the preview exists at all.
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
import { buttonText, color, dim, font, label } from './theme.ts';

export const WALK_KM = { min: 1, max: 10, step: 0.5, initial: 4 };

type PlanProps = {
  km: number;
  onKm: (km: number) => void;
  ask: WalkAsk;
  onAsk: (ask: WalkAsk) => void;
  onGo: () => void;
  busy: boolean;
  error: string | null;
};

export function Plan({ km, onKm, ask, onAsk, onGo, busy, error }: PlanProps) {
  return (
    <View style={styles.page}>
      <Text style={styles.title}>How far today?</Text>
      <Text style={styles.value} accessibilityLiveRegion="polite">{`${km} km`}</Text>
      <Slider
        style={styles.slider}
        minimumValue={WALK_KM.min}
        maximumValue={WALK_KM.max}
        step={WALK_KM.step}
        value={km}
        onValueChange={onKm}
        // The native component takes any ColorValue (RNCSliderNativeComponent.ts);
        // only the published typings say string.
        minimumTrackTintColor={color.ink as string}
        maximumTrackTintColor={color.rule as string}
        thumbTintColor={color.ink as string}
        accessibilityLabel="Walk length"
      />
      <View style={styles.ends}>
        <Text style={label}>{`${WALK_KM.min} km`}</Text>
        <Text style={label}>{`${WALK_KM.max} km`}</Text>
      </View>
      <View style={styles.chips}>
        <Chip label="Loop" on={ask.loop} onPress={() => onAsk({ ...ask, loop: true })} />
        <Chip label="One way" on={!ask.loop} onPress={() => onAsk({ ...ask, loop: false })} />
      </View>
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
        {`Five${ask.tag ? ` ${ask.tag}` : ''} memories, ${
          ask.loop ? 'looping back to where you start' : 'ending somewhere new'
        }.`}
      </Text>

      <Pressable
        style={dim(styles.primary)}
        onPress={onGo}
        disabled={busy}
        accessibilityRole="button"
        accessibilityLabel="Show me the walk"
      >
        {busy ? (
          <ActivityIndicator color={color.paper} />
        ) : (
          <Text style={styles.primaryText}>Show me the walk</Text>
        )}
      </Pressable>
      {error && <Text style={styles.error}>{error}</Text>}
    </View>
  );
}

type PreviewProps = {
  stops: number;
  meters: number;
  loop: boolean;
  /** Planned from central Copenhagen because there was no position to plan from. */
  fallback: boolean;
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
  loop,
  fallback,
  busy,
  error,
  onAccept,
  onAnother,
  onBack,
}: PreviewProps) {
  return (
    <View style={styles.card}>
      {stops === 0 ? (
        <Text style={styles.cardTitle}>No walk that long from here</Text>
      ) : (
        <Text style={styles.cardTitle}>
          {`${stops} ${stops === 1 ? 'stop' : 'stops'} · ${distance(meters)}${loop ? ' loop' : ''}`}
        </Text>
      )}
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
          accessibilityHint="This is today's walk. It can't be changed until tomorrow."
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
          <Text style={styles.cardBody}>The only walk that long from here.</Text>
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
  primary: {
    marginTop: 14,
    backgroundColor: color.ink,
    paddingVertical: 16,
    borderRadius: 4,
    alignItems: 'center',
  },
  primaryText: { ...buttonText, color: color.paper },
  secondary: {
    borderWidth: 1,
    borderColor: color.rule,
    paddingVertical: 14,
    borderRadius: 4,
    alignItems: 'center',
  },
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
    shadowColor: '#000',
    shadowOpacity: 0.14,
    shadowRadius: 18,
    shadowOffset: { width: 0, height: 8 },
    elevation: 6,
  },
  cardTitle: { fontFamily: font.display, fontSize: 23, lineHeight: 30, color: color.ink },
  cardBody: { fontFamily: font.prose, fontSize: 16, lineHeight: 25, color: color.inkSoft },
  doneTitle: { fontFamily: font.display, fontSize: 34, lineHeight: 40, color: color.ink },
});
