/** The heart action's own mark: outline when this device hasn't hearted a
 *  memory, filled once it has.
 *
 *  Monochrome like every other glyph here: never `seal`, that accent is
 *  reserved for "openable now".
 */

import { Path, Svg } from 'react-native-svg';
import type { ColorValue } from 'react-native';

type Props = { size: number; color: ColorValue; filled?: boolean };

const HEART_PATH =
  'M12 21s-7.5-4.6-10.3-9.1C-0.2 8.7 1 5 4.6 4.1 7 3.5 9.4 4.7 12 7.7 ' +
  '14.6 4.7 17 3.5 19.4 4.1 23 5 24.2 8.7 22.3 11.9 19.5 16.4 12 21 12 21z';

export default function HeartGlyph({ size, color, filled }: Props) {
  return (
    <Svg width={size} height={size} viewBox="0 0 24 24">
      <Path
        d={HEART_PATH}
        fill={filled ? color : 'none'}
        stroke={color}
        strokeWidth={filled ? 0 : 1.6}
        strokeLinejoin="round"
      />
    </Svg>
  );
}
