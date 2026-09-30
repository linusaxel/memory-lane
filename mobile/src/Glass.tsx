/** A control floating over the map: iOS 26's Liquid Glass, or raised paper
 *  with the one shadow where there is no glass (older iOS, Android).
 *
 *  Only for the navigation layer over the map - never a sheet or a card, and
 *  never glass on glass (docs/09-visual-design.md part 8). `place` positions
 *  it, `style` is its shape. It scales rather than dims when pressed: opacity
 *  on a glass view's parent stops the effect rendering.
 */

import { GlassContainer, GlassView, isLiquidGlassAvailable } from 'expo-glass-effect';
import type { ReactNode } from 'react';
import {
  Pressable,
  View,
  type ColorValue,
  type PressableProps,
  type StyleProp,
  type ViewStyle,
} from 'react-native';

import { color, lift } from './theme';

const GLASS = isLiquidGlassAvailable();

type Props = Omit<PressableProps, 'style' | 'children'> & {
  place?: StyleProp<ViewStyle>;
  style?: StyleProp<ViewStyle>;
  /** The one prominent control in view. Apple: tint only what matters. */
  tint?: ColorValue;
  children: ReactNode;
};

export function GlassButton({ place, style, tint, children, ...press }: Props) {
  return (
    <Pressable {...press} style={({ pressed }) => [place, pressed && { transform: [{ scale: 0.96 }] }]}>
      {GLASS ? (
        <GlassView style={style} glassEffectStyle="regular" tintColor={tint} isInteractive>
          {children}
        </GlassView>
      ) : (
        <View style={[style, lift, { backgroundColor: tint ?? color.paperRaised }]}>{children}</View>
      )}
    </Pressable>
  );
}

/** Glass controls that sit side by side as one group: on iOS 26 they merge
 *  like a toolbar's. Only round controls that touch - the container swallows
 *  taps in its gaps, and a gap over the map is a pin you cannot tap. */
export function GlassGroup({ style, children }: { style: StyleProp<ViewStyle>; children: ReactNode }) {
  return GLASS ? (
    <GlassContainer spacing={40} style={style}>
      {children}
    </GlassContainer>
  ) : (
    <View style={style}>{children}</View>
  );
}
