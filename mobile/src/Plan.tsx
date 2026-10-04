/** The planner, which is the home screen: a walk drawn on the map, and a
 *  card in two steps - the length and the shape, then what its memories are
 *  of, paged between walks, and Start. A third, for themes and years, is a
 *  subscriber's (docs/10, "Subscribers shape the walk").
 *  Any change redraws the walk; ‹ › trade it for another. A one-way walk can
 *  end at a spot tapped on the map (EndPick), asked for per walk and stored
 *  nowhere. docs/10, "A walk planner, nothing else" and "Draw first, adjust
 *  after".
 *
 *  Opening it is the location ask: the card under the dialog says why
 *  (UI.md, "Asking for location").
 *  Refused, the walk is planned from central Copenhagen and the card says so -
 *  never a dead end (rule 1).
 */

import Slider from '@react-native-community/slider';
import * as Haptics from 'expo-haptics';
import { useEffect, useRef, useState } from 'react';
import {
  AccessibilityInfo,
  ActivityIndicator,
  Image,
  Animated,
  type LayoutChangeEvent,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  View,
} from 'react-native';

import type { Coordinates, LocatedMemory, WalkAsk, WalkedRoute } from './api.ts';
import CloseButton from './CloseButton.tsx';
import { GlassCard } from './Glass.tsx';
import Glyph from './Glyph.tsx';
import { distance, walkDate } from './format.ts';
import { locketAt, locketOf } from './lockets.ts';
import { Chip } from './Submit.tsx';
import { button, buttonText, color, dim, font, label, radius } from './theme.ts';
import { WalkShape } from './WalkCard.tsx';

export const WALK_KM = { min: 1, max: 10, step: 0.5, initial: 4 };

/** pipeline/tags.py TAGS, the vocabulary a walk can lean on; a test holds the
 *  two to the same list. */
export const THEMES = [
  'personal',
  'travel',
  'business',
  'nightlife',
  'culture',
  'adventure',
  'comedy',
  'food',
  'drink',
  'nature',
  'music',
  'art',
  'history',
  'sport',
  'romance',
  'family',
  'work',
  'strange',
];

/** Where a range of years can start and end; null is either way open. */
const FROM_YEARS = [null, 1600, 1700, 1800, 1900, 1950, 2000];
const UNTIL_YEARS = [1700, 1800, 1900, 1950, 2000, null];

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
        minimumTrackTintColor={color.gold as string}
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
    <GlassCard style={styles.card} pointerEvents="box-none">
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
    </GlassCard>
  );
}

type PreviewProps = {
  /** In walk order, locked: what each is of, never what it says. Null until
   *  the first walk comes back. */
  stops: LocatedMemory[] | null;
  meters: number;
  /** What the slider asked for. */
  km: number;
  onKm: (km: number) => void;
  ask: WalkAsk;
  onAsk: (ask: WalkAsk) => void;
  /** Picks themes and years. */
  subscribed: boolean;
  /** The shortest walk that reaches the pin and the end; over WALK_KM.max, none does. */
  floorKm: number;
  /** Go to the map to tap where a one-way walk ends. */
  onPickEnd: () => void;
  /** Planned from central Copenhagen because there was no position to plan from. */
  fallback: boolean;
  /** The location ask, a press with a reason; then the walk is planned again. */
  onLocate: () => void;
  busy: boolean;
  error: string | null;
  onAccept: () => void;
  /** On through the walks stepped back past, then a new one. Null on the last:
   *  no length near this one has another walk. */
  onNext: (() => void) | null;
  /** Back to the walk shown before this one; null on the first. */
  onBack: (() => void) | null;
  /** Which walk this is, counting from the first: said to VoiceOver. */
  walkNumber: number;
  /** The asked length, when it had no walk and the card moved to the nearest. */
  emptyAt: number | null;
  /** Today's free walk is walked: the card offers the subscription instead. */
  walkedOut: boolean;
  onSubscribe: () => void;
  /** The card's height, so the map fits the walk into what is left above it. */
  onHeight: (height: number) => void;
  /** Back to the map, from any step. */
  onClose: () => void;
};

/** One side of the pages; null keeps the side's space empty. */
type ArrowProps = {
  glyph: 'chevron.left' | 'chevron.right';
  name: string;
  onPress: (() => void) | null;
  busy: boolean;
};

function Arrow({ glyph, name, onPress, busy }: ArrowProps) {
  if (!onPress) return <View style={styles.arrow} />;
  return (
    <Pressable
      style={dim(styles.arrow)}
      onPress={onPress}
      disabled={busy}
      accessibilityRole="button"
      accessibilityLabel={name}
    >
      <Glyph name={glyph} size={24} weight="semibold" color={color.ink} />
    </Pressable>
  );
}

export function Preview({
  stops,
  meters,
  km,
  onKm,
  ask,
  onAsk,
  subscribed,
  floorKm,
  onPickEnd,
  fallback,
  onLocate,
  busy,
  error,
  onAccept,
  onNext,
  onBack,
  walkNumber,
  emptyAt,
  walkedOut,
  onSubscribe,
  onHeight,
  onClose,
}: PreviewProps) {
  // Two steps: the length and the shape with the walk drawn behind, then its
  // stops, paged between walks, and Start.
  const [step, setStep] = useState<'stops' | 'choices' | null>(null);
  // Said, not focused: the arrows keep VoiceOver where it is (WAI carousels).
  const stepped = useRef(false);
  useEffect(() => {
    if (stepped.current) AccessibilityInfo.announceForAccessibility(`Walk ${walkNumber}`);
    stepped.current = true;
  }, [walkNumber]);
  const close = <CloseButton label="Close the planner" onPress={onClose} place={styles.close} />;
  if (walkedOut) {
    return (
      <GlassCard style={styles.card}>
        <Text style={styles.cardTitle}>Today's walk is done</Text>
        <Text style={styles.cardBody}>
          There's another tomorrow. Or subscribe for as many as you like.
        </Text>
        <Pressable
          style={dim(styles.primary)}
          onPress={onSubscribe}
          accessibilityRole="button"
          testID="more-walks"
        >
          <Text style={styles.primaryText}>More walks</Text>
        </Pressable>
        {close}
      </GlassCard>
    );
  }
  const count = stops?.length ?? null;
  const found = count != null && count > 0;
  const short = found && meters < ROUTE_FILL * km * 1000;
  const unreachable = floorKm > WALK_KM.max;
  // Up to the slider's grid, so a floor of 2.3 km does not shift every step.
  const min = Math.min(
    Math.ceil(Math.max(WALK_KM.min, floorKm) / WALK_KM.step) * WALK_KM.step,
    WALK_KM.max,
  );
  const measure = (e: LayoutChangeEvent) => onHeight(e.nativeEvent.layout.height);
  const back = (
    <Pressable
      style={dim(styles.back)}
      onPress={() => setStep(null)}
      accessibilityRole="button"
      accessibilityLabel="Back to the length"
    >
      <Glyph name="chevron.left" size={17} weight="semibold" color={color.ink} />
      <Text style={styles.secondaryText}>Back</Text>
    </Pressable>
  );
  const start = (
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
  );
  if (step === 'stops' && found && stops) {
    return (
      <GlassCard style={styles.card} onLayout={measure}>
        {back}
        <Stops stops={stops} />
        {start}
        {error && <Text style={styles.error}>{error}</Text>}
        {close}
      </GlassCard>
    );
  }
  if (step === 'choices') {
    const until = UNTIL_YEARS.filter((year) => year == null || ask.from == null || year > ask.from);
    return (
      <GlassCard style={styles.card} onLayout={measure} testID="walk-choices">
        {back}
        <Text style={styles.cardBody}>Lean the walk towards</Text>
        <View style={styles.chips}>
          {THEMES.map((theme) => {
            const on = ask.themes.includes(theme);
            return (
              <Chip
                key={theme}
                label={`#${theme}`}
                on={on}
                onPress={() =>
                  onAsk({
                    ...ask,
                    themes: on ? ask.themes.filter((t) => t !== theme) : [...ask.themes, theme],
                  })
                }
              />
            );
          })}
        </View>
        <Text style={styles.cardBody}>Memories from</Text>
        <View style={styles.chips}>
          {FROM_YEARS.map((year) => (
            <Chip
              key={`from-${year}`}
              label={year == null ? 'Any year' : String(year)}
              on={ask.from === year}
              onPress={() =>
                onAsk({
                  ...ask,
                  from: year,
                  until: year != null && ask.until != null && ask.until <= year ? null : ask.until,
                })
              }
            />
          ))}
        </View>
        <Text style={styles.cardBody}>Until</Text>
        <View style={styles.chips}>
          {until.map((year) => (
            <Chip
              key={`until-${year}`}
              label={year == null ? 'Now' : String(year)}
              on={ask.until === year}
              onPress={() => onAsk({ ...ask, until: year })}
            />
          ))}
        </View>
        {close}
      </GlassCard>
    );
  }
  const chosen = [
    ...ask.themes.map((t) => `#${t}`),
    ask.from != null || ask.until != null ? `${ask.from ?? '…'}–${ask.until ?? 'now'}` : '',
  ]
    .filter(Boolean)
    .join(' ');
  return (
    <GlassCard style={styles.card} onLayout={measure}>
      <Text style={styles.cardTitle}>A walk from here</Text>
      {found ? (
        // Pages: the arrows flank what they change. A missing one keeps its
        // space, so the line never shifts between walks.
        <View style={styles.pages}>
          <Arrow glyph="chevron.left" name="Previous walk" onPress={onBack} busy={busy} />
          <Text
            style={[styles.cardBody, styles.paged]}
          >{`${count} ${count === 1 ? 'memory' : 'memories'} · ${distance(meters)}${ask.loop ? ' loop' : ''}`}</Text>
          <Arrow glyph="chevron.right" name="Next walk" onPress={onNext} busy={busy} />
        </View>
      ) : (
        <Text style={styles.cardBody} testID={count === 0 ? 'no-walk' : undefined}>
          {count == null ? 'Finding a walk…' : `No walk within ${WALK_KM.max} km from here.`}
        </Text>
      )}
      {found && emptyAt != null && (
        <Text style={styles.cardBody}>{`Nothing at ${emptyAt} km; this is the nearest.`}</Text>
      )}
      {short && (
        <Text style={styles.cardBody} testID="longest-walk">
          That's the longest walk from here.
        </Text>
      )}
      {fallback && (
        <View style={styles.from}>
          <Text style={[styles.cardBody, styles.grow]} testID="planning-from-centre">
            Planning from central Copenhagen.
          </Text>
          <Pressable
            style={dim([styles.secondary, button.small])}
            onPress={onLocate}
            accessibilityRole="button"
            accessibilityHint="Plans the walk from where you are"
          >
            <Text style={styles.secondaryText}>Use my location</Text>
          </Pressable>
        </View>
      )}
      {unreachable ? (
        <Text
          style={styles.cardBody}
        >{`The nearest walk from here is over ${WALK_KM.max} km.`}</Text>
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
        onPress={() => setStep('stops')}
        disabled={busy || !found}
        accessibilityRole="button"
        accessibilityHint="Shows the stops on this walk"
      >
        {busy ? (
          <ActivityIndicator color={color.paper} />
        ) : (
          <Text style={styles.primaryText}>Next</Text>
        )}
      </Pressable>
      {subscribed ? (
        <Pressable
          style={dim([styles.secondary, styles.extra])}
          onPress={() => setStep('choices')}
          disabled={busy}
          accessibilityRole="button"
        >
          <Text style={styles.secondaryText} numberOfLines={1}>
            {chosen || 'Themes and years'}
          </Text>
        </Pressable>
      ) : (
        // A subscriber's, offered: gold, padlocked and badged, so it reads as
        // the paywall before it is tapped.
        <Pressable
          style={dim([styles.secondary, styles.extra, styles.plus])}
          onPress={onSubscribe}
          disabled={busy}
          accessibilityRole="button"
          accessibilityHint="Part of PLUS"
          testID="themes-plus"
        >
          <Glyph name="lock.fill" size={14} weight="semibold" color={color.gold} />
          <Text style={styles.secondaryText} numberOfLines={1}>
            Themes and years
          </Text>
          <View style={styles.badge}>
            <Text style={styles.badgeText}>PLUS</Text>
          </View>
        </Pressable>
      )}
      {error && <Text style={styles.error}>{error}</Text>}
      {close}
    </GlassCard>
  );
}

/** What the walk passes, in order: the place, when, whose story, a tag or
 *  two. All of it is on a locked memory already (api/gate.py locked_memory). */
function Stops({ stops }: { stops: LocatedMemory[] }) {
  return (
    <ScrollView style={styles.stops} testID="walk-stops">
      {stops.map((memory, i) => {
        const about = [
          memory.year,
          memory.source_name,
          memory.tags
            .slice(0, 2)
            .map((tag) => `#${tag}`)
            .join(' '),
        ]
          .filter(Boolean)
          .join(' · ');
        return (
          <View
            key={memory.id}
            style={styles.stop}
            accessible
            accessibilityLabel={`Stop ${i + 1}, ${memory.place.name}. ${about}`}
          >
            <View style={styles.number}>
              <Text style={styles.numberText}>{i + 1}</Text>
            </View>
            <View style={styles.stopText}>
              <Text style={styles.stopName} numberOfLines={1}>
                {memory.place.name}
              </Text>
              {about !== '' && (
                <Text style={label} numberOfLines={1}>
                  {about}
                </Text>
              )}
            </View>
            <Image source={locketOf(memory.locket).locked} style={styles.locket} />
          </View>
        );
      })}
    </ScrollView>
  );
}

type WalkDoneProps = {
  stops: number;
  meters: number;
  loop: boolean;
  /** First unlock to last, or null when they were not all earned today. */
  minutes: number | null;
  streak: number;
  /** What finishing earned, once the profile is back; null for a
   *  subscriber's second walk of the day, which earns nothing. */
  reward: Reward | null;
  /** The walk drawn whole, for the card it becomes in Your walks. */
  path: Coordinates[];
  onDone: () => void;
  /** The card as measured, so the map's fit clears it. */
  onHeight: (height: number) => void;
  /** The paywall, for a signed-in account without a subscription; unset
   *  hides the link. Never a pop-up: Done stays the one tap. */
  onMore?: () => void;
};

export type Reward = {
  xp: number;
  /** The level reached, when this walk reached one. */
  level: number | null;
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
    <GlassCard style={styles.card} accessibilityViewIsModal>
      <Text style={styles.cardTitle} accessibilityRole="header">
        End this walk?
      </Text>
      <Text style={styles.cardBody} testID="end-walk-warning">
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
    </GlassCard>
  );
}

/** The day's last card: the walk drawn whole behind it, and what it came to. */
export function WalkDone({
  stops,
  meters,
  loop,
  minutes,
  streak,
  reward,
  path,
  onDone,
  onHeight,
  onMore,
}: WalkDoneProps) {
  const took =
    minutes === null
      ? ''
      : minutes < 60
        ? ` · ${minutes} min`
        : ` · ${Math.floor(minutes / 60)} h ${minutes % 60} min`;
  return (
    <GlassCard
      style={styles.card}
      accessibilityViewIsModal
      onLayout={(e) => onHeight(e.nativeEvent.layout.height)}
    >
      <View style={styles.doneTop}>
        <Text style={styles.doneTitle} accessibilityRole="header" testID="walk-done">
          Nice walk.
        </Text>
        <WalkShape path={path} size={56} />
      </View>
      <Text style={styles.cardBody}>
        {`${stops} ${stops === 1 ? 'memory' : 'memories'} · ${distance(meters)}${loop ? ' loop' : ''}${took}`}
      </Text>
      {reward && <Text style={label}>{`+${reward.xp} XP`}</Text>}
      {reward?.level && <Text style={label}>{`Level ${reward.level}`}</Text>}
      {reward?.level && <Earned level={reward.level} />}
      {MILESTONES.includes(streak) ? (
        <Milestone streak={streak} />
      ) : (
        streak > 1 && <Text style={label}>{`${streak} days in a row`}</Text>
      )}
      <Pressable
        style={dim(styles.primary)}
        onPress={onDone}
        accessibilityRole="button"
        accessibilityLabel="Done"
      >
        <Text style={styles.primaryText}>Done</Text>
      </Pressable>
      {onMore && (
        <Pressable
          style={dim(styles.secondary)}
          onPress={onMore}
          accessibilityRole="button"
          testID="walk-done-more"
        >
          <Text style={styles.secondaryText}>Another walk today ›</Text>
        </Pressable>
      )}
    </GlassCard>
  );
}

// Quiet by default, loud only here: an ordinary day's streak is one line.
const MILESTONES = [7, 30, 100];

/** A streak milestone's own moment on the finish card: it springs in with a
 *  flame and a second success haptic. Still, under Reduce Motion. */
/** A level that brings a locket shows it: the reward is the thing itself. */
function Earned({ level }: { level: number }) {
  const locket = locketAt(level);
  if (!locket) return null;
  return (
    <View style={styles.earned}>
      <Image source={locket.opened} style={styles.earnedLocket} />
      <Text style={label}>{`New locket: ${locket.name}`}</Text>
    </View>
  );
}

function Milestone({ streak }: { streak: number }) {
  const scale = useRef(new Animated.Value(0.8)).current;
  useEffect(() => {
    Haptics.notificationAsync(Haptics.NotificationFeedbackType.Success).catch(() => {});
    AccessibilityInfo.isReduceMotionEnabled().then((still) => {
      if (still) scale.setValue(1);
      else
        Animated.spring(scale, {
          toValue: 1,
          speed: 8,
          bounciness: 14,
          useNativeDriver: true,
        }).start();
    });
  }, [scale]);
  return (
    <Animated.View style={[styles.milestone, { transform: [{ scale }] }]} testID="streak-milestone">
      <Glyph name="flame.fill" size={22} color={color.purple} bounce={streak} />
      <Text style={styles.milestoneText}>{`${streak} days in a row`}</Text>
    </Animated.View>
  );
}

/** A past walk, drawn on the map behind it: when, and what it came to.
 *  Opened from its card in Your walks. */
export function PastWalk({
  walk,
  onDone,
  onHeight,
}: {
  walk: WalkedRoute;
  onDone: () => void;
  onHeight: (height: number) => void;
}) {
  return (
    <GlassCard style={styles.card} onLayout={(e) => onHeight(e.nativeEvent.layout.height)}>
      <Text style={styles.cardTitle} accessibilityRole="header" testID="past-walk">
        {walkDate(walk.route_date)}
      </Text>
      <Text style={styles.cardBody}>
        {`${walk.earned} ${walk.earned === 1 ? 'memory' : 'memories'} · ${distance(walk.budget_meters)}`}
      </Text>
      <Pressable
        style={dim(styles.primary)}
        onPress={onDone}
        accessibilityRole="button"
        accessibilityLabel="Done"
      >
        <Text style={styles.primaryText}>Done</Text>
      </Pressable>
    </GlassCard>
  );
}

const styles = StyleSheet.create({
  locket: { width: 13, height: 13 },
  earned: { flexDirection: 'row', alignItems: 'center', gap: 8 },
  earnedLocket: { width: 40, height: 40 },
  doneTop: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' },
  milestone: { flexDirection: 'row', alignItems: 'center', gap: 8, alignSelf: 'flex-start' },
  milestoneText: { ...font.uiBold, fontSize: 18, color: color.ink },
  value: { ...font.uiBold, fontSize: 22, color: color.ink, marginTop: 4 },
  slider: { height: 40 },
  ends: { flexDirection: 'row', justifyContent: 'space-between' },
  chips: { flexDirection: 'row', flexWrap: 'wrap', gap: 8, marginTop: 4 },
  primary: { ...button.solid, marginTop: 14 },
  primaryText: { ...buttonText, color: color.paper },
  secondary: button.quiet,
  secondaryText: { ...buttonText, color: color.ink },
  error: { ...font.prose, fontSize: 14, color: color.inkSoft, textAlign: 'center' },
  card: {
    position: 'absolute',
    left: 16,
    right: 16,
    bottom: 26,
    padding: 24,
    gap: 10,
  },
  close: { position: 'absolute', top: 16, right: 16 },
  cardTitle: { ...font.display, fontSize: 23, lineHeight: 30, color: color.ink },
  cardBody: { ...font.prose, fontSize: 16, lineHeight: 25, color: color.inkSoft },
  from: { flexDirection: 'row', alignItems: 'center', gap: 12 },
  grow: { flex: 1 },
  extra: {
    ...button.small,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 8,
  },
  plus: { backgroundColor: color.goldTint },
  badge: {
    backgroundColor: color.gold,
    borderRadius: radius.pill,
    paddingHorizontal: 7,
    paddingVertical: 2,
  },
  badgeText: { ...font.uiBold, fontSize: 11, letterSpacing: 0.6, color: color.paper },
  // Four rows in view, the rest a scroll away: the map behind still shows the walk.
  stops: { maxHeight: 4 * 52, flexGrow: 0 },
  stop: { flexDirection: 'row', alignItems: 'center', gap: 12, height: 52 },
  number: {
    width: 26,
    height: 26,
    borderRadius: 13,
    backgroundColor: color.gold,
    alignItems: 'center',
    justifyContent: 'center',
  },
  numberText: { ...font.uiBold, fontSize: 13, color: color.paper },
  stopText: { flex: 1, gap: 2 },
  stopName: { ...font.uiBold, fontSize: 16, color: color.ink },
  back: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 4,
    alignSelf: 'flex-start',
    minHeight: 44,
    marginTop: -10,
  },
  pages: { flexDirection: 'row', alignItems: 'center' },
  paged: { flex: 1, textAlign: 'center' },
  // 44pt, Apple's smallest hit target.
  arrow: { width: 44, height: 44, alignItems: 'center', justifyContent: 'center' },
  doneTitle: { ...font.display, fontSize: 34, lineHeight: 40, color: color.ink },
});
