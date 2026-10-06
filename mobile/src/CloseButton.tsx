/** The one way a layer closes: an × in a quiet circle, top trailing
 *  (UI.md, rule 12). 40pt drawn, 44pt to the finger. The same circle with
 *  another `icon` is a story's ⋯. */

import type { ComponentProps } from 'react';
import { Pressable, StyleSheet, type StyleProp, type ViewStyle } from 'react-native';
import Glyph from './Glyph.tsx';
import { color, dim } from './theme.ts';

type Props = {
  onPress: () => void;
  /** What VoiceOver says, and what the e2e flows tap. */
  label?: string;
  disabled?: boolean;
  place?: StyleProp<ViewStyle>;
  icon?: ComponentProps<typeof Glyph>['name'];
};

export default function CloseButton({
  onPress,
  label = 'Close',
  disabled,
  place,
  icon = 'xmark',
}: Props) {
  return (
    <Pressable
      style={dim([styles.circle, place])}
      onPress={onPress}
      disabled={disabled}
      hitSlop={2}
      accessibilityRole="button"
      accessibilityLabel={label}
    >
      <Glyph name={icon} size={15} weight="semibold" color={color.ink} />
    </Pressable>
  );
}

const styles = StyleSheet.create({
  circle: {
    width: 40,
    height: 40,
    borderRadius: 20,
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: color.quiet,
    borderWidth: 1,
    borderColor: color.quietEdge,
  },
});
