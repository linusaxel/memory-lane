/** A floating pane of frosted glass.
 *
 * iOS 26's direction: chrome floats over content on glass rather than sitting
 * in solid blocks, so the content leads. Over a map that is not decoration -
 * a solid white bar hides the street you are standing on.
 *
 * Not for anything that has to be read at a glance. NN/g's complaint about
 * Liquid Glass is exactly that text over blur loses contrast, so the amber
 * reach pill and the "Near me" button stay solid. Glass is for the frame.
 *
 * And it is *frosted*, not transparent. The first attempt at 55% white over a
 * street map was unreadable on screen - the trend is "glass", the requirement
 * is still 4.5:1. 82% keeps a suggestion of the map moving underneath and
 * nothing more.
 *
 * BlurView is native on iOS and a translucent view on Android, which is the
 * right fallback: the layout is identical and only the texture is missing.
 */

import { BlurView } from 'expo-blur';
import { StyleSheet, View, type ViewStyle } from 'react-native';

type Props = {
  style?: ViewStyle | ViewStyle[];
  /** The corner radius. It has to be passed, not inferred - see below. */
  radius?: number;
  intensity?: number;
  children: React.ReactNode;
};

export default function Glass({ style, radius = 22, intensity = 30, children }: Props) {
  return (
    // The radius goes on both layers. A parent's overflow:hidden does not clip
    // the native blur on iOS, so the rounded background showed through square
    // corners of blur - visibly a rectangle with rounded paint under it.
    <View style={[styles.clip, { borderRadius: radius }, style]}>
      <BlurView intensity={intensity} tint="light" style={[styles.fill, { borderRadius: radius }]}>
        {children}
      </BlurView>
    </View>
  );
}

const styles = StyleSheet.create({
  clip: { overflow: 'hidden', backgroundColor: 'rgba(255,255,255,0.82)' },
  fill: { alignItems: 'center', justifyContent: 'center', overflow: 'hidden' },
});
