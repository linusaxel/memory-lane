/** Rank up: the one loud moment (docs/10, "The Collector"). Done on a walk
 *  that crossed a stage opens it over the map: the old look, a beat, the new
 *  one, its rank and count, a success haptic, one tap on. With no old look it
 *  is the one-time "You're already" for lockets opened before the Collector.
 *  Never on the unlock and never over a memory. Reduce Motion: a crossfade. */

import { useEffect, useRef } from 'react';
import { Animated, Image, StyleSheet, Text, View } from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import * as Haptics from 'expo-haptics';

import Button from './Button.tsx';
import CollectorLook from './CollectorLook.tsx';
import { classOf, type ClassId } from './collector.ts';
import { locketOf } from './lockets.ts';
import { useReduceMotion } from './useBreath.ts';
import { color, font, label, screenTitle } from './theme.ts';

type Props = {
  id: ClassId;
  /** The stage before; null for "You're already". */
  from: number | null;
  to: number;
  lockets: number;
  onDone: () => void;
};

export default function RankUp({ id, from, to, lockets, onDone }: Props) {
  const insets = useSafeAreaInsets();
  const reduceMotion = useReduceMotion();
  const shown = useRef(new Animated.Value(from === null ? 1 : 0)).current;
  const rank = classOf(id).ranks[to];

  useEffect(() => {
    const done = () =>
      Haptics.notificationAsync(Haptics.NotificationFeedbackType.Success).catch(() => {});
    if (from === null) {
      done();
      return;
    }
    // A beat on the old look, then the new one.
    const run = Animated.timing(shown, {
      toValue: 1,
      delay: 900,
      duration: reduceMotion ? 400 : 700,
      useNativeDriver: true,
    });
    run.start(({ finished }) => finished && done());
    return () => run.stop();
  }, [from, reduceMotion, shown]);

  const grow = reduceMotion
    ? []
    : [{ scale: shown.interpolate({ inputRange: [0, 1], outputRange: [0.85, 1] }) }];
  return (
    <View
      style={[styles.screen, { paddingTop: insets.top + 48, paddingBottom: insets.bottom + 16 }]}
      accessibilityViewIsModal
      testID="rank-up"
    >
      <Text style={label}>{from === null ? 'Your Collector' : 'Rank up'}</Text>
      <View style={styles.stage}>
        {from !== null && (
          <Animated.View
            style={[
              StyleSheet.absoluteFill,
              styles.center,
              { opacity: Animated.subtract(1, shown) },
            ]}
          >
            <CollectorLook id={id} stage={from} size={240} />
          </Animated.View>
        )}
        <Animated.View style={[styles.center, { opacity: shown, transform: grow }]}>
          <CollectorLook id={id} stage={to} size={240} />
        </Animated.View>
      </View>
      <View style={styles.words} accessible>
        <Text style={styles.title} accessibilityRole="header">
          {from === null ? `You're already ${rank}.` : rank}
        </Text>
        <View style={styles.count}>
          <Image source={locketOf().pin} style={styles.locket} />
          <Text style={styles.body}>{`${lockets} ${lockets === 1 ? 'locket' : 'lockets'}`}</Text>
        </View>
      </View>
      <View style={styles.foot}>
        <Button kind="go" label="Go on" onPress={onDone} />
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  screen: {
    position: 'absolute',
    top: 0,
    left: 0,
    right: 0,
    bottom: 0,
    backgroundColor: color.paper,
    paddingHorizontal: 24,
    alignItems: 'center',
  },
  stage: { width: 260, height: 260, marginTop: 32 },
  center: { flex: 1, alignItems: 'center', justifyContent: 'center' },
  words: { marginTop: 28, gap: 12, alignItems: 'center' },
  title: { ...screenTitle, textAlign: 'center' },
  count: { flexDirection: 'row', alignItems: 'center', gap: 8 },
  locket: { width: 18, height: 18 },
  body: { ...font.prose, fontSize: 17, lineHeight: 25, color: color.inkSoft },
  foot: { flex: 1, justifyContent: 'flex-end', alignSelf: 'stretch' },
});
