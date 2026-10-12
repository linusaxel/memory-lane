/** The one way a layer closes: an × in a quiet circle, top trailing
 *  (UI.md, rule 12). 40pt drawn, 44pt to the finger. The same circle with
 *  another `icon` is a story's ⋯. */

import { Pressable, StyleSheet, type StyleProp, type ViewStyle } from 'react-native';
import Icon, { type IconName } from './Icon.tsx';
import { color, dim } from './theme.ts';

type Props = {
  onPress: () => void;
  /** What VoiceOver says, and what the e2e flows tap. */
  label?: string;
  disabled?: boolean;
  place?: StyleProp<ViewStyle>;
  icon?: IconName;
};

export default function CloseButton({
  onPress,
  label = 'Close',
  disabled,
  place,
  icon = 'close',
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
      <Icon name={icon} size={18} color={color.ink} />
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
