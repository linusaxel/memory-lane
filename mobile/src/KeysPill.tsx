/** The top of the map: keys earned, one per finished walk. The count rolls
 *  when it changes (docs/10, "A walk planner, nothing else"). */

import { Host, Text as SwiftText } from '@expo/ui/swift-ui';
import { Animation, animation, contentTransition, font as swiftFont, foregroundColor } from '@expo/ui/swift-ui/modifiers';
import { Platform, StyleSheet, Text, View, useColorScheme, type StyleProp, type ViewStyle } from 'react-native';

import { GlassButton } from './Glass.tsx';
import Glyph from './Glyph.tsx';
import { color, label, pill, solid } from './theme.ts';

type Props = {
  keys: number;
  place: StyleProp<ViewStyle>;
  onPress: () => void;
};

export default function KeysPill({ keys, place, onPress }: Props) {
  const real = solid(useColorScheme() === 'dark');
  const line = `${keys} ${keys === 1 ? 'key' : 'keys'}`;
  return (
    <GlassButton
      place={place}
      style={styles.pill}
      accessibilityRole="button"
      accessibilityLabel={`${line}.`}
      accessibilityHint="How walks and keys work"
      onPress={onPress}
    >
      <Glyph name="key.fill" size={15} color={real.ember} />
      <View style={styles.lines}>
        {Platform.OS === 'ios' ? (
          <Host matchContents>
            <SwiftText
              modifiers={[
                swiftFont({ design: 'rounded', weight: 'semibold', size: 15 }),
                foregroundColor(real.ink),
                contentTransition('numericText'),
                animation(Animation.spring(), keys),
              ]}
            >
              {line}
            </SwiftText>
          </Host>
        ) : (
          <Text style={styles.figure}>{line}</Text>
        )}
      </View>
    </GlassButton>
  );
}

const styles = StyleSheet.create({
  pill,
  lines: { alignItems: 'center' },
  figure: { ...label, fontSize: 15, color: color.ink },
});
