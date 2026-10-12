/** Your Collector across the top of the map, like a game's status bar: the
 *  medal, the rank, and the bar to the next one. Never over a memory: App
 *  hides it while one is up (UI.md rule 13). Tapped, it opens its page. */

import { Pressable, StyleSheet, Text, View } from 'react-native';

import { STAGES, classOf, rankInto, wants, wantsWords } from './collector.ts';
import type { ClassId } from './collector.ts';
import { Bar, Medal, Velvet } from './Game.tsx';
import { color, font } from './theme.ts';

type Props = {
  id: ClassId;
  stage: number;
  lockets: number;
  filed: number;
  /** The walk's: one line, a smaller medal. */
  compact?: boolean;
  onPress?: () => void;
};

export default function CollectorHud({ id, stage, lockets, filed, compact, onPress }: Props) {
  const { name, ranks } = classOf(id);
  const top = stage + 1 >= STAGES.length;
  const next = top ? null : STAGES[stage + 1];
  const want = wants(stage, lockets, filed);
  const words = want ? wantsWords(want) : '';
  const say =
    `Your Collector, ${ranks[stage]}, rank ${stage + 1} of ${STAGES.length}.` +
    (words ? ` ${words} to ${ranks[stage + 1]}.` : '');
  return (
    <Pressable
      accessibilityRole="button"
      accessibilityLabel={say}
      testID="collector-hud"
      onPress={onPress}
      style={({ pressed }) => [styles.press, pressed && styles.pressed]}
    >
      <Velvet style={[styles.plate, compact && styles.plateCompact]}>
        <Medal id={id} stage={stage} size={compact ? 44 : 58} />
        <View style={styles.who}>
          {compact ? (
            <View style={styles.line}>
              <Text style={[styles.rank, styles.rankCompact]} numberOfLines={1}>
                {ranks[stage]}
              </Text>
              {next !== null && (
                <Text style={styles.count}>
                  {lockets} / {next}
                </Text>
              )}
            </View>
          ) : (
            <>
              <Text style={styles.cls} numberOfLines={1}>
                {`${name} · Rank ${stage + 1} of ${STAGES.length}`.toUpperCase()}
              </Text>
              <Text style={styles.rank} numberOfLines={1}>
                {ranks[stage]}
              </Text>
            </>
          )}
          <Bar into={rankInto(stage, lockets, filed)} height={compact ? 8 : 10} />
          {!compact && next !== null && (
            <View style={styles.line}>
              <Text style={styles.xp}>
                {lockets} / {next} lockets
              </Text>
              <Text style={styles.xp}>→ {ranks[stage + 1]}</Text>
            </View>
          )}
        </View>
      </Velvet>
    </Pressable>
  );
}

const styles = StyleSheet.create({
  press: { flex: 1 },
  pressed: { transform: [{ scale: 0.97 }] },
  plate: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 10,
    padding: 5,
    paddingRight: 16,
    borderRadius: 40,
    borderWidth: 1.5,
    borderColor: color.edge,
  },
  plateCompact: { padding: 4, paddingRight: 14 },
  who: { flex: 1, minWidth: 0, gap: 3 },
  line: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'baseline' },
  cls: { ...font.display, fontSize: 10, letterSpacing: 1.4, color: color.onVelvetGold },
  rank: { ...font.title, fontSize: 20, lineHeight: 24, color: color.onVelvet },
  rankCompact: { fontSize: 17, lineHeight: 21, flexShrink: 1 },
  count: { ...font.uiBold, fontSize: 12, color: color.onVelvetGold },
  xp: { ...font.uiBold, fontSize: 12, color: color.onVelvetSoft },
});
