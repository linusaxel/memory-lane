/** What to do next, in words. The only part of the map that moves.
 *
 * A locked pin within reach is the entire point of the product, and it is also
 * easy to walk straight past - one small shape among a dozen. So the map says
 * it, and when it is saying that, it breathes.
 *
 * When nothing is in reach it says how far the nearest lock is instead, which
 * is the other question a map of padlocks leaves you with. Same slot, muted,
 * still, because "walk 400m" is information and not an invitation.
 *
 * The animation is here and not on the marker because animating a custom
 * marker's children flickers in react-native-maps.
 */

import { useEffect, useRef } from 'react';
import { Animated, Easing, Pressable, StyleSheet, Text } from 'react-native';

type Props = {
  /** Null when nothing is in reach: then `meters` carries the nearest lock. */
  count: number | null;
  meters: number | null;
  onPress: () => void;
};

function label(count: number | null, meters: number | null): string {
  if (count != null) {
    return count === 1 ? '1 memory within reach' : `${count} memories within reach`;
  }
  const away = meters == null ? '' : meters < 1000 ? `${Math.round(meters)} m` : `${(meters / 1000).toFixed(1)} km`;
  return `Nearest locked memory \u00b7 ${away}`;
}

export default function ReachBanner({ count, meters, onPress }: Props) {
  const reachable = count != null;
  const breath = useRef(new Animated.Value(0)).current;

  useEffect(() => {
    if (!reachable) return;
    const loop = Animated.loop(
      Animated.sequence([
        Animated.timing(breath, {
          toValue: 1,
          duration: 1100,
          easing: Easing.inOut(Easing.quad),
          useNativeDriver: true,
        }),
        Animated.timing(breath, {
          toValue: 0,
          duration: 1100,
          easing: Easing.inOut(Easing.quad),
          useNativeDriver: true,
        }),
      ]),
    );
    loop.start();
    return () => loop.stop();
  }, [breath, reachable]);

  return (
    <Animated.View
      style={[
        styles.wrap,
        { transform: [{ scale: breath.interpolate({ inputRange: [0, 1], outputRange: [1, 1.04] }) }] },
      ]}
    >
      <Pressable
        style={[styles.pill, !reachable && styles.distant]}
        onPress={onPress}
        accessibilityRole="button"
        accessibilityLabel={
          reachable ? `${label(count, meters)}. Open to unlock.` : label(count, meters)
        }
      >
        <Text style={[styles.text, !reachable && styles.distantText]}>{label(count, meters)}</Text>
      </Pressable>
    </Animated.View>
  );
}

const styles = StyleSheet.create({
  wrap: { position: 'absolute', top: 108, alignSelf: 'center' },
  pill: {
    backgroundColor: '#f59e0b',
    paddingHorizontal: 18,
    paddingVertical: 10,
    borderRadius: 20,
    shadowColor: '#b45309',
    shadowOpacity: 0.35,
    shadowRadius: 10,
    shadowOffset: { width: 0, height: 3 },
    elevation: 4,
  },
  distant: { backgroundColor: 'rgba(255,255,255,0.94)', shadowColor: '#000', shadowOpacity: 0.12 },
  text: { color: '#fff', fontSize: 14, fontWeight: '700' },
  distantText: { color: '#71717a', fontWeight: '600' },
});
