/** Add a memory: a locket with a plus on its face. The founder has twelve
 *  options and has not picked one (docs/design-brief/jewel-box.md); this is
 *  v01, "original". */

import type { ColorValue } from 'react-native';
import Svg, { Circle, Ellipse, Path } from 'react-native-svg';

export default function AddIcon({ size, color }: { size: number; color: ColorValue }) {
  return (
    <Svg
      width={size}
      height={size}
      viewBox="0 0 28 28"
      fill="none"
      stroke={color}
      strokeWidth={2}
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <Circle cx={14} cy={4} r={2} />
      <Ellipse cx={14} cy={16} rx={8} ry={9.5} />
      <Path d="M14 12v8M10 16h8" />
    </Svg>
  );
}
