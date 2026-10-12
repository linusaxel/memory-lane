/** The app's own icons, one outlined family with AddIcon and the Plan-a-walk
 *  rose: the ones the map, the dock and a memory show. Everything else is a
 *  Glyph (SF Symbol) in a palette colour (docs/10, "Dusk"). `filled` is the
 *  on state: hearted, or the map following you. `bounce` pops it each time
 *  its value changes, as Glyph's does. */

import { useEffect, useRef } from 'react';
import { Animated, type ColorValue } from 'react-native';
import Svg, { Circle, Path } from 'react-native-svg';

const PATHS = {
  journal:
    'M6 4h11a2 2 0 0 1 2 2v14H8a2 2 0 0 1-2-2V4zM6 18a2 2 0 0 1 2-2h11M12.5 7.5l2 2-2 2-2-2z',
  locate: 'M20 4L4 11l7.2 1.8L13 20z',
  heart:
    'M12 20s-7.5-4.6-7.5-10.2A4.1 4.1 0 0 1 12 7.4a4.1 4.1 0 0 1 7.5 2.4C19.5 15.4 12 20 12 20z',
  settings:
    'M19.0 10.3L21.4 10.6L21.4 13.4L19.0 13.7L18.2 15.7L19.6 17.6L17.6 19.6L15.7 18.2L13.7 19.0L13.4 21.4L10.6 21.4L10.3 19.0L8.3 18.2L6.4 19.6L4.4 17.6L5.8 15.7L5.0 13.7L2.6 13.4L2.6 10.6L5.0 10.3L5.8 8.3L4.4 6.4L6.4 4.4L8.3 5.8L10.3 5.0L10.6 2.6L13.4 2.6L13.7 5.0L15.7 5.8L17.6 4.4L19.6 6.4L18.2 8.3z',
};

type Props = {
  name: keyof typeof PATHS;
  size: number;
  color: ColorValue;
  filled?: boolean;
  bounce?: unknown;
};

export default function Icon({ name, size, color, filled, bounce }: Props) {
  const scale = useRef(new Animated.Value(1)).current;
  const first = useRef(true);
  useEffect(() => {
    if (first.current) {
      first.current = false;
      return;
    }
    scale.setValue(0.8);
    Animated.spring(scale, {
      toValue: 1,
      speed: 30,
      bounciness: 14,
      useNativeDriver: true,
    }).start();
  }, [bounce, scale]);
  return (
    <Animated.View style={{ transform: [{ scale }] }}>
      <Svg
        width={size}
        height={size}
        viewBox="0 0 24 24"
        fill={filled ? color : 'none'}
        stroke={color}
        strokeWidth={1.8}
        strokeLinecap="round"
        strokeLinejoin="round"
      >
        <Path d={PATHS[name]} />
        {name === 'settings' && <Circle cx={12} cy={12} r={3} fill="none" />}
      </Svg>
    </Animated.View>
  );
}
