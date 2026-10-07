/** The planner, which is the home screen: a walk drawn on the map, and a
 *  card in two steps - the length and the shape, then what its memories are
 *  of, paged between walks, and Start. A third, Customize (themes and an era
 *  the walk leans towards), is a subscriber's (docs/10, "Subscribers shape
 *  the walk").
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
  Image,
  Animated,
  type LayoutChangeEvent,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  View,
} from 'react-native';

import type { Coordinates, LocatedMemory, Profile, WalkAsk, WalkedRoute } from './api.ts';
import Button from './Button.tsx';
import CloseButton from './CloseButton.tsx';
import { GlassCard } from './Glass.tsx';
import Glyph from './Glyph.tsx';
import { distance, walkDate } from './format.ts';
import { locketOf } from './lockets.ts';
import { ERAS } from './route.ts';
import { Chip } from './Submit.tsx';
import {
  button,
  buttonText,
  color,
  dim,
  foil,
  font,
  label,
  lift,
  metal,
  radius,
  screenTitle,
} from './theme.ts';
import { WalkShape } from './WalkCard.tsx';

export const WALK_KM = { min: 1, max: 10, step: 0.5, initial: 4 };

/** pipeline/tags.py TAGS, the vocabulary a walk can lean on; a test holds the
 *  two to the same list. Richest first (the corpus, 2026-10-07). */
export const THEMES = [
  'history',
  'culture',
  'strange',
  'personal',
  'drink',
  'art',
  'work',
  'comedy',
  'food',
  'business',
  'family',
  'music',
  'travel',
  'adventure',
  'nightlife',
  'sport',
  'nature',
  'romance',
];

const themeName = (theme: string) => theme[0].toUpperCase() + theme.slice(1);

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
      <View style={styles.lengthRow}>
        <Text style={label}>Length</Text>
        <Text style={styles.value} accessibilityLiveRegion="polite">{`${shown} km`}</Text>
      </View>
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
        thumbTintColor={metal.light}
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
      <Button kind="quiet" label="Cancel" onPress={onCancel} />
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
  /** Customizes the walk; a free walker is offered Plus instead. */
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
  /** Memories added within 2 km since your last walk (docs/10, "New since
   *  your last walk"). */
  newNearby: number;
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
  if (!onPress) return <View style={styles.arrowSpace} />;
  return (
    <Pressable
      style={dim(styles.arrow)}
      hitSlop={2}
      onPress={onPress}
      disabled={busy}
      accessibilityRole="button"
      accessibilityLabel={name}
    >
      <Glyph name={glyph} size={17} weight="semibold" color={color.ink} />
    </Pressable>
  );
}

/** One of the planner's three shapes: a segment of one capsule, the chosen
 *  one raised. */
function Mode({ label: text, on, onPress }: { label: string; on: boolean; onPress: () => void }) {
  return (
    <Pressable
      style={[styles.mode, on && styles.modeOn]}
      onPress={() => {
        Haptics.selectionAsync().catch(() => {});
        onPress();
      }}
      accessibilityRole="button"
      accessibilityState={{ selected: on }}
    >
      <Text style={[styles.modeText, on && styles.modeTextOn]} numberOfLines={1}>
        {text}
      </Text>
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
  newNearby,
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
        <Button
          kind="go"
          label="More walks"
          onPress={onSubscribe}
          testID="more-walks"
          place={styles.primary}
        />
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
    <Button
      kind="go"
      label="Start walk"
      onPress={onAccept}
      disabled={busy || !found}
      busy={busy}
      accessibilityLabel="Start this walk"
      accessibilityHint="You can end it any time."
      place={styles.primary}
    />
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
  const era = ERAS.find((e) => e.from === ask.from && e.until === ask.until) ?? ERAS[0];
  const customized = ask.themes.length > 0 || era !== ERAS[0];
  if (step === 'choices') {
    return (
      <GlassCard style={styles.card} onLayout={measure} testID="walk-choices">
        {back}
        <View style={styles.from}>
          <Text style={[styles.cardTitle, styles.grow]} accessibilityRole="header">
            Customize
          </Text>
          {customized && (
            <Pressable
              style={dim([styles.secondary, button.small])}
              onPress={() => onAsk({ ...ask, themes: [], from: null, until: null })}
              accessibilityRole="button"
              accessibilityHint="Clears the themes and the era"
            >
              <Text style={styles.secondaryText}>Clear</Text>
            </Pressable>
          )}
        </View>
        <Text style={styles.cardBody}>
          The walk leans towards these, and still fills up with the best nearby.
        </Text>
        <Text style={styles.section}>Themes</Text>
        <View style={styles.chips}>
          {THEMES.map((theme) => {
            const on = ask.themes.includes(theme);
            return (
              <Chip
                key={theme}
                label={themeName(theme)}
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
        <Text style={styles.section}>Era</Text>
        <View style={styles.chips}>
          {ERAS.map((e) => (
            <Chip
              key={e.label}
              label={e.label}
              on={e === era}
              onPress={() => onAsk({ ...ask, from: e.from, until: e.until })}
            />
          ))}
        </View>
        <Button
          kind="go"
          label={found ? `Done · ${count} ${count === 1 ? 'stop' : 'stops'}` : 'Done'}
          onPress={() => setStep(null)}
          busy={busy}
          place={styles.primary}
        />
        {close}
      </GlassCard>
    );
  }
  const chosen = [ask.themes.map(themeName).join(', '), era === ERAS[0] ? '' : era.label]
    .filter(Boolean)
    .join(' · ');
  return (
    <GlassCard style={styles.card} onLayout={measure}>
      {/* The arrows page through walks. A missing one keeps its space, so
          the title never shifts between walks. */}
      <View style={styles.pages}>
        <View style={styles.grow}>
          <Text style={styles.cardTitle}>A walk from here</Text>
          {found ? (
            <Text
              style={styles.cardBody}
            >{`${count} ${count === 1 ? 'memory' : 'memories'} · ${distance(meters)}${ask.loop ? ' loop' : ''}`}</Text>
          ) : (
            <Text style={styles.cardBody} testID={count === 0 ? 'no-walk' : undefined}>
              {count == null ? 'Finding a walk…' : `No walk within ${WALK_KM.max} km from here.`}
            </Text>
          )}
        </View>
        {found && (
          <>
            <Arrow glyph="chevron.left" name="Previous walk" onPress={onBack} busy={busy} />
            <Arrow glyph="chevron.right" name="Next walk" onPress={onNext} busy={busy} />
          </>
        )}
        <CloseButton label="Close the planner" onPress={onClose} />
      </View>
      {found && newNearby > 0 && (
        <Text style={styles.cardBody} testID="new-nearby">
          {`${newNearby} new ${newNearby === 1 ? 'story' : 'stories'} within 2 km since your last walk`}
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
      <View style={styles.modes}>
        <Mode label="Loop" on={ask.loop} onPress={() => onAsk({ ...ask, loop: true, end: null })} />
        <Mode
          label="One way"
          on={!ask.loop && !ask.end}
          onPress={() => onAsk({ ...ask, loop: false, end: null })}
        />
        {/* A second tap lets the end go. */}
        <Mode
          label={ask.end ? 'Ends where you tapped' : 'Pick where it ends'}
          on={!!ask.end}
          onPress={() => (ask.end ? onAsk({ ...ask, end: null }) : onPickEnd())}
        />
      </View>
      {/* A subscriber's, offered to a free walker: badged Plus, so it reads
          as the paywall before it is tapped. */}
      <Pressable
        style={dim(styles.themes)}
        onPress={subscribed ? () => setStep('choices') : onSubscribe}
        disabled={busy}
        accessibilityRole="button"
        accessibilityHint={subscribed ? undefined : 'Part of Plus'}
        testID={subscribed ? undefined : 'themes-plus'}
      >
        <Glyph name="slider.horizontal.3" size={18} weight="semibold" color={color.gold} />
        <Text style={styles.themesText} numberOfLines={1}>
          {(subscribed && chosen) || 'Customize'}
        </Text>
        {!subscribed && (
          <View style={styles.badge}>
            <Text style={styles.badgeText}>Plus</Text>
          </View>
        )}
        <Glyph name="chevron.right" size={14} weight="semibold" color={color.inkFaint} />
      </Pressable>
      <Button
        kind="go"
        label="Next"
        onPress={() => setStep('stops')}
        disabled={busy || !found}
        busy={busy}
        accessibilityHint="Shows the stops on this walk"
        place={styles.primary}
      />
      {error && <Text style={styles.error}>{error}</Text>}
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
  /** Where you stand now, for the level column. */
  level: number;
  into: number;
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
  /** Set until the surprise was chosen either way: asked here once, after a
   *  first walk, since nobody finds it in Settings (docs/10, "A surprise,
   *  once a week"). */
  onNotify?: (yes: boolean) => void;
};

export type Reward = {
  xp: number;
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
      {/* Ending is never the loud one: quiet, beside a green way on. */}
      <View style={styles.pair}>
        <Button
          kind="quiet"
          label="End walk"
          onPress={onEnd}
          disabled={busy}
          busy={busy}
          place={styles.grow}
        />
        <Button
          kind="go"
          label="Keep walking"
          onPress={onKeep}
          disabled={busy}
          place={styles.grow}
        />
      </View>
      {error && <Text style={styles.error}>{error}</Text>}
    </GlassCard>
  );
}

/** How far from this level's start to the next, 0 to 1. */
export function levelInto({ xp, xp_level, xp_next }: Profile): number {
  return Math.min(1, (xp - xp_level) / Math.max(1, xp_next - xp_level));
}

/** The day's last card: the walk drawn whole behind it, and what it came to. */
export function WalkDone({
  stops,
  meters,
  loop,
  minutes,
  streak,
  level,
  into,
  reward,
  path,
  onDone,
  onHeight,
  onMore,
  onNotify,
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
      {/* What you earned, in plum: this walk, where it leaves you, the streak. */}
      <View style={styles.stats}>
        {reward && (
          <View style={styles.stat}>
            <Text style={styles.statFigure}>{`+${reward.xp} XP`}</Text>
            <Text style={label}>This walk</Text>
          </View>
        )}
        <View style={[styles.stat, styles.statRuled]}>
          <Text style={[styles.statFigure, styles.statInk]}>{`Level ${level}`}</Text>
          <View style={styles.bar}>
            <View style={[styles.barFill, { width: `${into * 100}%` }]} />
          </View>
        </View>
        {streak > 0 && (
          <View style={[styles.stat, styles.statRuled]}>
            <Text style={styles.statFigure}>{`${streak} ${streak === 1 ? 'day' : 'days'}`}</Text>
            <Text style={label}>Streak</Text>
          </View>
        )}
      </View>
      {MILESTONES.includes(streak) && <Milestone streak={streak} />}
      {onNotify && (
        <View testID="surprise-ask">
          <Text style={styles.cardBody}>Let a story find you now and then?</Text>
          <View style={styles.pair}>
            <Button
              kind="quiet"
              label="Not now"
              onPress={() => onNotify(false)}
              place={styles.grow}
            />
            <Button kind="go" label="Yes" onPress={() => onNotify(true)} place={styles.grow} />
          </View>
        </View>
      )}
      <Button kind="foil" label="Done" onPress={onDone} place={styles.primary} />
      {onMore && (
        <Button kind="text" label="Another walk today ›" onPress={onMore} testID="walk-done-more" />
      )}
    </GlassCard>
  );
}

// Quiet by default, loud only here: an ordinary day's streak is one line.
const MILESTONES = [7, 30, 100];

/** A streak milestone's own moment on the finish card: it springs in with a
 *  flame and a second success haptic. Still, under Reduce Motion. */
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
      <Glyph name="flame.fill" size={22} color={color.plum} bounce={streak} />
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
      <Text style={label}>A walk you took</Text>
      <Text style={styles.doneTitle} accessibilityRole="header" testID="past-walk">
        {walkDate(walk.route_date)}
      </Text>
      <View style={styles.checks}>
        {Array.from({ length: Math.min(walk.earned, 10) }, (_, i) => (
          <View key={i} style={styles.check}>
            <Glyph name="checkmark" size={10} weight="bold" color={color.paper} />
          </View>
        ))}
        <Text style={styles.cardBody}>
          {`${walk.earned} ${walk.earned === 1 ? 'memory' : 'memories'} · ${distance(walk.budget_meters)}`}
        </Text>
      </View>
      <Button kind="quiet" label="Done" onPress={onDone} place={styles.primary} />
    </GlassCard>
  );
}

const styles = StyleSheet.create({
  locket: { width: 13, height: 13 },
  checks: { flexDirection: 'row', alignItems: 'center', gap: 6, flexWrap: 'wrap' },
  check: {
    width: 20,
    height: 20,
    borderRadius: 10,
    backgroundColor: color.gold,
    alignItems: 'center',
    justifyContent: 'center',
  },
  stats: {
    flexDirection: 'row',
    paddingVertical: 14,
    borderTopWidth: StyleSheet.hairlineWidth,
    borderBottomWidth: StyleSheet.hairlineWidth,
    borderColor: color.rule,
  },
  stat: { flex: 1, gap: 4, paddingHorizontal: 10 },
  statRuled: { borderLeftWidth: StyleSheet.hairlineWidth, borderColor: color.rule },
  statFigure: { ...font.title, fontSize: 24, lineHeight: 30, color: color.plum },
  statInk: { color: color.ink },
  bar: { height: 6, borderRadius: 3, backgroundColor: color.track, overflow: 'hidden' },
  barFill: { height: 6, borderRadius: 3, backgroundColor: color.plum },
  doneTop: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' },
  milestone: { flexDirection: 'row', alignItems: 'center', gap: 8, alignSelf: 'flex-start' },
  milestoneText: { ...font.uiBold, fontSize: 18, color: color.ink },
  value: { ...font.title, fontSize: 30, lineHeight: 34, color: color.ink },
  lengthRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'flex-end',
    marginTop: 6,
  },
  modes: {
    flexDirection: 'row',
    padding: 4,
    borderRadius: radius.pill,
    backgroundColor: color.quiet,
    borderWidth: 1,
    borderColor: color.quietEdge,
  },
  mode: {
    flexGrow: 1,
    minHeight: 40,
    paddingHorizontal: 12,
    borderRadius: radius.pill,
    alignItems: 'center',
    justifyContent: 'center',
  },
  modeOn: { backgroundColor: color.paperRaised, ...lift, shadowOpacity: 0.08 },
  modeText: { ...font.uiMedium, fontSize: 15, color: color.inkSoft },
  modeTextOn: { ...font.uiBold, color: color.ink },
  themes: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 12,
    minHeight: 52,
    borderTopWidth: StyleSheet.hairlineWidth,
    borderBottomWidth: StyleSheet.hairlineWidth,
    borderColor: color.rule,
    marginTop: 6,
  },
  themesText: { ...font.uiMedium, flex: 1, fontSize: 17, color: color.ink },
  section: { ...font.uiBold, fontSize: 13, color: color.inkSoft, marginTop: 6 },
  slider: { height: 40 },
  ends: { flexDirection: 'row', justifyContent: 'space-between' },
  chips: { flexDirection: 'row', flexWrap: 'wrap', gap: 8, marginTop: 4 },
  primary: { marginTop: 14 },
  pair: { flexDirection: 'row', gap: 12, marginTop: 14 },
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
  cardTitle: { ...screenTitle, fontSize: 28, lineHeight: 32 },
  cardBody: { ...font.prose, fontSize: 16, lineHeight: 25, color: color.inkSoft },
  from: { flexDirection: 'row', alignItems: 'center', gap: 12 },
  grow: { flex: 1 },
  badge: {
    backgroundColor: metal.light,
    borderRadius: radius.pill,
    paddingHorizontal: 7,
    paddingVertical: 2,
  },
  badgeText: { ...font.uiBold, fontSize: 13, color: foil.text },
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
  pages: { flexDirection: 'row', alignItems: 'flex-start', gap: 8, paddingRight: 0 },
  // 40pt drawn; hitSlop takes it to Apple's 44.
  arrowSpace: { width: 40 },
  arrow: {
    width: 40,
    height: 40,
    borderRadius: 20,
    backgroundColor: color.quiet,
    borderWidth: 1,
    borderColor: color.quietEdge,
    alignItems: 'center',
    justifyContent: 'center',
  },
  doneTitle: screenTitle,
});
