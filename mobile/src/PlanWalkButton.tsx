/** Plan a walk, the gold glass pill on home. A tap walks the figure through
 *  its label as the letters part, and when he arrives (0.9 s) `onWalkEnd`
 *  opens the planner. Reduce Motion skips the walk.
 *
 *  The figure is native Views, not SVG, so every joint animates on the UI
 *  thread: a two-link leg per frame, sampled into the arrays below, 180 ms a
 *  stride. Adapted from the designer's handoff (4.3c, the walk alone).
 */

import { useCallback, useEffect, useMemo, useRef, useState, type ReactNode } from 'react';
import {
  StyleSheet,
  View,
  type ColorValue,
  type LayoutChangeEvent,
  type StyleProp,
  type ViewStyle,
} from 'react-native';
import Animated, {
  cancelAnimation,
  Easing,
  runOnJS,
  useAnimatedStyle,
  useDerivedValue,
  useReducedMotion,
  useSharedValue,
  withTiming,
  type SharedValue,
} from 'react-native-reanimated';

import { GlassButton } from './Glass';
import { buttonText, color } from './theme';

const LABEL = 'Plan a walk';
const FIGURE = 20;
const FIGURE_GAP = 8;

const CYCLE_MS = 180;
const WALK_MS = 900;
const START_MS = 42;

// One stride, 41 samples, phase 0 = front heel lands. Degrees, clockwise.
const THIGH = [
  -39.1, -36.8, -33.7, -36.7, -32.6, -28.7, -24.9, -21.2, -17.5, -13.9, -10.3, -6.7, -3.2, 0.4, 3.6,
  5.8, 7.5, 9.2, 11.1, 13.3, 17.3, 23.9, 36.0, 43.5, 37.9, 26.6, 15.8, 4.7, -6.6, -17.8, -28.4,
  -37.6, -44.6, -48.7, -49.6, -46.5, -33.5, -36.5, -38.5, -39.5, -39.1,
];
const SHIN = [
  0.0, 0.0, 0.0, 13.7, 13.6, 13.6, 13.5, 13.5, 13.5, 13.5, 13.5, 13.5, 13.5, 13.5, 14.3, 17.4, 21.6,
  26.3, 31.1, 35.9, 37.1, 32.0, 14.4, 0.0, 8.9, 26.8, 41.4, 53.9, 64.0, 71.3, 75.2, 75.2, 71.3,
  63.4, 51.4, 34.3, 0.0, 0.0, 0.0, 0.0, 0.0,
];
const ARM = [
  64.1, 65.0, 64.6, 62.9, 60.0, 55.9, 50.8, 44.7, 37.8, 30.3, 22.3, 14.1, 5.9, -2.1, -9.9, -17.0,
  -23.4, -29.0, -33.5, -36.9, -39.1, -40.0, -39.6, -37.9, -35.0, -30.9, -25.8, -19.7, -12.8, -5.3,
  2.7, 10.9, 19.1, 27.1, 34.9, 42.0, 48.4, 54.0, 58.5, 61.9, 64.1,
];
const FORE = [
  -67.9, -69.0, -68.5, -66.6, -63.4, -59.2, -54.4, -49.3, -44.4, -40.0, -36.6, -34.3, -33.3, -33.5,
  -34.9, -37.2, -40.0, -43.1, -46.1, -48.5, -50.2, -51.0, -50.7, -49.3, -47.1, -44.3, -41.3, -38.3,
  -35.7, -33.9, -33.2, -33.7, -35.5, -38.5, -42.5, -47.3, -52.3, -57.3, -61.9, -65.5, -67.9,
];
const BOB = [
  0.48, 0.65, 0.48, 0.05, -0.48, -0.93, -1.29, -1.58, -1.81, -1.96, -2.06, -2.09, -2.06, -1.96,
  -1.81, -1.58, -1.29, -0.93, -0.48, 0.05, 0.48, 0.65, 0.48, 0.05, -0.48, -0.93, -1.29, -1.58,
  -1.81, -1.96, -2.06, -2.09, -2.06, -1.96, -1.81, -1.58, -1.29, -0.93, -0.48, 0.05, 0.48,
];

// At rest he is the walk icon; B is where the trailing leg is at START_MS.
const REST_A = { th: -30, sh: 0, ar: 65, fa: -65 };
const REST_B = { th: 30, sh: 0, ar: -40, fa: -51 };
const START_B = { th: -21.3, sh: 72.9 };

const clamp01 = (x: number) => {
  'worklet';
  return x < 0 ? 0 : x > 1 ? 1 : x;
};
const easeOutCubic = (x: number) => {
  'worklet';
  return 1 - Math.pow(1 - x, 3);
};
const sample = (arr: number[], p: number) => {
  'worklet';
  const f = p * 40;
  const i = Math.min(39, Math.max(0, Math.floor(f)));
  return arr[i] + (arr[i + 1] - arr[i]) * (f - i);
};
const phase = (t: number, offset: number) => {
  'worklet';
  const c = Math.min(t, WALK_MS) / CYCLE_MS + offset;
  return c - Math.floor(c);
};
const joint = (
  t: number,
  active: number,
  arr: number[],
  offset: number,
  rest: number,
  start?: number,
) => {
  'worklet';
  if (!active) return rest;
  if (start !== undefined && t < START_MS) return rest + (start - rest) * (t / START_MS);
  return sample(arr, phase(t, offset));
};

/** The figure is drawn in a 40 × 46 unit box, x from 4 to 44. */
const K = FIGURE / 46;
type Pt = { x: number; y: number };
const P = (x: number, y: number): Pt => ({ x: (x - 4) * K, y: y * K });

function Limb({
  pivot,
  length,
  width,
  fill,
  angle,
  children,
}: {
  pivot: Pt;
  length: number;
  width: number;
  fill: ColorValue;
  angle: SharedValue<number>;
  children?: ReactNode;
}) {
  const a = -length / 2;
  const style = useAnimatedStyle(() => ({
    transform: [{ translateY: a }, { rotate: `${angle.value}deg` }, { translateY: -a }],
  }));
  return (
    <Animated.View
      style={[
        {
          position: 'absolute',
          left: pivot.x - width / 2,
          top: pivot.y - width / 2,
          width,
          height: length + width,
          borderRadius: width / 2,
          backgroundColor: fill,
        },
        style,
      ]}
    >
      {children}
    </Animated.View>
  );
}

function Figure({
  t,
  active,
  ink,
  halo,
}: {
  t: SharedValue<number>;
  active: SharedValue<number>;
  ink: ColorValue;
  halo: ColorValue;
}) {
  const thA = useDerivedValue(() => joint(t.value, active.value, THIGH, 0, REST_A.th));
  const shA = useDerivedValue(() => joint(t.value, active.value, SHIN, 0, REST_A.sh));
  const arA = useDerivedValue(() => joint(t.value, active.value, ARM, 0, REST_A.ar));
  const faA = useDerivedValue(() => joint(t.value, active.value, FORE, 0, REST_A.fa));
  const thB = useDerivedValue(() =>
    joint(t.value, active.value, THIGH, 0.5, REST_B.th, START_B.th),
  );
  const shB = useDerivedValue(() => joint(t.value, active.value, SHIN, 0.5, REST_B.sh, START_B.sh));
  const arB = useDerivedValue(() => joint(t.value, active.value, ARM, 0.5, REST_B.ar));
  const faB = useDerivedValue(() => joint(t.value, active.value, FORE, 0.5, REST_B.fa));
  const bob = useAnimatedStyle(() => ({
    transform: [{ translateY: active.value ? sample(BOB, phase(t.value, 0)) * K : 0 }],
  }));

  // The halo widths are a limb plus a gap in the button's colour, so the
  // near limbs read in front of the far ones.
  const w = 3.8 * K;
  const hw = 6.6 * K;
  const thigh = 8.1 * K;
  const upper = 7.5 * K;
  const fore = 7 * K;
  const hip = P(21.5, 28.5);
  const shoulder = P(21.5, 14);
  const head = P(23.6, 4.9);
  const r = 4.4 * K;

  const leg = (
    width: number,
    fill: ColorValue,
    th: SharedValue<number>,
    sh: SharedValue<number>,
  ) => (
    <Limb pivot={hip} length={thigh} width={width} fill={fill} angle={th}>
      <Limb
        pivot={{ x: width / 2, y: width / 2 + thigh }}
        length={thigh}
        width={width}
        fill={fill}
        angle={sh}
      />
    </Limb>
  );
  const arm = (
    width: number,
    fill: ColorValue,
    ar: SharedValue<number>,
    fa: SharedValue<number>,
  ) => (
    <Limb pivot={shoulder} length={upper} width={width} fill={fill} angle={ar}>
      <Limb
        pivot={{ x: width / 2, y: width / 2 + upper }}
        length={fore}
        width={width}
        fill={fill}
        angle={fa}
      />
    </Limb>
  );
  const torso = (width: number, fill: ColorValue) => {
    const top = P(21.5, 14.7);
    const bottom = P(21.5, 26.5);
    return (
      <View
        style={{
          position: 'absolute',
          left: top.x - width / 2,
          top: top.y - width / 2,
          width,
          height: bottom.y - top.y + width,
          borderRadius: width / 2,
          backgroundColor: fill,
        }}
      />
    );
  };

  return (
    <View style={{ width: 40 * K, height: 46 * K }}>
      <Animated.View style={[StyleSheet.absoluteFill, bob]}>
        {leg(w, ink, thB, shB)}
        {arm(w, ink, arA, faA)}
        {torso(10 * K, halo)}
        {leg(hw, halo, thA, shA)}
        {torso(7.2 * K, ink)}
        {leg(w, ink, thA, shA)}
        {arm(hw, halo, arB, faB)}
        {arm(w, ink, arB, faB)}
        <View
          style={{
            position: 'absolute',
            left: head.x - r,
            top: head.y - r,
            width: 2 * r,
            height: 2 * r,
            borderRadius: r,
            backgroundColor: ink,
          }}
        />
      </Animated.View>
    </View>
  );
}

function Letter({
  ch,
  index,
  start,
  t,
  active,
  onLayout,
}: {
  ch: string;
  index: number;
  start: number;
  t: SharedValue<number>;
  active: SharedValue<number>;
  onLayout: (e: LayoutChangeEvent) => void;
}) {
  const style = useAnimatedStyle(() => {
    const e = active.value ? easeOutCubic(clamp01((t.value - start) / 300)) : 0;
    return {
      opacity: 1 - e,
      transform: [{ translateY: (index % 2 === 0 ? -14 : 14) * e }, { scale: 1 - 0.3 * e }],
    };
  });
  return (
    <Animated.Text onLayout={onLayout} style={[styles.letter, style]}>
      {ch}
    </Animated.Text>
  );
}

export function PlanWalkButton({
  place,
  style,
  onPress,
  onWalkEnd,
}: {
  place?: StyleProp<ViewStyle>;
  style?: StyleProp<ViewStyle>;
  /** On tap, for the haptic. */
  onPress: () => void;
  /** When the figure arrives. */
  onWalkEnd: () => void;
}) {
  const reduceMotion = useReducedMotion();
  const chars = useMemo(() => Array.from(LABEL), []);

  const t = useSharedValue(0);
  const active = useSharedValue(0);
  const travel = useSharedValue(140);
  const busy = useRef(false);

  const [fig, setFig] = useState<{ x: number; w: number } | null>(null);
  const [lab, setLab] = useState<{ x: number; w: number } | null>(null);
  const [boxes, setBoxes] = useState<number[]>([]);

  const geo = useMemo(() => {
    if (!fig || !lab) return null;
    const dist = Math.max(40, lab.x + lab.w + 6 - fig.x);
    const starts = chars.map((_, i) =>
      boxes[i] == null
        ? 0
        : Math.max(0, ((lab.x + boxes[i] - (fig.x + fig.w)) / dist) * WALK_MS - 40),
    );
    return { dist, starts };
  }, [fig, lab, boxes, chars]);

  useEffect(() => {
    if (geo) travel.value = geo.dist;
  }, [geo, travel]);
  useEffect(() => () => cancelAnimation(t), [t]);

  const finish = useCallback(() => {
    busy.current = false;
    onWalkEnd();
  }, [onWalkEnd]);

  const press = () => {
    if (busy.current) return;
    onPress();
    if (reduceMotion) {
      onWalkEnd();
      return;
    }
    busy.current = true;
    t.value = 0;
    active.value = 1;
    t.value = withTiming(WALK_MS, { duration: WALK_MS, easing: Easing.linear }, (done) => {
      if (done) runOnJS(finish)();
    });
  };

  const walker = useAnimatedStyle(() => ({
    transform: [
      { translateX: active.value ? (travel.value * Math.min(t.value, WALK_MS)) / WALK_MS : 0 },
    ],
  }));
  return (
    <GlassButton
      place={place}
      style={[style, styles.clip]}
      prominent
      onPress={press}
      accessibilityRole="button"
      accessibilityLabel={LABEL}
    >
      {/* row-reverse, so the figure draws over the letters */}
      <View style={styles.row}>
        <View
          style={styles.label}
          onLayout={(e) => setLab({ x: e.nativeEvent.layout.x, w: e.nativeEvent.layout.width })}
        >
          {chars.map((ch, i) => (
            <Letter
              key={i}
              ch={ch}
              index={i}
              start={geo ? geo.starts[i] : 0}
              t={t}
              active={active}
              onLayout={(e) => {
                const { x } = e.nativeEvent.layout;
                setBoxes((prev) => {
                  const next = prev.slice();
                  next[i] = x;
                  return next;
                });
              }}
            />
          ))}
        </View>
        <Animated.View
          style={[{ marginRight: FIGURE_GAP }, walker]}
          onLayout={(e) => setFig({ x: e.nativeEvent.layout.x, w: e.nativeEvent.layout.width })}
        >
          <Figure t={t} active={active} ink={color.onGo} halo={color.goBg} />
        </Animated.View>
      </View>
    </GlassButton>
  );
}

const styles = StyleSheet.create({
  clip: { overflow: 'hidden' },
  row: { flexDirection: 'row-reverse', alignItems: 'center' },
  label: { flexDirection: 'row', alignItems: 'center' },
  letter: { ...buttonText, color: color.onGo },
});
