import { useEffect, useRef } from 'react';
import { AccessibilityInfo, Animated, Image, StyleSheet, Text, View } from 'react-native';
import * as SplashScreen from 'expo-splash-screen';

import { color, screenTitle } from './theme.ts';

/** The native splash's own image (scripts/generate-app-icons.mjs), so the
 *  first frame here is the splash exactly. */
const TILE = require('../assets/splash-icon.png');
/** app.json's splash `imageWidth`. */
const SIZE = 120;

/** The splash, then the name fades in under the tile (B-01), then onDone.
 *  Reduce Motion skips the fade. */
export default function StartupLogo({ onDone }: { onDone: () => void }) {
  const name = useRef(new Animated.Value(0)).current;

  useEffect(() => {
    SplashScreen.hideAsync();
    const animation = Animated.sequence([
      Animated.timing(name, { toValue: 1, delay: 150, duration: 450, useNativeDriver: true }),
      Animated.delay(350),
    ]);
    AccessibilityInfo.isReduceMotionEnabled().then((reduce) => {
      if (reduce) return onDone();
      animation.start(({ finished }) => {
        if (finished) onDone();
      });
    });
    return () => animation.stop();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <View style={styles.container}>
      <LogoTile size={SIZE} />
      <Animated.View style={[styles.name, { opacity: name }]}>
        <Text style={screenTitle}>Memory Lane</Text>
      </Animated.View>
    </View>
  );
}

/** The tile at rest: what the sign-in screen opens on, so the logo stays put
 *  when the splash hands over. */
export function LogoTile({ size }: { size: number }) {
  return <Image source={TILE} style={{ width: size, height: size }} accessible={false} />;
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: color.paper,
  },
  // Under the tile without moving it off the splash's centre.
  name: { position: 'absolute', top: '50%', marginTop: SIZE / 2 + 28 },
});
