/** Plan a walk, the raised middle of the map's dock: a compass rose on go
 *  enamel in a foil ring, its name under it. A tap swings the rose a turn and
 *  a half, and when it settles (0.9 s) `onWalkEnd` opens the planner. Reduce
 *  Motion skips the swing. */

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
import Svg, { Circle, Path } from 'react-native-svg';

import { Foil } from './Game';
import { color, foil, font } from './theme';

const LABEL = 'Plan a walk';
const SIZE = 72;
const SWING_MS = 900;

/** Eight points, each a light and a dark half, so the rose reads as struck
 *  foil. Drawn in a 48 box. */
function Rose({ size }: { size: number }) {
  const point = (angle: number, long: boolean) => {
    const r = long ? 21 : 13;
    const w = long ? 4.5 : 3.5;
    return [
      <Path
        key={`${angle}l`}
        d={`M24 ${24 - r} L${24 - w} 24 L24 24 Z`}
        fill={foil.colors[0]}
        transform={`rotate(${angle} 24 24)`}
      />,
      <Path
        key={`${angle}d`}
        d={`M24 ${24 - r} L${24 + w} 24 L24 24 Z`}
        fill={foil.colors[2]}
        opacity={0.75}
        transform={`rotate(${angle} 24 24)`}
      />,
    ];
  };
  return (
    <Svg width={size} height={size} viewBox="0 0 48 48">
      <Circle
        cx={24}
        cy={24}
        r={16}
        fill="none"
        stroke={foil.colors[1]}
        strokeWidth={1}
        opacity={0.7}
      />
      {[45, 135, 225, 315].map((a) => point(a, false))}
      {[0, 90, 180, 270].map((a) => point(a, true))}
      <Circle cx={24} cy={24} r={2.6} fill={foil.colors[0]} stroke={foil.ring} strokeWidth={0.8} />
    </Svg>
  );
}

export function PlanWalkButton({
  onPress,
  onWalkEnd,
}: {
  /** On tap, for the haptic. */
  onPress: () => void;
  /** When the rose settles. */
  onWalkEnd: () => void;
}) {
  const reduceMotion = useReducedMotion();
  const turn = useSharedValue(0);
  const busy = useRef(false);

  const finish = () => {
    busy.current = false;
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
    turn.value = 0;
    turn.value = withTiming(
      540,
      { duration: SWING_MS, easing: Easing.out(Easing.cubic) },
      (done) => {
        if (done) runOnJS(finish)();
      },
    );
  };

  const spin = useAnimatedStyle(() => ({ transform: [{ rotate: `${turn.value}deg` }] }));
  return (
    <Pressable
      onPress={press}
      accessibilityRole="button"
      accessibilityLabel={LABEL}
      style={({ pressed }) => [styles.press, pressed && styles.pressed]}
    >
      <Foil style={styles.ring}>
        <View style={styles.enamel}>
          <Animated.View style={spin}>
            <Rose size={SIZE - 18} />
          </Animated.View>
        </View>
      </Foil>
      <Text style={styles.label}>{LABEL}</Text>
    </Pressable>
  );
}

const styles = StyleSheet.create({
  press: { alignItems: 'center', gap: 4 },
  pressed: { transform: [{ scale: 0.95 }] },
  ring: { width: SIZE, height: SIZE, borderRadius: SIZE / 2, padding: 3 },
  enamel: {
    flex: 1,
    borderRadius: SIZE / 2,
    backgroundColor: color.goBg,
    borderWidth: 1,
    borderColor: color.goRim,
    alignItems: 'center',
    justifyContent: 'center',
  },
  label: { ...font.uiBold, fontSize: 12, color: color.ink },
});
