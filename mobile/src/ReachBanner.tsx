/** "Something here is openable." The only part of the map that pulses.
 *
 * A locked pin that happens to be within reach is the entire point of the
 * product, and it is also easy to walk straight past - it is one small shape
 * among a dozen. So the map says it in words, and the words breathe.
 *
 * The animation is here and not on the marker because animating a custom
 * marker's children flickers in react-native-maps.
 */

import { useEffect, useRef } from 'react';
import { Animated, Easing, Pressable, StyleSheet, Text } from 'react-native';

type Props = {
  count: number;
  onPress: () => void;
};

export default function ReachBanner({ count, onPress }: Props) {
  const breath = useRef(new Animated.Value(0)).current;

  useEffect(() => {
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
  }, [breath]);

  return (
    <Animated.View
      style={[
        styles.wrap,
        { transform: [{ scale: breath.interpolate({ inputRange: [0, 1], outputRange: [1, 1.04] }) }] },
      ]}
    >
      <Pressable
        style={styles.pill}
        onPress={onPress}
        accessibilityRole="button"
        accessibilityLabel={`${count} ${count === 1 ? 'memory' : 'memories'} within reach. Open to unlock.`}
      >
        <Text style={styles.text}>
          {count === 1 ? '1 memory within reach' : `${count} memories within reach`}
        </Text>
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
  text: { color: '#fff', fontSize: 14, fontWeight: '700' },
});
