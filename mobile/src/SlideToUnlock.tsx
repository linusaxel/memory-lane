/** The track under the locket, as iOS draws slide to power off: a foil knob
 *  with a key on green enamel and one shimmering line, in place of the bottom
 *  row while a memory is in reach. Slide the knob to open it. It
 *  scrubs the locket's own hold (LocketUnlock's `scrub`), so the key turns
 *  under your thumb and rewinds as you slide back; letting go short springs
 *  it shut, and the end commits. Holding the locket moves the thumb too: one
 *  progress, two ways to drive it (docs/10, "Slide to unlock"). */

import { useEffect, useRef, type RefObject } from 'react';
import { PanResponder, StyleSheet, Text, View } from 'react-native';
import Animated, {
  type SharedValue,
  useAnimatedStyle,
  useReducedMotion,
  useSharedValue,
  withRepeat,
  withTiming,
} from 'react-native-reanimated';

import { LinearGradient } from 'expo-linear-gradient';
import Icon from './Icon.tsx';
import type { LocketDrive } from './LocketUnlock.tsx';
import { clamp } from './lockets/math.ts';
import { color, foil, font, lift, radius } from './theme.ts';

type Props = {
  drive: RefObject<LocketDrive | null>;
  /** The locket's hold, shared with it. */
  progress: SharedValue<number>;
  /** Said to VoiceOver, so the track names what it opens. */
  placeName: string;
};

export default function SlideToUnlock({ drive, progress, placeName }: Props) {
  const reduce = useReducedMotion();
  const range = useSharedValue(1);
  const shimmer = useSharedValue(1);
  const from = useRef(0);

  useEffect(() => {
    if (!reduce) shimmer.value = withRepeat(withTiming(0.45, { duration: 1100 }), -1, true);
  }, [reduce, shimmer]);

  const pan = useRef(
    PanResponder.create({
      onStartShouldSetPanResponder: () => true,
      onPanResponderTerminationRequest: () => false,
      onPanResponderGrant: () => {
        from.current = clamp(progress.value, 0, 1);
        drive.current?.scrub(from.current);
      },
      onPanResponderMove: (_, g) => drive.current?.scrub(from.current + g.dx / range.value),
      onPanResponderRelease: () => drive.current?.release(),
      onPanResponderTerminate: () => drive.current?.release(),
    }),
  ).current;

  const thumbStyle = useAnimatedStyle(() => ({
    transform: [{ translateX: clamp(progress.value, 0, 1) * range.value }],
  }));
  const wordsStyle = useAnimatedStyle(() => ({
    opacity: 1 - clamp(progress.value * 2.5, 0, 1),
  }));
  const shimmerStyle = useAnimatedStyle(() => ({ opacity: shimmer.value }));

  return (
    <View
      style={styles.track}
      onLayout={(e) => (range.value = e.nativeEvent.layout.width - 2 * PAD - THUMB)}
      accessible
      accessibilityRole="button"
      accessibilityLabel={`Slide to unlock, ${placeName}`}
      accessibilityHint="Or press and hold the locket."
      accessibilityActions={[{ name: 'activate' }]}
      onAccessibilityAction={() => drive.current?.open()}
      testID="slide-to-unlock"
    >
      <View style={styles.rim} pointerEvents="none" />
      <Animated.View style={[styles.words, wordsStyle]} pointerEvents="none">
        <Animated.View style={[styles.say, shimmerStyle]}>
          <Text style={styles.slide}>Slide to unlock</Text>
          <Icon name="slide" size={18} color={color.onGo} />
        </Animated.View>
      </Animated.View>
      <Animated.View style={[styles.thumb, thumbStyle]} {...pan.panHandlers}>
        <LinearGradient
          colors={foil.colors}
          locations={[0, 0.5, 1]}
          style={StyleSheet.absoluteFill}
          pointerEvents="none"
        />
        <View pointerEvents="none">
          <Icon name="key" size={26} color={foil.text} tone={color.paperRaised} />
        </View>
      </Animated.View>
    </View>
  );
}

const THUMB = 54;
const PAD = 5;

const styles = StyleSheet.create({
  // Green enamel, as every go is, with a foil knob carrying the key.
  track: {
    alignSelf: 'stretch',
    height: THUMB + 2 * PAD,
    justifyContent: 'center',
    borderRadius: radius.pill,
    backgroundColor: color.goBg,
    ...lift,
  },
  rim: {
    ...StyleSheet.absoluteFill,
    margin: 4,
    borderRadius: radius.pill,
    borderWidth: 1,
    borderColor: color.goRim,
  },
  say: { flexDirection: 'row', alignItems: 'center', gap: 8 },
  words: {
    ...StyleSheet.absoluteFill,
    alignItems: 'center',
    justifyContent: 'center',
    paddingLeft: THUMB + 2 * PAD,
    paddingRight: 16,
  },
  slide: { ...font.uiBold, fontSize: 21, color: color.onGo },
  thumb: {
    position: 'absolute',
    left: PAD,
    width: THUMB,
    height: THUMB,
    borderRadius: THUMB / 2,
    overflow: 'hidden',
    alignItems: 'center',
    justifyContent: 'center',
  },
});
