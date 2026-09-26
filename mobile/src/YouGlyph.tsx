/** You and settings: a head and shoulders, drawn like HeartGlyph. */

import { Circle, Path, Svg } from 'react-native-svg';
import type { ColorValue } from 'react-native';

type Props = { size: number; color: ColorValue };

export default function YouGlyph({ size, color }: Props) {
  return (
    <Svg width={size} height={size} viewBox="0 0 24 24">
      <Circle cx={12} cy={8} r={4} fill="none" stroke={color} strokeWidth={1.8} />
      <Path
        d="M4.5 20.5c0-4.1 3.4-6.5 7.5-6.5s7.5 2.4 7.5 6.5"
        fill="none"
        stroke={color}
        strokeWidth={1.8}
        strokeLinecap="round"
      />
    </Svg>
  );
}
