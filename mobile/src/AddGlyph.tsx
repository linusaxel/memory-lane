/** "Add a memory", without the words: a map pin in the pins' own `brand`,
 *  with a plus where the eye would be. The header's Add button is this and
 *  nothing else, so it carries its own VoiceOver label there. */

import { Path, Svg } from 'react-native-svg';
import type { ColorValue } from 'react-native';

type Props = { size: number; color: ColorValue; plus: ColorValue };

const PIN_PATH = 'M12 22.5s-7.5-6.4-7.5-12.6a7.5 7.5 0 0 1 15 0c0 6.2-7.5 12.6-7.5 12.6z';
const PLUS_PATH = 'M12 6.4v7M8.5 9.9h7';

export default function AddGlyph({ size, color, plus }: Props) {
  return (
    <Svg width={size} height={size} viewBox="0 0 24 24">
      <Path d={PIN_PATH} fill={color} />
      <Path d={PLUS_PATH} stroke={plus} strokeWidth={2} strokeLinecap="round" />
    </Svg>
  );
}
