/** Rank up: the one loud moment (docs/10, "The Collector"). Done on a walk
 *  that crossed a stage opens it over the map: the old look in its plate, a
 *  gathering gold light with two light taps, then the new look springs in
 *  with a success haptic, its rank and count rise, one tap on. With no old
 *  look it is the one-time "You're already" for lockets opened before the
 *  Collector: the plate and the light, still. Never on the unlock and never
 *  over a memory. Reduce Motion: a crossfade, no rays, no growth. */

import { useEffect, useRef } from 'react';
import { Animated, Easing, Image, StyleSheet, Text, View } from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import Svg, { Circle, Defs, Path, RadialGradient, Stop } from 'react-native-svg';
import * as Haptics from 'expo-haptics';

import Button from './Button.tsx';
import CollectorLook from './CollectorLook.tsx';
import Plate from './Plate.tsx';
import { STAGES, classOf, type ClassId } from './collector.ts';
import { locketOf } from './lockets.ts';
import { useReduceMotion } from './useBreath.ts';
import { color, foil, font, label, metal, screenTitle } from './theme.ts';
import { Foil, Velvet } from './Game.tsx';

type Props = {
  id: ClassId;
  /** The stage before; null for "You're already". */
  from: number | null;
  to: number;
  lockets: number;
  filed: number;
  onDone: () => void;
};

const LOOK = 220;
const LIGHT = 340;
/** Twelve thin rays from the middle, drawn once in a 100 box. */
const RAYS = Array.from({ length: 12 }, (_, i) => {
  const a = (i * Math.PI) / 6;
  const at = (r: number, d: number) =>
    `${(50 + r * Math.cos(a + d)).toFixed(2)} ${(50 + r * Math.sin(a + d)).toFixed(2)}`;
  return `M${at(6, -0.05)} L${at(50, 0)} L${at(6, 0.05)} Z`;
}).join(' ');

export default function RankUp({ id, from, to, lockets, filed, onDone }: Props) {
  const insets = useSafeAreaInsets();
  const reduceMotion = useReduceMotion();
  const still = from === null;
  const glow = useRef(new Animated.Value(still ? 1 : 0)).current;
  const breath = useRef(new Animated.Value(0)).current;
  const shown = useRef(new Animated.Value(still ? 1 : 0)).current;
  const words = useRef(new Animated.Value(still ? 1 : 0)).current;
  const turn = useRef(new Animated.Value(0)).current;
  const rank = classOf(id).ranks[to];

  useEffect(() => {
    const tap = () => Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Light).catch(() => {});
    const done = () =>
      Haptics.notificationAsync(Haptics.NotificationFeedbackType.Success).catch(() => {});
    const spin = Animated.loop(
      Animated.timing(turn, {
        toValue: 1,
        duration: 24000,
        easing: Easing.linear,
        useNativeDriver: true,
      }),
    );
    if (!reduceMotion) spin.start();
    if (still) {
      [glow, shown, words].forEach((v) => v.setValue(1));
      done();
      return () => spin.stop();
    }
    const taps: ReturnType<typeof setTimeout>[] = [];
    const run = reduceMotion
      ? Animated.sequence([
          Animated.delay(900),
          Animated.parallel([
            Animated.timing(glow, { toValue: 1, duration: 400, useNativeDriver: true }),
            Animated.timing(shown, { toValue: 1, duration: 400, useNativeDriver: true }),
            Animated.timing(words, { toValue: 1, duration: 400, useNativeDriver: true }),
          ]),
        ])
      : Animated.sequence([
          Animated.delay(900),
          // The gathering: the light comes up and the old look draws breath.
          Animated.parallel([
            Animated.timing(glow, { toValue: 1, duration: 600, useNativeDriver: true }),
            Animated.timing(breath, {
              toValue: 1,
              duration: 600,
              easing: Easing.inOut(Easing.quad),
              useNativeDriver: true,
            }),
          ]),
          Animated.spring(shown, {
            toValue: 1,
            damping: 9,
            stiffness: 140,
            useNativeDriver: true,
          }),
        ]);
    if (!reduceMotion) {
      taps.push(setTimeout(tap, 900), setTimeout(tap, 1200));
      // The change lands as the spring first reaches the new look.
      taps.push(
        setTimeout(() => {
          done();
          Animated.timing(words, {
            toValue: 1,
            duration: 360,
            delay: 200,
            useNativeDriver: true,
          }).start();
        }, 1700),
      );
    }
    run.start(({ finished }) => finished && reduceMotion && done());
    return () => {
      run.stop();
      spin.stop();
      taps.forEach(clearTimeout);
    };
  }, [still, reduceMotion, glow, breath, shown, words, turn]);

  const motion = !reduceMotion;
  const rays = motion
    ? [{ rotate: turn.interpolate({ inputRange: [0, 1], outputRange: ['0deg', '360deg'] }) }]
    : [];
  const breathe = motion
    ? [{ scale: breath.interpolate({ inputRange: [0, 1], outputRange: [1, 1.04] }) }]
    : [];
  const grow = motion
    ? [{ scale: shown.interpolate({ inputRange: [0, 1], outputRange: [0.85, 1] }) }]
    : [];
  const rise = motion
    ? [{ translateY: words.interpolate({ inputRange: [0, 1], outputRange: [12, 0] }) }]
    : [];
  return (
    <Velvet
      style={[styles.screen, { paddingTop: insets.top + 32, paddingBottom: insets.bottom + 16 }]}
      accessibilityViewIsModal
      testID="rank-up"
    >
      {!still && (
        <Foil style={styles.banner}>
          <Text style={styles.bannerText}>RANK UP</Text>
        </Foil>
      )}
      <Text style={styles.over}>
        {still ? 'Your Collector' : `Rank ${to + 1} of ${STAGES.length}`}
      </Text>
      <View style={styles.stage}>
        <Animated.View style={[styles.light, { opacity: glow }]} pointerEvents="none">
          <Svg width={LIGHT} height={LIGHT} viewBox="0 0 100 100">
            <Defs>
              <RadialGradient id="gather">
                <Stop offset="0" stopColor={metal.mid} stopOpacity={0.55} />
                <Stop offset="0.5" stopColor={metal.light} stopOpacity={0.3} />
                <Stop offset="1" stopColor={metal.light} stopOpacity={0} />
              </RadialGradient>
            </Defs>
            <Circle cx="50" cy="50" r="50" fill="url(#gather)" />
          </Svg>
        </Animated.View>
        {motion && (
          <Animated.View
            style={[styles.light, { opacity: glow, transform: rays }]}
            pointerEvents="none"
          >
            <Svg width={LIGHT} height={LIGHT} viewBox="0 0 100 100">
              <Path d={RAYS} fill={metal.mid} opacity={0.45} />
            </Svg>
          </Animated.View>
        )}
        <Plate size={LOOK} on>
          {from !== null && (
            <Animated.View
              style={[
                StyleSheet.absoluteFill,
                styles.center,
                { opacity: Animated.subtract(1, shown), transform: breathe },
              ]}
            >
              <CollectorLook id={id} stage={from} size={LOOK - 16} />
            </Animated.View>
          )}
          <Animated.View style={[styles.center, { opacity: shown, transform: grow }]}>
            <CollectorLook id={id} stage={to} size={LOOK - 16} />
          </Animated.View>
        </Plate>
      </View>
      <Animated.View style={[styles.words, { opacity: words, transform: rise }]} accessible>
        <Text style={styles.title} accessibilityRole="header">
          {still ? `You're already ${rank}.` : rank}
        </Text>
        <View style={styles.count}>
          <Image source={locketOf().pin} style={styles.locket} />
          <Text style={styles.body}>
            {`${lockets} ${lockets === 1 ? 'locket' : 'lockets'} · ${filed} added`}
          </Text>
        </View>
      </Animated.View>
      <View style={styles.foot}>
        <Button kind="foil" label="Go on" onPress={onDone} />
      </View>
    </Velvet>
  );
}

const styles = StyleSheet.create({
  screen: {
    position: 'absolute',
    top: 0,
    left: 0,
    right: 0,
    bottom: 0,
    paddingHorizontal: 24,
    alignItems: 'center',
  },
  stage: {
    width: LIGHT,
    height: LIGHT,
    marginTop: 8,
    alignItems: 'center',
    justifyContent: 'center',
  },
  light: { position: 'absolute', top: 0, left: 0 },
  center: { flex: 1, alignItems: 'center', justifyContent: 'center' },
  words: { marginTop: 12, gap: 12, alignItems: 'center' },
  banner: { paddingHorizontal: 26, paddingVertical: 8, borderRadius: 6, marginBottom: 12 },
  bannerText: { ...font.display, fontSize: 15, letterSpacing: 4, color: foil.text },
  over: { ...label, letterSpacing: 1.4, color: color.onVelvetGold },
  title: { ...screenTitle, textAlign: 'center', color: color.onVelvet },
  count: { flexDirection: 'row', alignItems: 'center', gap: 8 },
  locket: { width: 18, height: 18 },
  body: { ...font.prose, fontSize: 17, lineHeight: 25, color: color.onVelvetSoft },
  foot: { flex: 1, justifyContent: 'flex-end', alignSelf: 'stretch' },
});
