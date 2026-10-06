/** A memory just filed: its locket shuts over the map, then drops onto the
 *  spot it was filed at, and the sheet opens on it. The first one ever holds a
 *  beat longer and says what just happened. docs/10, "Writing is a calm page". */

import { useEffect, useState } from 'react';
import { StyleSheet, View, useWindowDimensions } from 'react-native';
import Animated, {
  Easing,
  runOnJS,
  useAnimatedStyle,
  useReducedMotion,
  useSharedValue,
  withDelay,
  withTiming,
} from 'react-native-reanimated';
import * as Haptics from 'expo-haptics';

import LocketUnlock from './LocketUnlock.tsx';
import type { LocketId } from './lockets.ts';
import { color, radius, story } from './theme.ts';

const SIZE = 240;

type Props = {
  locket: LocketId;
  placeName: string;
  /** Where it lands, in screen points: the pin. Null lands in the middle. */
  at: { x: number; y: number } | null;
  first: boolean;
  onLanded: () => void;
};

export default function LocketSeal({ locket, placeName, at, first, onLanded }: Props) {
  const reduce = useReducedMotion();
  const { width, height } = useWindowDimensions();
  const [shut, setShut] = useState(false);
  const drop = useSharedValue(0);

  useEffect(() => {
    if (reduce) onLanded();
    // Once, as it mounts.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const land = () => {
    Haptics.notificationAsync(Haptics.NotificationFeedbackType.Success).catch(() => {});
    onLanded();
  };

  const sealed = () => {
    setShut(true);
    drop.value = withDelay(
      first ? 1600 : 250,
      withTiming(1, { duration: 520, easing: Easing.in(Easing.cubic) }, (fin) => {
        if (fin) runOnJS(land)();
      }),
    );
  };

  const dx = (at?.x ?? width / 2) - width / 2;
  const dy = (at?.y ?? height / 2) - height / 2;
  const moving = useAnimatedStyle(() => ({
    transform: [
      { translateX: dx * drop.value },
      { translateY: dy * drop.value },
      { scale: 1 - 0.85 * drop.value },
    ],
    opacity: 1 - Math.max(drop.value - 0.8, 0) * 5,
  }));
  const words = useAnimatedStyle(() => ({ opacity: 1 - Math.min(drop.value * 4, 1) }));

  if (reduce) return null;
  return (
    <View style={styles.over} pointerEvents="none">
      <Animated.View style={moving}>
        <LocketUnlock
          locket={locket}
          placeName={placeName}
          size={SIZE}
          requestUnlock={async () => false}
          onSealed={sealed}
        />
      </Animated.View>
      {first && shut && (
        <Animated.Text style={[styles.first, words]}>
          Your first memory. Anyone who stands here can open it.
        </Animated.Text>
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  over: { ...StyleSheet.absoluteFill, alignItems: 'center', justifyContent: 'center' },
  first: {
    ...story.body,
    color: color.ink,
    textAlign: 'center',
    position: 'absolute',
    left: 40,
    right: 40,
    top: '50%',
    marginTop: SIZE / 2 + 16,
    padding: 16,
    borderRadius: radius.card,
    backgroundColor: color.paper,
    overflow: 'hidden',
  },
});
