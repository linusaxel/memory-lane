/** The one playful control in the app - spec in "The unlock control", UI.md. */

import { useEffect, useRef, useState } from 'react';
import { AccessibilityInfo, Animated, Easing, Pressable, StyleSheet, View } from 'react-native';
import * as Haptics from 'expo-haptics';

import Glyph from './Glyph.tsx';
import { color } from './theme.ts';

/** Long enough to feel like a lock turning, short enough not to be a chore. */
export const HOLD_MS = 900;

/** How long the lock is given to open and bounce before the request goes
 *  out and the sheet is allowed to swap. Roughly where the recoil has settled;
 *  longer is noticeable, shorter and the lock is cut off mid-bounce. Against a
 *  local API the round trip is ~20ms - without this wait the lock never
 *  visibly opens at all. */
const SNAP_MS = 240;

/** Ticks under the thumb while the ring fills, because 900ms of silence is a
 *  long time to wonder whether a control is working.
 *
 *  The gaps close - 340, 250, 190, 110 - and the taps sharpen, so the hold
 *  accelerates in the hand while the ring rises steadily in the eye. That
 *  mismatch is the whole trick: anticipation comes from the tempo, and the
 *  ring stays honest about how much longer you have to wait. */
const TICKS: { at: number; style: Haptics.ImpactFeedbackStyle }[] = [
  { at: 340, style: Haptics.ImpactFeedbackStyle.Soft },
  { at: 590, style: Haptics.ImpactFeedbackStyle.Light },
  { at: 780, style: Haptics.ImpactFeedbackStyle.Rigid },
];

/** Where the ring starts straining. Matches the last tick, so the thing you
 *  feel and the thing you see arrive together. */
const STRAIN_FROM = TICKS[2].at / HOLD_MS;

/** One breath and one ripple at rest. Slow enough to read as alive, not as a
 *  spinner asking you to wait. */
const IDLE_MS = 2400;

type Props = {
  onUnlock: () => void;
  busy?: boolean;
  /** True while a hold is under way, false when it is let go or refused. */
  onHold?: (holding: boolean) => void;
  /** Why the last hold was refused. Nothing draws it - the ring shakes its
   *  head - so a screen reader is told instead. */
  error?: string | null;
};

export default function UnlockButton({ onUnlock, busy = false, onHold, error }: Props) {
  const fill = useRef(new Animated.Value(0)).current;
  const burst = useRef(new Animated.Value(0)).current;
  const sprung = useRef(new Animated.Value(0)).current;
  const idle = useRef(new Animated.Value(0)).current;
  const calm = useRef(new Animated.Value(0)).current;
  const press = useRef(new Animated.Value(0)).current;
  const shake = useRef(new Animated.Value(0)).current;
  const loop = useRef<Animated.CompositeAnimation | null>(null);
  const holding = useRef(false);
  const timers = useRef<ReturnType<typeof setTimeout>[]>([]);
  const [assistive, setAssistive] = useState(false);
  const [still, setStill] = useState(false);
  const [open, setOpen] = useState(false);

  useEffect(() => {
    AccessibilityInfo.isScreenReaderEnabled().then(setAssistive);
    AccessibilityInfo.isReduceMotionEnabled().then(setStill);
    const subs = [
      AccessibilityInfo.addEventListener('screenReaderChanged', setAssistive),
      AccessibilityInfo.addEventListener('reduceMotionChanged', setStill),
    ];
    return () => subs.forEach((sub) => sub.remove());
  }, []);

  // At rest the ring breathes and ripples, so it asks to be touched before it
  // is. The hold takes the stage from it: nothing loops while the ring fills.
  const rest = () => {
    if (busy || still) return;
    Animated.timing(calm, { toValue: 1, duration: 300, useNativeDriver: true }).start();
    loop.current?.stop();
    idle.setValue(0);
    loop.current = Animated.loop(
      Animated.timing(idle, {
        toValue: 1,
        duration: IDLE_MS,
        easing: Easing.linear,
        useNativeDriver: true,
      }),
    );
    loop.current.start();
  };

  const quiet = () => {
    loop.current?.stop();
    Animated.timing(calm, { toValue: 0, duration: 150, useNativeDriver: true }).start();
  };

  useEffect(() => {
    if (busy || still) quiet();
    else rest();
    return () => loop.current?.stop();
  }, [busy, still]);

  const clearTicks = () => {
    timers.current.forEach(clearTimeout);
    timers.current = [];
  };

  useEffect(
    () => () => {
      clearTicks();
      // Walked out of reach mid-hold: the pill must not stay counted down.
      if (holding.current) onHold?.(false);
    },
    [],
  );

  // A refusal leaves this mounted with a full ring, which reads as "it worked"
  // next to an error saying it did not. Success unmounts us instead - the
  // sheet swaps to its open composition - so busy falling is always a no.
  const wasBusy = useRef(false);
  useEffect(() => {
    if (wasBusy.current && !busy) {
      onHold?.(false);
      burst.setValue(0);
      sprung.setValue(0);
      setOpen(false);
      Animated.spring(fill, { toValue: 0, speed: 14, useNativeDriver: true }).start();
      // There are no words to say no with, so it shakes its head.
      Haptics.notificationAsync(Haptics.NotificationFeedbackType.Warning).catch(() => {});
      Animated.sequence(
        [-10, 10, -6, 6, 0].map((toValue) =>
          Animated.timing(shake, { toValue, duration: 64, useNativeDriver: true }),
        ),
      ).start();
    }
    wasBusy.current = busy;
  }, [busy, fill, burst, sprung, shake]);

  useEffect(() => {
    if (error) AccessibilityInfo.announceForAccessibility(error);
  }, [error]);

  const start = () => {
    if (busy) return;
    holding.current = true;
    onHold?.(true);
    Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Light).catch(() => {});
    quiet();
    Animated.spring(press, { toValue: 1, speed: 40, bounciness: 0, useNativeDriver: true }).start();

    clearTicks();
    timers.current = TICKS.map(({ at, style }) =>
      setTimeout(() => {
        if (holding.current) Haptics.impactAsync(style).catch(() => {});
      }, at),
    );

    Animated.timing(fill, {
      toValue: 1,
      duration: HOLD_MS,
      easing: Easing.linear,
      useNativeDriver: true,
    }).start(({ finished }) => {
      if (!finished || !holding.current) return;
      holding.current = false;
      clearTicks();
      // Success, not another impact: a three-part pattern is the one signature
      // in the app that means a thing was earned, and nothing else uses it.
      Haptics.notificationAsync(Haptics.NotificationFeedbackType.Success).catch(() => {});
      setOpen(true);
      Animated.parallel([
        release(),
        Animated.timing(burst, {
          toValue: 1,
          duration: 420,
          easing: Easing.out(Easing.quad),
          useNativeDriver: true,
        }),
        // Tension and friction rather than a duration: a lock is sprung
        // steel, and it should overshoot and settle rather than arrive. High
        // tension, low friction - metal, not rubber.
        Animated.spring(sprung, {
          toValue: 1,
          tension: 170,
          friction: 7,
          useNativeDriver: true,
        }),
      ]).start();
      timers.current.push(setTimeout(onUnlock, SNAP_MS));
    });
  };

  const cancel = () => {
    if (!holding.current) return;
    holding.current = false;
    onHold?.(false);
    clearTicks();
    // Springs back where it was, visibly. Letting go early has to read as "you
    // let go", not as "it refused you" - and no haptic, which would reward it.
    Animated.spring(fill, { toValue: 0, speed: 14, useNativeDriver: true }).start();
    release().start();
    rest();
  };

  // Pops back past where it was, so letting go is answered as firmly as pressing.
  const release = () =>
    Animated.spring(press, { toValue: 0, speed: 20, bounciness: 10, useNativeDriver: true });

  // Everything below is transform and opacity only, because those are the two
  // things useNativeDriver can carry. A colour that animates would put this
  // whole control back on the JS thread for the 900ms it most needs to be
  // smooth.
  const rising = { transform: [{ scale: fill.interpolate(RISE) }] };

  const straining = {
    opacity: fill.interpolate(STRAIN),
    transform: [{ scale: fill.interpolate(STRAIN_SCALE) }],
  };

  // Two ripples half a breath apart, so one is always leaving the ring.
  const ripple = (phase: Animated.AnimatedInterpolation<number> | Animated.Value) => ({
    opacity: Animated.multiply(phase.interpolate(RIPPLE_FADE), calm),
    transform: [{ scale: phase.interpolate(RIPPLE_SCALE) }],
  });
  const later = Animated.modulo(Animated.add(idle, 0.5), 1);

  const body = {
    transform: [
      { translateX: shake },
      { scale: Animated.multiply(idle.interpolate(BREATHE), press.interpolate(SQUISH)) },
    ],
  };

  const flare = {
    opacity: burst.interpolate({ inputRange: [0, 1], outputRange: [0.55, 0] }),
    transform: [{ scale: burst.interpolate({ inputRange: [0, 1], outputRange: [1, 1.75] }) }],
  };

  // The lock swells as it is worked, then recoils once as it opens. Out and
  // back, because a lock that stays tilted reads as broken.
  const working = {
    transform: [
      { scale: Animated.add(fill.interpolate(SWELL), burst.interpolate(GIVE)) },
      { rotate: sprung.interpolate(RECOIL) },
    ],
  };

  return (
    <View style={styles.wrap}>
      <Pressable
        accessibilityRole="button"
        accessibilityLabel="Unlock this memory"
        accessibilityHint="Press and hold until the ring fills"
        accessibilityState={{ disabled: busy }}
        onPressIn={start}
        onPressOut={cancel}
        // A hold is impossible for some hands. VoiceOver's activation is a plain
        // press, so it opens the gate directly.
        // ponytail: covers screen-reader users, not every motor impairment.
        // A "tap to unlock" accessibility setting is the next rung if asked for.
        onPress={assistive ? onUnlock : undefined}
      >
        {/* Outside the clipped ring, or it would be trimmed to nothing. */}
        <Animated.View pointerEvents="none" style={[styles.ripple, ripple(idle)]} />
        <Animated.View pointerEvents="none" style={[styles.ripple, ripple(later)]} />
        <Animated.View pointerEvents="none" style={[styles.flare, flare]} />

        {/* The glow lives out here: the ring's overflow clip would cut it off. */}
        <Animated.View style={[styles.glow, body]}>
          <View style={styles.ring}>
            <Animated.View style={[styles.fill, rising]} />
            {/* The last quarter. An inner ring brightening and closing in is the
                lock about to turn, and it arrives with the third haptic. */}
            <Animated.View pointerEvents="none" style={[styles.strain, straining]} />
            {/* A lock, so the ring reads as the thing that opens memories rather
                than as a record button. Amber-700 stays readable on both the
                white rest state and the filled one. */}
            <Animated.View style={working}>
              <Glyph
                name={open ? 'lock.open.fill' : 'lock.fill'}
                size={44}
                color={color.sealDeep}
                bounce={open}
              />
            </Animated.View>
          </View>
        </Animated.View>
      </Pressable>
    </View>
  );
}

const RING = 136;

/** Not from zero: the press has to be answered in the same frame it happens,
 *  and a disc growing from nothing reads as lag. */
const RISE = { inputRange: [0, 1], outputRange: [0.14, 1] };
const STRAIN = { inputRange: [0, STRAIN_FROM, 1], outputRange: [0, 0, 1] };
const STRAIN_SCALE = { inputRange: [0, STRAIN_FROM, 1], outputRange: [1, 1, 0.9] };
const SWELL = { inputRange: [0, 1], outputRange: [1, 1.12] };
// Clamped, because `sprung` is a spring and overshoots past 1. Unclamped, the
// body would keep rotating along the last segment's slope and tip a degree the
// wrong way at the exact moment it is supposed to have settled.
const RECOIL = {
  inputRange: [0, 0.4, 1],
  outputRange: ['0deg', '3deg', '0deg'],
  extrapolate: 'clamp' as const,
};
const BREATHE = { inputRange: [0, 0.5, 1], outputRange: [1, 1.03, 1] };
const SQUISH = { inputRange: [0, 1], outputRange: [1, 0.94] };
const RIPPLE_SCALE = { inputRange: [0, 1], outputRange: [1, 1.6] };
const RIPPLE_FADE = { inputRange: [0, 1], outputRange: [0.45, 0] };
const GIVE = { inputRange: [0, 0.35, 1], outputRange: [0, 0.22, 0] };

const styles = StyleSheet.create({
  wrap: { alignItems: 'center' },
  glow: {
    borderRadius: RING / 2,
    backgroundColor: color.paper,
    shadowColor: color.seal,
    shadowOpacity: 0.5,
    shadowRadius: 14,
    shadowOffset: { width: 0, height: 0 },
  },
  ripple: {
    position: 'absolute',
    top: 0,
    left: 0,
    width: RING,
    height: RING,
    borderRadius: RING / 2,
    borderWidth: 2,
    borderColor: color.seal,
  },
  ring: {
    width: RING,
    height: RING,
    borderRadius: RING / 2,
    borderWidth: 3,
    borderColor: color.sealDeep,
    backgroundColor: color.paper,
    alignItems: 'center',
    justifyContent: 'center',
    // Clips the growing disc to the circle; without it the fill is a square.
    overflow: 'hidden',
  },
  fill: {
    position: 'absolute',
    top: 0,
    left: 0,
    right: 0,
    bottom: 0,
    borderRadius: RING / 2,
    backgroundColor: color.sealSoft,
  },
  strain: {
    position: 'absolute',
    top: 4,
    left: 4,
    right: 4,
    bottom: 4,
    borderRadius: RING / 2,
    borderWidth: 2,
    borderColor: color.sealDeep,
  },
  flare: {
    position: 'absolute',
    top: 0,
    left: 0,
    width: RING,
    height: RING,
    borderRadius: RING / 2,
    borderWidth: 3,
    borderColor: color.seal,
  },
});
