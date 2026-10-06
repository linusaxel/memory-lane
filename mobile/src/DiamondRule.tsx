/** The one ornament (docs/10, "Jewel Box"): a gold hairline, an emerald
 *  diamond set in gold, a gold hairline. Under a story's byline, above its
 *  notes, over the place you are standing on. */

import { StyleSheet, View, type StyleProp, type ViewStyle } from 'react-native';

import { color } from './theme.ts';

export default function DiamondRule({ place }: { place?: StyleProp<ViewStyle> }) {
  return (
    <View
      style={[styles.row, place]}
      accessibilityElementsHidden
      importantForAccessibility="no-hide-descendants"
    >
      <View style={styles.line} />
      <View style={styles.diamond} />
      <View style={styles.line} />
    </View>
  );
}

const styles = StyleSheet.create({
  row: { flexDirection: 'row', alignItems: 'center', gap: 14 },
  line: { flex: 1, height: 1, backgroundColor: color.goldLine },
  diamond: {
    width: 11,
    height: 11,
    transform: [{ rotate: '45deg' }],
    backgroundColor: color.seal,
    borderWidth: 1,
    borderColor: color.goldLine,
  },
});
