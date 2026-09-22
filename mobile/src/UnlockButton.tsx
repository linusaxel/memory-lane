/** The one playful control in the app - spec in "The unlock control", UI.md. */

import { useEffect, useRef, useState } from 'react';
import {
  AccessibilityInfo,
  Animated,
  Easing,
  Pressable,
  StyleSheet,
  Text,
  View,
} from 'react-native';
import * as Haptics from 'expo-haptics';

import Padlock from './Padlock.tsx';
import { color, font, label } from './theme.ts';

/** Long enough to feel like a lock turning, short enough not to be a chore. */
const HOLD_MS = 900;

/** How long the shackle is given to clear the body before the request goes
 *  out and the sheet is allowed to swap. Roughly where the spring has settled;
 *  longer is noticeable, shorter and the lock is cut off mid-swing. Against a
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

type Props = {
  onUnlock: () => void;
  busy?: boolean;
};

export default function UnlockButton({ onUnlock, busy = false }: Props) {
  const fill = useRef(new Animated.Value(0)).current;
  const burst = useRef(new Animated.Value(0)).current;
  const sprung = useRef(new Animated.Value(0)).current;
  const holding = useRef(false);
  const timers = useRef<ReturnType<typeof setTimeout>[]>([]);
  const [assistive, setAssistive] = useState(false);

  useEffect(() => {
    AccessibilityInfo.isScreenReaderEnabled().then(setAssistive);
    const sub = AccessibilityInfo.addEventListener('screenReaderChanged', setAssistive);
    return () => sub.remove();
  }, []);

  const clearTicks = () => {
    timers.current.forEach(clearTimeout);
    timers.current = [];
  };

  useEffect(() => clearTicks, []);

  // A refusal leaves this mounted with a full ring, which reads as "it worked"
  // next to an error saying it did not. Success unmounts us instead - the
  // sheet swaps to its open composition - so busy falling is always a no.
  const wasBusy = useRef(false);
  useEffect(() => {
    if (wasBusy.current && !busy) {
      burst.setValue(0);
      sprung.setValue(0);
      Animated.spring(fill, { toValue: 0, speed: 14, useNativeDriver: true }).start();
    }
    wasBusy.current = busy;
  }, [busy, fill, burst, sprung]);

  const start = () => {
    if (busy) return;
    holding.current = true;
    Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Light).catch(() => {});

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
      Animated.parallel([
        Animated.timing(burst, {
          toValue: 1,
          duration: 420,
          easing: Easing.out(Easing.quad),
          useNativeDriver: true,
        }),
        // Tension and friction rather than a duration: a shackle is a sprung
        // piece of steel, and it should overshoot and settle rather than
        // arrive. High tension, low friction - metal, not rubber.
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
    clearTicks();
    // Springs back where it was, visibly. Letting go early has to read as "you
    // let go", not as "it refused you" - and no haptic, which would reward it.
    Animated.spring(fill, { toValue: 0, speed: 14, useNativeDriver: true }).start();
  };

  // Everything below is transform and opacity only, because those are the two
  // things useNativeDriver can carry. A colour that animates would put this
  // whole control back on the JS thread for the 900ms it most needs to be
  // smooth.
  const rising = { transform: [{ scale: fill.interpolate(RISE) }] };

  const straining = {
    opacity: fill.interpolate(STRAIN),
    transform: [{ scale: fill.interpolate(STRAIN_SCALE) }],
  };

  const flare = {
    opacity: burst.interpolate({ inputRange: [0, 1], outputRange: [0.55, 0] }),
    transform: [{ scale: burst.interpolate({ inputRange: [0, 1], outputRange: [1, 1.75] }) }],
  };

  // The body swells as it is worked, then recoils once as the shackle leaves
  // it. Out and back, because a body that stays tilted reads as broken.
  const working = {
    transform: [
      { scale: Animated.add(fill.interpolate(SWELL), burst.interpolate(GIVE)) },
      { rotate: sprung.interpolate(RECOIL) },
    ],
  };

  // Up and out, hinged on the leg that stays in the body. Both happen at once
  // and the rotation is what makes it a lock rather than a lid.
  const shackle = {
    transform: [
      { translateY: sprung.interpolate({ inputRange: [0, 1], outputRange: [0, -7] }) },
      { rotate: sprung.interpolate({ inputRange: [0, 1], outputRange: ['0deg', '38deg'] }) },
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
        <Animated.View pointerEvents="none" style={[styles.flare, flare]} />

        <View style={styles.ring}>
          <Animated.View style={[styles.fill, rising]} />
          {/* The last quarter. An inner ring brightening and closing in is the
              lock about to turn, and it arrives with the third haptic. */}
          <Animated.View pointerEvents="none" style={[styles.strain, straining]} />
          {/* The same padlock the map pins use, so the ring reads as the thing
              that opens them rather than as a record button. Amber-700 stays
              readable on both the white rest state and the filled one. */}
          <Animated.View style={working}>
            <Padlock size={27} color={color.sealDeep} shackleStyle={shackle} />
          </Animated.View>
        </View>
      </Pressable>
      <Text style={styles.caption}>{busy ? 'Unlocking…' : 'Hold to unlock'}</Text>
    </View>
  );
}

const RING = 84;

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
const GIVE = { inputRange: [0, 0.35, 1], outputRange: [0, 0.22, 0] };

const styles = StyleSheet.create({
  wrap: { alignItems: 'center', gap: 12, paddingVertical: 8 },
  ring: {
    width: RING,
    height: RING,
    borderRadius: RING / 2,
    borderWidth: 3,
    borderColor: color.seal,
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
    borderColor: color.seal,
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
  caption: { ...label },
});
