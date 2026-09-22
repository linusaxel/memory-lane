import { useEffect, useRef } from 'react';
import { Animated, StyleSheet, View, useColorScheme } from 'react-native';
import Svg, { Path } from 'react-native-svg';

const AnimatedPath = Animated.createAnimatedComponent(Path);

/** mobile/assets/logo-mark.svg's three paths, inlined - there is no SVG-import
 *  tooling in this project (no metro transformer), so this copies the same
 *  `d` strings mobile/scripts/generate-app-icons.mjs rasterizes. */
const STROKES = [
  { d: 'M 20 82 C 30 82 38 78 42 68 C 46 54 20 54 24 40 C 28 26 50 26 54 18', width: 7 },
  { d: 'M 58 20 C 66 14 74 12 82 14', width: 5 },
  { d: 'M 60 12 C 66 8 72 8 78 6', width: 4 },
];

// Longer than any of the three paths, so an approximate dasharray still
// clears the full stroke with room to spare - exact getTotalLength() is not
// worth the extra native round trip for a ~750ms one-shot.
const DASH_LENGTH = 220;

/** Draws the logo mark on once, then calls onDone. Splash colours, not
 *  DynamicColorIOS: react-native-svg's `stroke`/View `backgroundColor` here
 *  sit on the same "real colour, not a platform-resolved one" exception as
 *  the map's Circle/Polyline - see mobile/UI.md. */
export default function StartupLogo({ onDone }: { onDone: () => void }) {
  const scheme = useColorScheme();
  const paper = scheme === 'dark' ? '#161412' : '#F7F4EE';
  const ink = scheme === 'dark' ? '#F2EDE4' : '#1C1917';
  const progress = useRef(new Animated.Value(0)).current;

  useEffect(() => {
    const animation = Animated.timing(progress, {
      toValue: 1,
      duration: 750,
      useNativeDriver: false, // strokeDashoffset is not a native-driver prop
    });
    animation.start(({ finished }) => {
      if (finished) onDone();
    });
    return () => animation.stop();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <View style={[styles.container, { backgroundColor: paper }]}>
      <Svg width={120} height={120} viewBox="0 0 100 100">
        {STROKES.map((stroke, i) => (
          <AnimatedPath
            key={i}
            d={stroke.d}
            fill="none"
            stroke={ink}
            strokeWidth={stroke.width}
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeDasharray={DASH_LENGTH}
            strokeDashoffset={progress.interpolate({
              inputRange: [0, 1],
              outputRange: [DASH_LENGTH, 0],
            })}
          />
        ))}
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
