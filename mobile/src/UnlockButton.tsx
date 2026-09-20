/** The one playful control in the app. See "The unlock control" in UI.md. */

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

/** Long enough to feel like a lock turning, short enough not to be a chore. */
const HOLD_MS = 900;

type Props = {
  onUnlock: () => void;
  busy?: boolean;
};

export default function UnlockButton({ onUnlock, busy = false }: Props) {
  const fill = useRef(new Animated.Value(0)).current;
  const holding = useRef(false);
  const [assistive, setAssistive] = useState(false);

  useEffect(() => {
    AccessibilityInfo.isScreenReaderEnabled().then(setAssistive);
    const sub = AccessibilityInfo.addEventListener('screenReaderChanged', setAssistive);
    return () => sub.remove();
  }, []);

  const start = () => {
    if (busy) return;
    holding.current = true;
    Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Light);
    Animated.timing(fill, {
      toValue: 1,
      duration: HOLD_MS,
      easing: Easing.linear,
      useNativeDriver: true,
    }).start(({ finished }) => {
      if (!finished || !holding.current) return;
      holding.current = false;
      Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Medium);
      onUnlock();
    });
  };

  const cancel = () => {
    if (!holding.current) return;
    holding.current = false;
    // Springs back where it was, visibly. Letting go early has to read as "you
    // let go", not as "it refused you" - and no haptic, which would reward it.
    Animated.spring(fill, { toValue: 0, speed: 14, useNativeDriver: true }).start();
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
        <View style={styles.ring}>
          <Animated.View style={[styles.fill, { transform: [{ scale: fill }] }]} />
          {/* The same padlock the map pins use, so the ring reads as the thing
              that opens them rather than as a record button. Amber-700 stays
              readable on both the white rest state and the filled one. */}
          <Padlock size={27} color="#b45309" />
        </View>
      </Pressable>
      <Text style={styles.caption}>{busy ? 'Unlocking…' : 'Hold to unlock'}</Text>
    </View>
  );
}

const RING = 84;

const styles = StyleSheet.create({
  wrap: { alignItems: 'center', gap: 10, paddingVertical: 8 },
  ring: {
    width: RING,
    height: RING,
    borderRadius: RING / 2,
    borderWidth: 3,
    borderColor: '#f59e0b',
    backgroundColor: '#fff',
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
    backgroundColor: '#fde68a',
  },
  caption: { fontSize: 13, color: '#71717a' },
});
