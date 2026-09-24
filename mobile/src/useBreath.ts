import { useEffect, useRef, useState } from 'react';
import { AccessibilityInfo, Animated, Easing } from 'react-native';

function useReduceMotion() {
  const [reduceMotion, setReduceMotion] = useState(false);
  useEffect(() => {
    AccessibilityInfo.isReduceMotionEnabled().then(setReduceMotion);
    const sub = AccessibilityInfo.addEventListener('reduceMotionChanged', setReduceMotion);
    return () => sub.remove();
  }, []);
  return reduceMotion;
}

/** The breath, as a transform: the "at a stop" pill, when there is something
 *  to open right here. */
export function useBreath(active: boolean) {
  const breath = useRef(new Animated.Value(0)).current;
  const reduceMotion = useReduceMotion();

  useEffect(() => {
    // Stopping a loop leaves the value wherever the last frame put it, so a
    // banner that stops being reachable - or has Reduce Motion turned on -
    // mid-breath would stay 2% too big for the rest of the session.
    if (!active || reduceMotion) {
      breath.setValue(0);
      return;
    }
    const loop = Animated.loop(
      Animated.sequence([
        Animated.timing(breath, {
          toValue: 1,
          duration: 1100,
          easing: Easing.inOut(Easing.quad),
          useNativeDriver: true,
        }),
        Animated.timing(breath, {
          toValue: 0,
          duration: 1100,
          easing: Easing.inOut(Easing.quad),
          useNativeDriver: true,
        }),
      ]),
    );
    loop.start();
    return () => loop.stop();
  }, [breath, active, reduceMotion]);

  return { transform: [{ scale: breath.interpolate({ inputRange: [0, 1], outputRange: [1, 1.04] }) }] };
}

/** The hop: the next stop's pin jumps, lands with a squash, and rests. Only a
 *  transform, so the pin's tap target never moves. */
export function useHop(active: boolean) {
  const hop = useRef(new Animated.Value(0)).current;
  const reduceMotion = useReduceMotion();

  useEffect(() => {
    if (!active || reduceMotion) {
      hop.setValue(0);
      return;
    }
    const loop = Animated.loop(
      Animated.sequence([
        Animated.timing(hop, {
          toValue: 1,
          duration: 260,
          easing: Easing.out(Easing.quad),
          useNativeDriver: true,
        }),
        Animated.timing(hop, {
          toValue: 2,
          duration: 260,
          easing: Easing.in(Easing.quad),
          useNativeDriver: true,
        }),
        Animated.timing(hop, {
          toValue: 3,
          duration: 180,
          easing: Easing.out(Easing.quad),
          useNativeDriver: true,
        }),
        Animated.delay(900),
      ]),
    );
    loop.start();
    return () => loop.stop();
  }, [hop, active, reduceMotion]);

  // 0 rest, 1 top of the jump, 2 landing, 3 back at rest.
  return {
    transform: [
      { translateY: hop.interpolate({ inputRange: [0, 1, 2, 3], outputRange: [0, -10, 0, 0] }) },
      { scaleX: hop.interpolate({ inputRange: [0, 1, 2, 2.4, 3], outputRange: [1, 0.94, 1.12, 1, 1] }) },
      { scaleY: hop.interpolate({ inputRange: [0, 1, 2, 2.4, 3], outputRange: [1, 1.08, 0.86, 1, 1] }) },
    ],
  };
}
