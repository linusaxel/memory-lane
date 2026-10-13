/** Plan a walk, in the map's dock beside the others and their size: your
 *  Collector in a foil ring, as the HUD's medal draws it, its name under it.
 *  A tap sets them walking: three bobbing steps, a lean, and out of the ring
 *  to the right, and as they leave (0.9 s) `onWalkEnd` opens the planner.
 *  Reduce Motion skips the walk. */

import { useRef } from 'react';
import { Pressable, StyleSheet, Text, View } from 'react-native';
import Animated, {
  Easing,
  runOnJS,
  useAnimatedStyle,
  useReducedMotion,
  useSharedValue,
  withTiming,
} from 'react-native-reanimated';

import CollectorLook from './CollectorLook';
import type { ClassId } from './collector';
import { Foil } from './Game';
import { color, font } from './theme';

const LABEL = 'Plan a walk';
const SIZE = 34;
const WALK_MS = 900;

export function PlanWalkButton({
  id,
  stage,
  onPress,
  onWalkEnd,
}: {
  /** Your Collector: its class and look. */
  id: ClassId;
  stage: number;
  /** On tap, for the haptic. */
  onPress: () => void;
  /** As they walk out of the ring. */
  onWalkEnd: () => void;
}) {
  const reduceMotion = useReducedMotion();
  const t = useSharedValue(0);
  const busy = useRef(false);

  const finish = () => {
    busy.current = false;
    t.value = 0;
    onWalkEnd();
  };

  const press = () => {
    if (busy.current) return;
    onPress();
    if (reduceMotion) {
      onWalkEnd();
      return;
    }
    busy.current = true;
    t.value = 0;
    t.value = withTiming(1, { duration: WALK_MS, easing: Easing.linear }, (done) => {
      if (done) runOnJS(finish)();
    });
  };

  // Three steps: a bob on each, the body rocking with them, leaning in as
  // it goes; the last third carries them out of the ring.
  const walk = useAnimatedStyle(() => {
    const x = t.value;
    const step = Math.abs(Math.sin(3 * Math.PI * x));
    const out = x < 0.6 ? 0 : (x - 0.6) / 0.4;
    return {
      transform: [
        { translateX: SIZE * 0.9 * out * out },
        { translateY: -SIZE * 0.08 * step },
        { rotate: `${x > 0 ? 5 + 4 * Math.sin(6 * Math.PI * x) : 0}deg` },
        { scaleY: 1 - 0.05 * step },
      ],
    };
  });

  return (
    <Pressable
      onPress={press}
      accessibilityRole="button"
      accessibilityLabel={LABEL}
      style={({ pressed }) => [styles.press, pressed && styles.pressed]}
    >
      <Foil style={styles.ring}>
        <View style={styles.well}>
          <Animated.View style={[styles.look, walk]}>
            <CollectorLook id={id} stage={stage} size={SIZE * 1.05} />
          </Animated.View>
        </View>
      </Foil>
      <Text style={styles.label}>{LABEL}</Text>
    </Pressable>
  );
}

const styles = StyleSheet.create({
  press: { alignItems: 'center', gap: 2 },
  pressed: { transform: [{ scale: 0.95 }] },
  ring: { width: SIZE, height: SIZE, borderRadius: SIZE / 2, padding: 1.5 },
  well: {
    flex: 1,
    borderRadius: SIZE / 2,
    overflow: 'hidden',
    backgroundColor: color.paperRaised,
    alignItems: 'center',
    justifyContent: 'flex-end',
  },
  look: { marginBottom: '-12%' },
  label: { ...font.uiBold, fontSize: 11, color: color.gold },
});
