/** The one way a layer closes: an × in a quiet circle, top trailing
 *  (UI.md, rule 12). 30pt drawn, 44pt to the finger. */

import { Pressable, StyleSheet, type StyleProp, type ViewStyle } from 'react-native';
import Glyph from './Glyph.tsx';
import { color, dim } from './theme.ts';

type Props = {
  onPress: () => void;
  /** What VoiceOver says, and what the e2e flows tap. */
  label?: string;
  disabled?: boolean;
  place?: StyleProp<ViewStyle>;
};

export default function CloseButton({ onPress, label = 'Close', disabled, place }: Props) {
  return (
    <Pressable
      style={dim([styles.circle, place])}
      onPress={onPress}
      disabled={disabled}
      hitSlop={7}
      accessibilityRole="button"
      accessibilityLabel={label}
    >
      <Glyph name="xmark" size={13} weight="semibold" color={color.inkSoft} />
    </Pressable>
  );
}

const styles = StyleSheet.create({
  circle: {
    width: 30,
    height: 30,
    borderRadius: 15,
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: color.rule,
  },
});
