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

import Glass from './Glass.tsx';

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
      {/* Amber stays solid: it is the one thing in the app you are meant to
          act on, and text on glass loses the contrast to say so. The muted
          version is chrome, so it gets the glass. */}
      <Pressable
        onPress={onPress}
        accessibilityRole="button"
        accessibilityLabel={
          reachable ? `${label(count, meters)}. Open to unlock.` : label(count, meters)
        }
      >
        {reachable ? (
          <Text style={[styles.pill, styles.text]}>{label(count, meters)}</Text>
        ) : (
          <Glass style={styles.distant} radius={20}>
            <Text style={styles.distantText}>{label(count, meters)}</Text>
          </Glass>
        )}
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
    shadowOpacity: 0.4,
    shadowRadius: 16,
    shadowOffset: { width: 0, height: 6 },
    elevation: 5,
  },
  distant: {
    shadowColor: '#000',
    shadowOpacity: 0.1,
    shadowRadius: 12,
    shadowOffset: { width: 0, height: 4 },
    elevation: 3,
  },
  text: { color: '#fff', fontSize: 14, fontWeight: '700', overflow: 'hidden' },
  distantText: {
    color: '#52525b',
    fontSize: 14,
    fontWeight: '600',
    paddingHorizontal: 18,
    paddingVertical: 10,
  },
});
