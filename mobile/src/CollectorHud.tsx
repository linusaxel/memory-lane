/** Your Collector at the top left of the map: the portrait, its rank on the
 *  coin, and a plum ring round it filling toward the next rank. No card, no
 *  words (docs/10, "The Collector is a portrait"). Never over a memory: App
 *  hides it while one is up (UI.md rule 13). Tapped, it opens its page. */

import { Pressable, StyleSheet, View } from 'react-native';
import Svg, { Circle } from 'react-native-svg';

import { STAGES, classOf, rankInto, wants, wantsWords } from './collector.ts';
import type { ClassId } from './collector.ts';
import { Medal } from './Game.tsx';
import { color, glassLift } from './theme.ts';

type Props = {
  id: ClassId;
  stage: number;
  lockets: number;
  filed: number;
  onPress?: () => void;
};

const MEDAL = 56;
const STROKE = 4;
const SIZE = MEDAL + 2 * (STROKE + 2);
const R = (SIZE - STROKE) / 2;
const ROUND = 2 * Math.PI * R;

export default function CollectorHud({ id, stage, lockets, filed, onPress }: Props) {
  const { ranks } = classOf(id);
  const want = wants(stage, lockets, filed);
  const words = want ? wantsWords(want) : '';
  const say =
    `Your Collector, ${ranks[stage]}, rank ${stage + 1} of ${STAGES.length}.` +
    (words ? ` ${words} to the next rank.` : '');
  const into = rankInto(stage, lockets, filed);
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
        <Circle
          cx={SIZE / 2}
          cy={SIZE / 2}
          r={R}
          stroke={color.plum}
          strokeWidth={STROKE}
          strokeLinecap="round"
          strokeDasharray={ROUND}
          strokeDashoffset={ROUND * (1 - into)}
          fill="none"
          transform={`rotate(-90 ${SIZE / 2} ${SIZE / 2})`}
        />
      </Svg>
      <View style={styles.medal}>
        <Medal id={id} stage={stage} size={MEDAL} />
      </View>
    </Pressable>
  );
}

const styles = StyleSheet.create({
  press: { width: SIZE, height: SIZE, ...glassLift },
  pressed: { transform: [{ scale: 0.94 }] },
  medal: { position: 'absolute', top: STROKE + 2, left: STROKE + 2 },
});
