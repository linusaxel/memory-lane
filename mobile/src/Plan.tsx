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
  type LayoutChangeEvent,
  PanResponder,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  View,
} from 'react-native';

import { classOf, rankInto, wants, wantsWords, type ClassId } from './collector.ts';
import type { Coordinates, LocatedMemory, WalkAsk, WalkedRoute } from './api.ts';
import Button from './Button.tsx';
import CloseButton from './CloseButton.tsx';
import { GlassCard } from './Glass.tsx';
import Glyph from './Glyph.tsx';
import Icon from './Icon.tsx';
import { ERA_STOPS, distance, eraLabel, eraSpan, eraStops, walkDate } from './format.ts';
import { clamp } from './lockets/math.ts';
import { locketOf } from './lockets.ts';
import { Chip } from './Submit.tsx';
import {
  button,
  buttonText,
  color,
  dim,
  foil,
  font,
  label,
  metal,
  radius,
  screenTitle,
  velvet,
} from './theme.ts';
import { Bar, Coin, Medal, Panel, Ribbon, Velvet } from './Game.tsx';
import { WalkShape } from './WalkCard.tsx';

export const WALK_KM = { min: 1, max: 10, step: 0.5, initial: 4 };

// A stop's coin on the walk card's timeline.
const COIN = 30;

/** pipeline/tags.py TAGS, the vocabulary a walk can lean on; a test holds the
 *  two to the same list. Three groups of six, so the grid has no gaps. */
const THEME_GROUPS = [
  {
    title: 'Places & past',
    themes: ['history', 'culture', 'art', 'music', 'strange', 'adventure'],
  },
  { title: 'Out & about', themes: ['food', 'drink', 'nightlife', 'sport', 'nature', 'travel'] },
  { title: 'People', themes: ['personal', 'family', 'romance', 'comedy', 'work', 'business'] },
];

const themeName = (theme: string) => theme[0].toUpperCase() + theme.slice(1);

type LengthProps = { km: number; min: number; onKm: (km: number) => void };

/** Uncontrolled: the library's `value` is write-only, and lifting every tick
 *  re-rendered all of App under the thumb. No `step` either - iOS snaps the
 *  thumb only on release, which read as a jolt - so it rounds here, and the
 *  walk redraws once, on release. Compact: it shares a row with the shape. */
function LengthSlider({ km, min, onKm }: LengthProps) {
  const [shown, setShown] = useState(km);
  const round = (v: number) => Math.round(v / WALK_KM.step) * WALK_KM.step;
  return (
    <>
      <Slider
        style={[styles.slider, styles.grow]}
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
      <Text style={styles.value} accessibilityLiveRegion="polite">{`${shown} km`}</Text>
    </>
  );
}

type Span = { from: number | null; until: number | null };
type EraProps = Span & { onEra: (span: Span) => void };

// The length slider's native thumb: a pill, so the two read as one family.
const THUMB = 38;
const THUMB_HEIGHT = 24;
const LAST_STOP = ERA_STOPS.length - 1;

/** Two thumbs that snap to ERA_STOPS: Earlier to 1945 is old only, 1945 to
 *  Today modern only, both ends any time. A two-thumb slider is misread when
 *  it slides freely and says nothing (Baymard), so this one snaps, ticks, and
 *  names the span above it. Hand-rolled with a PanResponder, as SlideToUnlock
 *  is: the community slider has one thumb. The walk redraws once, on release. */
function EraRange({ from, until, onEra }: EraProps) {
  const [span, setSpan] = useState<[number, number]>(eraStops(from, until) ?? [0, LAST_STOP]);
  const [width, setWidth] = useState(0);
  const live = useRef(span);
  const at = useRef({ x: 0, thumb: 0, width: 0 });
  const done = useRef(onEra);
  done.current = onEra;

  const move = (thumb: number, stop: number) => {
    const [lo, hi] = live.current;
    const next: [number, number] =
      thumb === 0 ? [clamp(stop, 0, hi - 1), hi] : [lo, clamp(stop, lo + 1, LAST_STOP)];
    if (next[0] === lo && next[1] === hi) return;
    Haptics.selectionAsync().catch(() => {});
    live.current = next;
    setSpan(next);
  };
  const stopAt = (x: number) =>
    clamp(Math.round(((x - THUMB / 2) / (at.current.width - THUMB)) * LAST_STOP), 0, LAST_STOP);
  const release = () => done.current(eraSpan(live.current[0], live.current[1]));

  const pan = useRef(
    PanResponder.create({
      onStartShouldSetPanResponder: () => true,
      onPanResponderTerminationRequest: () => false,
      onPanResponderGrant: (e) => {
        // The thumbs take no touches, so this is the track's own x.
        const x = e.nativeEvent.locationX;
        const stop = stopAt(x);
        const [lo, hi] = live.current;
        const thumb = stop <= lo ? 0 : stop >= hi ? 1 : stop - lo <= hi - stop ? 0 : 1;
        at.current = { ...at.current, x, thumb };
        move(thumb, stop);
      },
      onPanResponderMove: (_, g) => move(at.current.thumb, stopAt(at.current.x + g.dx)),
      onPanResponderRelease: release,
      onPanResponderTerminate: release,
    }),
  ).current;

  const [lo, hi] = span;
  const x = (stop: number) => THUMB / 2 + (stop * (width - THUMB)) / LAST_STOP;
  const named = (stop: number) =>
    stop === 0 ? 'Earlier' : stop === LAST_STOP ? 'Today' : String(ERA_STOPS[stop]);
  const { from: shownFrom, until: shownUntil } = eraSpan(lo, hi);
  return (
    <>
      <View style={styles.lengthRow}>
        <Text style={styles.section} accessibilityRole="header">
          Era
        </Text>
        <Text style={styles.eraName} accessibilityLiveRegion="polite">
          {eraLabel(shownFrom, shownUntil)}
        </Text>
      </View>
      <View style={styles.tickNames}>
        {width > 0 &&
          ERA_STOPS.map((_, stop) => (
            <Text
              key={stop}
              style={[
                label,
                styles.tickName,
                stop === 0
                  ? { left: 0, textAlign: 'left' }
                  : stop === LAST_STOP
                    ? { right: 0, textAlign: 'right' }
                    : { left: x(stop) - 30 },
              ]}
            >
              {named(stop)}
            </Text>
          ))}
      </View>
      <View
        style={styles.eraTrack}
        onLayout={(e) => {
          at.current.width = e.nativeEvent.layout.width;
          setWidth(e.nativeEvent.layout.width);
        }}
        {...pan.panHandlers}
      >
        {width > 0 && (
          <>
            <View pointerEvents="none" style={styles.rail} />
            <View
              pointerEvents="none"
              style={[styles.rail, styles.railOn, { left: x(lo), width: x(hi) - x(lo) }]}
            />
            {ERA_STOPS.map((_, stop) => (
              <View
                key={stop}
                pointerEvents="none"
                style={[
                  styles.tick,
                  stop >= lo && stop <= hi && styles.tickOn,
                  { left: x(stop) - 3 },
                ]}
              />
            ))}
            {[lo, hi].map((stop, thumb) => (
              <View
                key={thumb}
                pointerEvents="none"
                style={[styles.thumb, { left: x(stop) - THUMB / 2 }]}
                accessible
                accessibilityRole="adjustable"
                accessibilityLabel={thumb === 0 ? 'From' : 'Until'}
                accessibilityValue={{ text: named(stop) }}
                accessibilityActions={[{ name: 'increment' }, { name: 'decrement' }]}
                onAccessibilityAction={(e) => {
                  move(thumb, stop + (e.nativeEvent.actionName === 'increment' ? 1 : -1));
                  release();
                }}
              />
            ))}
          </>
        )}
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
  /** This week's free walk is walked: the day the next one comes, and the
   *  card offers the subscription instead. */
  walkedOut: string | null;
  onSubscribe: () => void;
  /** The card's height, so the map fits the walk into what is left above it. */
  onHeight: (height: number) => void;
  /** Back to the map, from any step. */
  onClose: () => void;
  /** The step a dev link asked for (src/devOpen.ts). */
  devStep?: 'choices' | null;
};

/** One side of the pages; null keeps the side's space empty. */
type ArrowProps = {
  glyph: 'back' | 'forward';
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
      <Icon name={glyph} size={20} color={color.ink} />
    </Pressable>
  );
}

export function Preview({
  stops,
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
  devStep,
}: PreviewProps) {
  // One card: the shape and length in one row between ‹ ›, Customize, Start.
  // Customize is a step of its own.
  const [step, setStep] = useState<'choices' | null>(null);
  useEffect(() => {
    if (devStep !== undefined) setStep(devStep);
  }, [devStep]);
  // Said, not focused: the arrows keep VoiceOver where it is (WAI carousels).
  const stepped = useRef(false);
  useEffect(() => {
    if (stepped.current) AccessibilityInfo.announceForAccessibility(`Walk ${walkNumber}`);
    stepped.current = true;
  }, [walkNumber]);
  const close = <CloseButton label="Close the planner" onPress={onClose} place={styles.close} />;
  if (walkedOut !== null) {
    const day = walkedOut
      ? `on ${new Date(`${walkedOut}T12:00`).toLocaleDateString('en', { weekday: 'long' })}`
      : 'next week';
    return (
      <GlassCard style={styles.card}>
        <Text style={styles.cardTitle}>This week's free walk is done</Text>
        <Text style={styles.cardBody}>
          Your next one comes {day}. Or get Plus and walk every day.
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
  const unreachable = floorKm > WALK_KM.max;
  // Up to the slider's grid, so a floor of 2.3 km does not shift every step.
  const min = Math.min(
    Math.ceil(Math.max(WALK_KM.min, floorKm) / WALK_KM.step) * WALK_KM.step,
    WALK_KM.max,
  );
  const measure = (e: LayoutChangeEvent) => onHeight(e.nativeEvent.layout.height);
  const era = ask.from == null && ask.until == null ? '' : eraLabel(ask.from, ask.until);
  const customized = ask.themes.length > 0 || era !== '';
  if (step === 'choices') {
    return (
      <GlassCard style={styles.card} onLayout={measure} testID="walk-choices">
        <Pressable
          style={dim(styles.back)}
          onPress={() => setStep(null)}
          accessibilityRole="button"
          accessibilityLabel="Back to the walk"
        >
          <Icon name="back" size={18} color={color.ink} />
          <Text style={styles.secondaryText}>Back</Text>
        </Pressable>
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
        <ScrollView style={styles.choices} contentContainerStyle={styles.choicesInner}>
          <EraRange
            key={`${ask.from}:${ask.until}`}
            from={ask.from}
            until={ask.until}
            onEra={(span) => onAsk({ ...ask, ...span })}
          />
          {THEME_GROUPS.map((group) => (
            <Panel key={group.title} title={group.title}>
              <View style={styles.chips}>
                {group.themes.map((theme) => {
                  const on = ask.themes.includes(theme);
                  return (
                    <Chip
                      key={theme}
                      label={themeName(theme)}
                      on={on}
                      style={styles.themeChip}
                      onPress={() =>
                        onAsk({
                          ...ask,
                          themes: on
                            ? ask.themes.filter((t) => t !== theme)
                            : [...ask.themes, theme],
                        })
                      }
                    />
                  );
                })}
              </View>
            </Panel>
          ))}
        </ScrollView>
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
  const chosen = [ask.themes.map(themeName).join(', '), era].filter(Boolean).join(' · ');
  return (
    <GlassCard style={styles.card} onLayout={measure}>
      {/* The arrows page through walks. A missing one keeps its space, so
          nothing shifts between walks. */}
      <View style={styles.pages}>
        <View style={styles.grow}>
          <Ribbon label={subscribed ? "Today's walk" : "This week's walk"} />
        </View>
        <Arrow glyph="back" name="Previous walk" onPress={found ? onBack : null} busy={busy} />
        <Arrow glyph="forward" name="Next walk" onPress={found ? onNext : null} busy={busy} />
        <CloseButton label="Close the planner" onPress={onClose} />
      </View>
      {count === 0 && (
        <Text style={styles.cardBody} testID="no-walk">
          {`No walk within ${WALK_KM.max} km from here.`}
        </Text>
      )}
      {found && newNearby > 0 && (
        <Text style={styles.cardBody} testID="new-nearby">
          {`${newNearby} new ${newNearby === 1 ? 'story' : 'stories'} within 2 km since your last walk`}
        </Text>
      )}
      {found && emptyAt != null && (
        <Text style={styles.cardBody}>{`Nothing at ${emptyAt} km; this is the nearest.`}</Text>
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
      {unreachable && (
        <Text
          style={styles.cardBody}
        >{`The nearest walk from here is over ${WALK_KM.max} km.`}</Text>
      )}
      {/* The shape and the length, one control: a loop has a length, a
          one-way walk an end tapped on the map. */}
      <View style={styles.walkRow}>
        <Pressable
          style={dim(styles.shapeChip)}
          onPress={() => {
            Haptics.selectionAsync().catch(() => {});
            if (ask.loop) onPickEnd();
            else onAsk({ ...ask, loop: true, end: null });
          }}
          accessibilityRole="button"
          accessibilityLabel={ask.loop ? 'Loop' : 'One way'}
          accessibilityHint={ask.loop ? 'Switches to one way' : 'Switches to a loop'}
        >
          <Text style={styles.shapeText}>{ask.loop ? '↻ Loop' : '→ One way'}</Text>
        </Pressable>
        {ask.loop ? (
          // Keyed, so a length the server lifted resets the label; never
          // mid-drag, since only a release changes km.
          <LengthSlider key={`${min}:${km}`} km={Math.max(km, min)} min={min} onKm={onKm} />
        ) : (
          <Pressable
            style={dim([styles.secondary, button.small, styles.grow])}
            onPress={onPickEnd}
            accessibilityRole="button"
            accessibilityHint="Tap the map again for a new end"
          >
            <Text style={styles.secondaryText} numberOfLines={1}>
              {ask.end ? 'Change the end' : 'Tap the map for the end'}
            </Text>
          </Pressable>
        )}
      </View>
      {/* A subscriber's, offered to a free walker: velvet and badged Plus, so
          it is seen, and reads as the paywall before it is tapped. */}
      <Pressable
        onPress={subscribed ? () => setStep('choices') : onSubscribe}
        disabled={busy}
        accessibilityRole="button"
        accessibilityHint={subscribed ? undefined : 'Part of Plus'}
        testID="themes"
      >
        {({ pressed }) => (
          <Velvet style={[styles.customize, pressed && styles.pressed]}>
            <Coin size={34}>
              <Icon name="customize" size={20} color={foil.text} tone={color.paperRaised} />
            </Coin>
            <View style={styles.grow}>
              <Text style={styles.customizeText} numberOfLines={1}>
                {(subscribed && chosen) || 'Customize the walk'}
              </Text>
              <Text style={styles.customizeSub} numberOfLines={1}>
                Themes and an era it leans towards
              </Text>
            </View>
            {!subscribed && (
              <View style={styles.badge}>
                <Text style={styles.badgeText}>Plus</Text>
              </View>
            )}
            <Icon name="forward" size={16} color={color.onVelvetSoft} />
          </Velvet>
        )}
      </Pressable>
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
      {error && <Text style={styles.error}>{error}</Text>}
    </GlassCard>
  );
}

type WalkDoneProps = {
  stops: number;
  meters: number;
  loop: boolean;
  /** First unlock to last, or null when they were not all earned today. */
  minutes: number | null;
  /** Your Collector, every locket so far and the memories you filed, for its
   *  bar to the next rank. */
  collector: ClassId;
  rank: number;
  lockets: number;
  filed: number;
  /** The walk drawn whole, for the card it becomes in the journal. */
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

/** The day's last card: the walk drawn whole behind it, and what it came to. */
export function WalkDone({
  stops,
  meters,
  loop,
  minutes,
  collector,
  rank,
  lockets,
  filed,
  path,
  onDone,
  onHeight,
  onMore,
  onNotify,
}: WalkDoneProps) {
  const want = wants(rank, lockets, filed);
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
      <Ribbon label="Quest complete" />
      <View style={styles.doneTop}>
        <Text style={styles.doneTitle} accessibilityRole="header" testID="walk-done">
          Nice walk.
        </Text>
        <WalkShape path={path} size={56} />
      </View>
      <Text style={styles.cardBody}>
        {`${stops} ${stops === 1 ? 'memory' : 'memories'} · ${distance(meters)}${loop ? ' loop' : ''}${took}`}
      </Text>
      {/* What you earned: a tile per locket, then the Collector's bar
          filling with them (docs/10, "Game menus"). */}
      <View style={styles.loot}>
        {Array.from({ length: Math.min(stops, 5) }, (_, n) => (
          <Velvet key={n} style={styles.lootTile}>
            <Image source={locketOf().pin} style={styles.lootLocket} />
            <Text style={styles.lootPlus}>+1</Text>
          </Velvet>
        ))}
      </View>
      <Text style={[styles.cardBody, styles.lootText]}>
        {`+${stops} ${stops === 1 ? 'locket' : 'lockets'}`}
      </Text>
      <Velvet style={styles.rankStrip}>
        <View
          style={styles.rankStripIn}
          accessible
          accessibilityLabel={`${classOf(collector).ranks[rank]}, ${lockets} lockets`}
        >
          <Medal id={collector} stage={rank} size={50} />
          <View style={styles.grow}>
            <Text style={styles.rankName} numberOfLines={1}>
              {classOf(collector).ranks[rank]}
            </Text>
            <Bar into={rankInto(rank, lockets, filed)} height={12} />
          </View>
        </View>
      </Velvet>
      {/* Lockets alone don't grow it: when a memory of theirs is what's
          missing, say so here, where the walk just paid out. */}
      {want && want.filed > 0 && (
        <Text style={styles.cardBody}>{`${wantsWords(want)} to rank up`}</Text>
      )}
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
        <Button
          kind="text"
          label="Walk again tomorrow ›"
          onPress={onMore}
          testID="walk-done-more"
        />
      )}
    </GlassCard>
  );
}

/** A past walk, drawn on the map behind it: when, and what it came to.
 *  Opened from its card in the journal. */
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
  loot: { flexDirection: 'row', justifyContent: 'center', gap: 8, marginTop: 4 },
  lootTile: {
    width: 60,
    paddingVertical: 8,
    alignItems: 'center',
    borderRadius: 14,
    borderWidth: 1,
    borderColor: color.edge,
    borderBottomWidth: 3,
    borderBottomColor: velvet.deep,
  },
  lootLocket: { width: 28, height: 28 },
  lootPlus: { ...font.display, fontSize: 14, color: color.onVelvetGold },
  lootText: { textAlign: 'center' },
  rankStrip: { borderRadius: 18, borderWidth: 1, borderColor: color.edge },
  rankStripIn: { flexDirection: 'row', alignItems: 'center', gap: 12, padding: 10 },
  rankName: { ...font.title, fontSize: 18, lineHeight: 22, color: color.onVelvet, marginBottom: 4 },
  checks: { flexDirection: 'row', alignItems: 'center', gap: 6, flexWrap: 'wrap' },
  check: {
    width: 20,
    height: 20,
    borderRadius: 10,
    backgroundColor: color.gold,
    alignItems: 'center',
    justifyContent: 'center',
  },
  doneTop: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' },
  lengthRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'flex-end',
    marginTop: 6,
  },
  section: { ...font.uiBold, fontSize: 13, color: color.inkSoft, marginTop: 6 },
  slider: { height: 40 },
  chips: { flexDirection: 'row', flexWrap: 'wrap', gap: 8, marginTop: 4 },
  themeChip: { width: '31%' },
  // Bled out and padded back, so a thumb's or chip's shadow is not cut at the edge.
  choices: { maxHeight: 440, marginHorizontal: -8 },
  choicesInner: { gap: 10, paddingHorizontal: 8 },
  eraName: { ...font.uiBold, fontSize: 15, color: color.ink },
  tickNames: { height: 16 },
  tickName: { position: 'absolute', width: 60, textAlign: 'center' },
  eraTrack: { height: 40, justifyContent: 'center' },
  rail: {
    position: 'absolute',
    left: THUMB / 2,
    right: THUMB / 2,
    height: 4,
    borderRadius: 2,
    backgroundColor: color.rule,
  },
  railOn: { right: undefined, backgroundColor: color.velvetGround },
  tick: {
    position: 'absolute',
    width: 6,
    height: 6,
    borderRadius: 3,
    backgroundColor: color.inkSoft,
    opacity: 0.35,
  },
  tickOn: { backgroundColor: color.paper, opacity: 1 },
  thumb: {
    position: 'absolute',
    width: THUMB,
    height: THUMB_HEIGHT,
    borderRadius: THUMB_HEIGHT / 2,
    backgroundColor: metal.light,
    shadowColor: color.shadow,
    shadowOffset: { width: 0, height: 1 },
    shadowRadius: 3,
    shadowOpacity: 0.2,
  },
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
  back: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 4,
    alignSelf: 'flex-start',
    minHeight: 44,
    marginTop: -10,
  },
  doneTitle: screenTitle,
  value: {
    ...font.title,
    fontSize: 20,
    lineHeight: 24,
    color: color.ink,
    minWidth: 52,
    textAlign: 'right',
  },
  pages: { flexDirection: 'row', alignItems: 'center', gap: 8 },
  walkRow: { flexDirection: 'row', alignItems: 'center', gap: 8, marginTop: 4 },
  shapeChip: {
    minHeight: 40,
    paddingHorizontal: 12,
    borderRadius: radius.pill,
    justifyContent: 'center',
    backgroundColor: color.velvetGround,
    borderBottomWidth: 3,
    borderColor: velvet.deep,
  },
  shapeText: { ...font.uiBold, fontSize: 15, color: color.onVelvet },
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
  customize: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 12,
    minHeight: 60,
    paddingHorizontal: 12,
    borderRadius: 16,
    borderWidth: 1,
    borderColor: color.edge,
    borderBottomWidth: 3,
    borderBottomColor: velvet.deep,
    marginTop: 6,
  },
  customizeText: { ...font.uiBold, fontSize: 17, color: color.onVelvet },
  customizeSub: { ...font.uiMedium, fontSize: 13, color: color.onVelvetSoft },
  pressed: { opacity: 0.85 },
});
