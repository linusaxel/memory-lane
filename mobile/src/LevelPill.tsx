/** The top of the map: your level, and how far into it, from finished walks.
 *  The number rolls when it changes (docs/10, "Walks earn XP; rare memories
 *  wait for a level"). */

import { Host, Text as SwiftText } from '@expo/ui/swift-ui';
import {
  Animation,
  animation,
  contentTransition,
  font as swiftFont,
  foregroundColor,
} from '@expo/ui/swift-ui/modifiers';
import {
  Platform,
  StyleSheet,
  Text,
  View,
  useColorScheme,
  type StyleProp,
  type ViewStyle,
} from 'react-native';

import type { Profile } from './api.ts';
import { GlassButton } from './Glass.tsx';
import { color, label, pill, solid } from './theme.ts';

type Props = {
  level: number;
  /** How far from this level's start to the next, 0 to 1. */
  into: number;
  place: StyleProp<ViewStyle>;
  onPress: () => void;
};

export default function LevelPill({ level, into, place, onPress }: Props) {
  const real = solid(useColorScheme() === 'dark');
  const line = `Level ${level}`;
  return (
    <GlassButton
      place={place}
      style={styles.pill}
      accessibilityRole="button"
      accessibilityLabel={`${line}, ${Math.round(into * 100)}% to the next.`}
      accessibilityHint="Your level and every walk"
      onPress={onPress}
    >
      <View style={styles.lines}>
        {Platform.OS === 'ios' ? (
          <Host matchContents>
            <SwiftText
              modifiers={[
                swiftFont({ design: 'rounded', weight: 'semibold', size: 15 }),
                foregroundColor(real.ink),
                contentTransition('numericText'),
                animation(Animation.spring(), level),
              ]}
            >
              {line}
            </SwiftText>
          </Host>
        ) : (
          <Text style={styles.figure}>{line}</Text>
        )}
        <View style={[styles.track, { backgroundColor: real.track }]}>
          <View style={[styles.fill, { width: `${into * 100}%`, backgroundColor: real.plum }]} />
        </View>
      </View>
    </GlassButton>
  );
}

/** How far into this level the profile is, 0 to 1. */
export function levelInto({ xp, xp_level, xp_next }: Profile): number {
  return Math.min(1, (xp - xp_level) / Math.max(1, xp_next - xp_level));
}

const styles = StyleSheet.create({
  pill: { ...pill, minHeight: 48, paddingHorizontal: 20 },
  lines: { flexDirection: 'row', alignItems: 'center', gap: 10 },
  figure: { ...label, fontSize: 15, color: color.ink },
  track: { width: 48, height: 6, borderRadius: 3, overflow: 'hidden' },
  fill: { height: 6, borderRadius: 3 },
});
