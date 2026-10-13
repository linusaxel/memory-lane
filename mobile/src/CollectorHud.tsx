/** Your Collector at the top left of the map: the portrait, its rank on the
 *  coin, and a plum ring round it filling toward the next rank. No card, no
 *  words (docs/10, "The Collector is a portrait"). Never over a memory: App
 *  hides it while one is up (UI.md rule 13). Tapped, it opens its page. The
 *  ring ticks forward when it rises, and the portrait pops: a collected locket
 *  landing (CollectFlight). Down, a new rank, or Reduce Motion: it snaps. */

import { useEffect } from 'react';
import { Pressable, StyleSheet } from 'react-native';
import Animated, {
  Easing,
  useAnimatedProps,
  useAnimatedStyle,
  useSharedValue,
  withSequence,
  withTiming,
} from 'react-native-reanimated';
import Svg, { Circle } from 'react-native-svg';

import { STAGES, classOf, rankInto, wants, wantsWords } from './collector.ts';
import type { ClassId } from './collector.ts';
import { Medal } from './Game.tsx';
import { ACircle } from './lockets/parts.tsx';
import { color, glassLift } from './theme.ts';
import { useReduceMotion } from './useBreath.ts';

type Props = {
  id: ClassId;
  stage: number;
  lockets: number;
  filed: number;
  onPress?: () => void;
};

const MEDAL = 56;
const STROKE = 4;
/** Where a collected locket lands: App's `top` row puts the HUD at its start. */
export const SIZE = MEDAL + 2 * (STROKE + 2);
const R = (SIZE - STROKE) / 2;
const ROUND = 2 * Math.PI * R;
const TICK_MS = 425;

export default function CollectorHud({ id, stage, lockets, filed, onPress }: Props) {
  const { ranks } = classOf(id);
  const want = wants(stage, lockets, filed);
  const words = want ? wantsWords(want) : '';
  const say =
    `Your Collector, ${ranks[stage]}, rank ${stage + 1} of ${STAGES.length}.` +
    (words ? ` ${words} to the next rank.` : '');
  const into = rankInto(stage, lockets, filed);
  const still = useReduceMotion();
  const fill = useSharedValue(into);
  const pop = useSharedValue(1);
  useEffect(() => {
    if (into <= fill.value || still) {
      fill.value = into;
      return;
    }
    fill.value = withTiming(into, { duration: TICK_MS, easing: Easing.out(Easing.cubic) });
    pop.value = withSequence(withTiming(1.14, { duration: 170 }), withTiming(1, { duration: 210 }));
  }, [into, still, fill, pop]);
  const ring = useAnimatedProps(() => ({ strokeDashoffset: ROUND * (1 - fill.value) }));
  const popped = useAnimatedStyle(() => ({ transform: [{ scale: pop.value }] }));
  return (
    <Pressable
      accessibilityRole="button"
      accessibilityLabel={say}
      testID="collector-hud"
      hitSlop={4}
      onPress={onPress}
      style={({ pressed }) => [styles.press, pressed && styles.pressed]}
    >
      <Svg width={SIZE} height={SIZE} style={StyleSheet.absoluteFill}>
        <Circle
          cx={SIZE / 2}
          cy={SIZE / 2}
          r={R}
          stroke={color.track}
          strokeWidth={STROKE}
          fill="none"
        />
        <ACircle
          cx={SIZE / 2}
          cy={SIZE / 2}
          r={R}
          stroke={color.plum}
          strokeWidth={STROKE}
          strokeLinecap="round"
          strokeDasharray={ROUND}
          animatedProps={ring}
          fill="none"
          transform={`rotate(-90 ${SIZE / 2} ${SIZE / 2})`}
        />
      </Svg>
      <Animated.View style={[styles.medal, popped]}>
        <Medal id={id} stage={stage} size={MEDAL} />
      </Animated.View>
    </Pressable>
  );
}

const styles = StyleSheet.create({
  press: { width: SIZE, height: SIZE, ...glassLift },
  pressed: { transform: [{ scale: 0.94 }] },
  medal: { position: 'absolute', top: STROKE + 2, left: STROKE + 2 },
});
