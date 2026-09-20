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

import { distance } from './format.ts';
import { color, font } from './theme.ts';

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
  const away = meters == null ? '' : distance(meters);
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
      {/* Both are solid paper. Glass went in and came straight back out: it is
          on every list of tells for a generated interface, and over a street
          map it either cannot be read or is not glass. */}
      <Pressable
        onPress={onPress}
        accessibilityRole="button"
        accessibilityLabel={
          reachable ? `${label(count, meters)}. Open to unlock.` : label(count, meters)
        }
      >
        <Text style={[styles.pill, reachable ? styles.text : styles.distantText]}>
          {label(count, meters)}
        </Text>
      </Pressable>
    </Animated.View>
  );
}

const styles = StyleSheet.create({
  wrap: { position: 'absolute', top: 106, alignSelf: 'center' },
  pill: {
    paddingHorizontal: 16,
    paddingVertical: 9,
    borderRadius: 4,
    overflow: 'hidden',
    fontFamily: font.monoBold,
    fontSize: 12,
    letterSpacing: 1,
    textTransform: 'uppercase',
  },
  // Stamp ink on paper. The only thing in the app wearing this colour.
  text: { backgroundColor: color.seal, color: color.paper },
  distantText: {
    backgroundColor: color.paper,
    color: color.inkFaint,
    borderWidth: 1,
    borderColor: color.rule,
  },
});
