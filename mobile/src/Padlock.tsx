/** The app's one symbol, drawn rather than set in an emoji font.
 *
 * It has to work at 20px on a map pin and at 48px in the middle of a sheet, and
 * it has to take the state colour - grey out of reach, amber in reach. An emoji
 * padlock does neither: it is always yellow and always its own design.
 */

import {
  Animated,
  StyleSheet,
  View,
  type ColorValue,
  type StyleProp,
  type ViewStyle,
} from 'react-native';

type Props = {
  size: number;
  /** ColorValue, not string: the palette's entries are dynamic on iOS and the
   *  platform resolves them at draw time. */
  color: ColorValue;
  /** Applied to the shackle alone, so it can be lifted and swung out of the
   *  body while the body stays put - which is the difference between a lock
   *  that opens and an icon that swaps. Only the unlock control passes this;
   *  every pin on the map leaves it undefined and gets a static symbol.
   *
   *  The pivot is set here rather than by the caller: a shackle that turns
   *  about its own centre reads as a wobble, and the leg it hinges on is a
   *  property of the drawing, not of whoever is animating it. */
  shackleStyle?: StyleProp<ViewStyle> | Animated.WithAnimatedValue<StyleProp<ViewStyle>>;
};

export default function Padlock({ size, color, shackleStyle }: Props) {
  const stroke = Math.max(2, size * 0.14);

  return (
    <View style={styles.wrap}>
      <Animated.View
        style={[
          {
            width: size * 0.62,
            height: size * 0.44,
            borderWidth: stroke,
            borderBottomWidth: 0,
            borderColor: color,
            borderTopLeftRadius: 999,
            borderTopRightRadius: 999,
            // The right leg stays in the body and everything swings off it.
            transformOrigin: 'right bottom',
          },
          shackleStyle,
        ]}
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
