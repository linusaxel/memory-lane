/** Collect: the locket just read lifts off the sheet's foot, arcs up to your
 *  Collector top left and lands in a spark of gold (docs/10, "Collect, don't
 *  close"). `onLanded` is the touch, so the ring ticks; `onDone` once the
 *  sparks have gone. App skips it under Reduce Motion. Timings were tuned in
 *  an HTML mock and kept. */

import { useEffect, useRef } from 'react';
import { StyleSheet, View, type ImageSourcePropType } from 'react-native';
import Animated, {
  Easing,
  runOnJS,
  useAnimatedStyle,
  useSharedValue,
  withSequence,
  withTiming,
  type SharedValue,
} from 'react-native-reanimated';

import { metal } from './theme.ts';

type Point = { x: number; y: number };

type Props = {
  pin: ImageSourcePropType;
  from: Point;
  to: Point;
  onLanded: () => void;
  onDone: () => void;
};

const SIZE = 64;
const LIFT_MS = 160;
const FLIGHT_MS = 650;
/** Matches the ring's tick in CollectorHud. */
const SPARK_MS = 425;
const SPARKS = 7;

export default function CollectFlight({ pin, from, to, onLanded, onDone }: Props) {
  // 0 to 1 lifts it off the button, 1 to 2 flies it, 2 to 3 sparks.
  const p = useSharedValue(0);
  // The animation is started once; what it calls back is this render's.
  const calls = useRef({ onLanded, onDone });
  calls.current = { onLanded, onDone };
  useEffect(() => {
    const landed = () => calls.current.onLanded();
    const done = () => calls.current.onDone();
    p.value = withSequence(
      withTiming(1, { duration: LIFT_MS, easing: Easing.out(Easing.cubic) }),
      withTiming(2, { duration: FLIGHT_MS, easing: Easing.inOut(Easing.quad) }, (fin) => {
        if (fin) runOnJS(landed)();
      }),
      withTiming(3, { duration: SPARK_MS, easing: Easing.out(Easing.cubic) }, (fin) => {
        if (fin) runOnJS(done)();
      }),
    );
  }, [p]);

  const lift = { x: from.x, y: from.y - 18 };
  // Out to the left and low, so it swings up into the corner.
  const bend = { x: lift.x - 30, y: to.y + 120 };
  const locket = useAnimatedStyle(() => {
    const v = p.value;
    if (v <= 1)
      return {
        opacity: v,
        transform: [
          { translateX: from.x - SIZE / 2 },
          { translateY: from.y - 18 * v - SIZE / 2 },
          { scale: 0.35 + 0.75 * v },
        ],
      };
    const e = Math.min(1, v - 1);
    const u = 1 - e;
    return {
      opacity: e > 0.9 ? (1 - e) * 10 : 1,
      transform: [
        { translateX: u * u * lift.x + 2 * u * e * bend.x + e * e * to.x - SIZE / 2 },
        { translateY: u * u * lift.y + 2 * u * e * bend.y + e * e * to.y - SIZE / 2 },
        { scale: 1.1 - 0.7 * e },
      ],
    };
  });

  return (
    <View style={StyleSheet.absoluteFill} pointerEvents="none">
      <Animated.Image source={pin} style={[styles.locket, locket]} />
      {Array.from({ length: SPARKS }, (_, i) => (
        <Spark key={i} p={p} at={to} angle={(i / SPARKS) * 2 * Math.PI} />
      ))}
    </View>
  );
}

function Spark({ p, at, angle }: { p: SharedValue<number>; at: Point; angle: number }) {
  const style = useAnimatedStyle(() => {
    const t = Math.max(0, p.value - 2);
    const r = 44 * (1 - (1 - t) ** 3);
    return {
      opacity: p.value < 2 ? 0 : 1 - t,
      transform: [
        { translateX: at.x - 3 + Math.cos(angle) * r },
        { translateY: at.y - 3 + Math.sin(angle) * r },
      ],
    };
  });
  return <Animated.View style={[styles.spark, style]} />;
}

const styles = StyleSheet.create({
  locket: { position: 'absolute', width: SIZE, height: SIZE, resizeMode: 'contain' },
  spark: {
    position: 'absolute',
    width: 6,
    height: 6,
    borderRadius: 3,
    backgroundColor: metal.inner,
  },
});
