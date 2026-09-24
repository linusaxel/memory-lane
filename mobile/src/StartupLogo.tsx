import { useEffect, useRef } from 'react';
import { Animated, StyleSheet, View, useColorScheme } from 'react-native';
import Svg, { Circle, Path, Rect } from 'react-native-svg';

const AnimatedCircle = Animated.createAnimatedComponent(Circle);

/** mobile/assets/icon.svg inlined - there is no SVG-import tooling in this
 *  project (no metro transformer). ROAD and the sun are that file's; TILE_RX
 *  is mobile/scripts/generate-app-icons.mjs's, so the first frame here is the
 *  native splash-icon.png exactly. */
const ROAD =
  'M180 1024 C220 740 760 780 640 540 C580 430 440 430 490 350 L530 350 C500 420 660 440 710 540 C820 760 520 860 820 1024Z';
const TILE_RX = 229;

/** Fades the sun in over the splash's sunless tile, then calls onDone. Splash
 *  colours, not DynamicColorIOS: react-native-svg's fills/View
 *  `backgroundColor` here sit on the same "real colour, not a
 *  platform-resolved one" exception as the map's Circle/Polyline - see
 *  mobile/UI.md. */
export default function StartupLogo({ onDone }: { onDone: () => void }) {
  const dark = useColorScheme() === 'dark';
  const paper = dark ? '#161412' : '#F7F4EE';
  const tile = dark ? '#0a2b2c' : '#106a6d';
  const road = dark ? '#e9f1ee' : '#f2ede4';
  const progress = useRef(new Animated.Value(0)).current;

  useEffect(() => {
    const animation = Animated.timing(progress, {
      toValue: 1,
      duration: 750,
      useNativeDriver: false, // react-native-svg props are not native-driver props
    });
    animation.start(({ finished }) => {
      if (finished) onDone();
    });
    return () => animation.stop();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <View style={[styles.container, { backgroundColor: paper }]}>
      <Svg width={200} height={200} viewBox="0 0 1024 1024">
        <Rect width={1024} height={1024} rx={TILE_RX} fill={tile} />
        <Path d={ROAD} fill={road} />
        <AnimatedCircle cx={510} cy={280} r={66} fill="#f2a65a" opacity={progress} />
      </Svg>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
  },
});
