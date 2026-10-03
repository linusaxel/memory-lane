/** The break between a story's parts: a hairline that tapers in from both
 *  edges to two curls and a leaf, the way an old book sets a section break.
 *  It replaces a label, never adds to one (docs/10, "The open story is one
 *  voice"). Decoration, so VoiceOver skips it. */

import { StyleSheet, View } from 'react-native';
import Svg, { Path } from 'react-native-svg';

import { color } from './theme.ts';

const H = 18;

export default function Flourish() {
  const ink = color.inkFaint;
  // Only the rules stretch; the leaf keeps its shape at any width.
  const rule = (d: string) => (
    <Svg style={styles.rule} height={H} viewBox="0 0 100 14" preserveAspectRatio="none">
      <Path d={d} fill={ink} />
    </Svg>
  );
  return (
    <View style={styles.row} accessible={false} importantForAccessibility="no-hide-descendants">
      {rule('M0 7 L100 6.4 L100 7.6 Z')}
      <Svg width={72} height={H} viewBox="0 0 56 14">
        <Path
          d="M0 7 C8 7 14 3 19 5 C23 6.5 22 10 19 10 C17 10 17 8 18.5 7.5 M56 7 C48 7 42 3 37 5 C33 6.5 34 10 37 10 C39 10 39 8 37.5 7.5"
          stroke={ink}
          strokeWidth={1}
          fill="none"
        />
        <Path d="M28 1.5 C31 4 31 8.5 28 12.5 C25 8.5 25 4 28 1.5 Z" fill={ink} />
      </Svg>
      {rule('M0 6.4 L100 7 L0 7.6 Z')}
    </View>
  );
}

const styles = StyleSheet.create({
  row: { flexDirection: 'row', alignItems: 'center' },
  rule: { flex: 1 },
});
