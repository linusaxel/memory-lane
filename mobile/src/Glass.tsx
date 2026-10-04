/** A control or a card floating over the map: iOS 26's Liquid Glass, or
 *  raised paper with the one shadow where there is no glass (older iOS,
 *  Android).
 *
 *  Never a full sheet, and never glass on glass (docs/09-visual-design.md
 *  parts 8 and 13). `place` positions
 *  it, `style` is its shape. The glass is warmed with `frost`, so it reads as
 *  paper and not as cold white. A press squishes it and springs it back with
 *  a little overshoot; it never dims: opacity on a glass view's parent stops
 *  the effect rendering.
 */

import { GlassView, isLiquidGlassAvailable } from 'expo-glass-effect';
import { useRef, type ReactNode } from 'react';
import {
  Animated,
  Pressable,
  View,
  useColorScheme,
  type PressableProps,
  type StyleProp,
  type ViewProps,
  type ViewStyle,
} from 'react-native';

import { color, floating, lift, radius, solid } from './theme';

const GLASS = isLiquidGlassAvailable();

type Props = Omit<PressableProps, 'style' | 'children'> & {
  place?: StyleProp<ViewStyle>;
  style?: StyleProp<ViewStyle>;
  children: ReactNode;
};

export function GlassButton({ place, style, children, onPressIn, onPressOut, ...press }: Props) {
  const frost = solid(useColorScheme() === 'dark').frost;
  const scale = useRef(new Animated.Value(1)).current;
  const to = (toValue: number, bounciness: number) =>
    Animated.spring(scale, { toValue, speed: 40, bounciness, useNativeDriver: true }).start();
  return (
    <Pressable
      {...press}
      style={place}
      onPressIn={(e) => {
        to(0.92, 0);
        onPressIn?.(e);
      }}
      onPressOut={(e) => {
        to(1, 14);
        onPressOut?.(e);
      }}
    >
      <Animated.View style={{ transform: [{ scale }] }}>
        {GLASS ? (
          <GlassView style={style} glassEffectStyle="regular" tintColor={frost} isInteractive>
            {children}
          </GlassView>
        ) : (
          <View style={[style, lift, { backgroundColor: color.paperRaised }]}>{children}</View>
        )}
      </Animated.View>
    </Pressable>
  );
}

/** A card over the map: the planner's, the unlock card. Its tint is thicker
 *  than a control's, since it carries prose. Never under an animated opacity:
 *  that stops the glass rendering. */
export function GlassCard({ style, ...props }: ViewProps) {
  const frost = solid(useColorScheme() === 'dark').frostCard;
  return GLASS ? (
    <GlassView
      {...props}
      style={[style, { borderRadius: radius.card }]}
      glassEffectStyle="regular"
      tintColor={frost}
    />
  ) : (
    <View {...props} style={[style, floating]} />
  );
}
