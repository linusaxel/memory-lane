import { useEffect, useRef } from 'react';
import { AccessibilityInfo, Animated, Easing, StyleSheet, View, useColorScheme } from 'react-native';
import * as SplashScreen from 'expo-splash-screen';
import Svg, { Circle, Path, Rect } from 'react-native-svg';

import { solid } from './theme.ts';

const AnimatedRect = Animated.createAnimatedComponent(Rect);
const AnimatedCircle = Animated.createAnimatedComponent(Circle);

/** mobile/assets/icon.svg inlined - there is no SVG-import tooling in this
 *  project (no metro transformer). TILE_RX is
 *  mobile/scripts/generate-app-icons.mjs's, so the first frame here is the
 *  native splash-icon.png (the bare tile) exactly. */
const ROAD =
  'M180 1024 C220 740 760 780 640 540 C580 430 440 430 490 350 L530 350 C500 420 660 440 710 540 C820 760 520 860 820 1024Z';
const ROAD_TOP = 330;
const ROAD_SPAN = 1024 - ROAD_TOP;
const SUN_R = 66;
const TILE_RX = 229;
const SIZE = 200;

/** "The lane draws in": the road grows up from the bottom edge, then the sun
 *  lands, then onDone. Timings are lane-draws-in/README.md's, minus the
 *  breath - the app is ready by then. theme.ts `solid`, not DynamicColorIOS:
 *  react-native-svg's fills/View `backgroundColor` here sit on the same "real
 *  colour, not a platform-resolved one" exception as the map's
 *  Circle/Polyline - see mobile/UI.md. */
export default function StartupLogo({ onDone }: { onDone: () => void }) {
  const { paper, tile, road, sun: sunColor } = solid(useColorScheme() === 'dark');
  const reveal = useRef(new Animated.Value(0)).current;
  const sun = useRef(new Animated.Value(0)).current;

  useEffect(() => {
    SplashScreen.hideAsync();
    // react-native-svg props are not native-driver props
    const animation = Animated.parallel([
      Animated.timing(reveal, {
        toValue: 1,
        delay: 150,
        duration: 650,
        easing: Easing.bezier(0.3, 0.7, 0.2, 1),
        useNativeDriver: false,
      }),
      Animated.timing(sun, {
        toValue: 1,
        delay: 760,
        duration: 260,
        easing: Easing.bezier(0, 0, 0.58, 1),
        useNativeDriver: false,
      }),
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
    <View style={[styles.container, { backgroundColor: paper }]}>
      <View style={[styles.tile, { backgroundColor: tile }]}>
        <Svg width={SIZE} height={SIZE} viewBox="0 0 1024 1024">
          <Path d={ROAD} fill={road} />
          {/* A tile-coloured cover shrinking from the top down, so the road
              seems to grow upward. Animating a ClipPath re-renders unreliably. */}
          <AnimatedRect
            y={ROAD_TOP}
            width={1024}
            height={reveal.interpolate({ inputRange: [0, 1], outputRange: [ROAD_SPAN, 0] })}
            fill={tile}
          />
          <AnimatedCircle
            cx={510}
            cy={280}
            r={sun.interpolate({ inputRange: [0, 1], outputRange: [SUN_R * 0.6, SUN_R] })}
            opacity={sun}
            fill={sunColor}
          />
        </Svg>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
  },
  tile: {
    width: SIZE,
    height: SIZE,
    borderRadius: (SIZE * TILE_RX) / 1024,
    overflow: 'hidden',
  },
});

/** The same tile at rest: the lane drawn, the sun landed. What the sign-in
 *  screen opens on, so the logo stays put when the animation hands over. */
export function LogoTile({ size }: { size: number }) {
  const { tile, road, sun } = solid(useColorScheme() === 'dark');
  return (
    <View
      style={{
        width: size,
        height: size,
        borderRadius: (size * TILE_RX) / 1024,
        overflow: 'hidden',
        backgroundColor: tile,
      }}
    >
      <Svg width={size} height={size} viewBox="0 0 1024 1024">
        <Path d={ROAD} fill={road} />
        <Circle cx={510} cy={280} r={SUN_R} fill={sun} />
      </Svg>
    </View>
  );
}
