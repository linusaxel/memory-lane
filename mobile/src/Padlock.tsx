/** The app's one symbol, drawn rather than set in an emoji font.
 *
 * It has to work at 20px on a map pin and at 48px in the middle of a sheet, and
 * it has to take the state colour - grey out of reach, amber in reach. An emoji
 * padlock does neither: it is always yellow and always its own design.
 */

import { StyleSheet, View } from 'react-native';

type Props = {
  size: number;
  color: string;
};

export default function Padlock({ size, color }: Props) {
  const stroke = Math.max(2, size * 0.14);

  return (
    <View style={styles.wrap}>
      <View
        style={{
          width: size * 0.62,
          height: size * 0.44,
          borderWidth: stroke,
          borderBottomWidth: 0,
          borderColor: color,
          borderTopLeftRadius: 999,
          borderTopRightRadius: 999,
        }}
      />
      <View
        style={{
          width: size,
          height: size * 0.78,
          borderRadius: size * 0.18,
          backgroundColor: color,
          marginTop: -1,
        }}
      />
    </View>
  );
}

const styles = StyleSheet.create({
  wrap: { alignItems: 'center' },
});
