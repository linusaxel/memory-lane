/** A control or a card floating over the map: iOS 26's Liquid Glass, or
 *  raised paper with the one shadow where there is no glass (older iOS,
 *  Android).
 *
 *  Never a full sheet, and never glass on glass (docs/09-visual-design.md
 *  parts 8 and 13). `place` positions
 *  it, `style` is its shape. Untinted, with a hairline and a shadow so it
 *  holds an edge on the cream map; `prominent`, the one primary, is green
 *  enamel glass in a gold bezel (docs/10, "Jewel Box"). A press squishes it and springs it back with
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

import { color, floating, glassEdge, glassLift, lift, radius, solid } from './theme';

const GLASS = isLiquidGlassAvailable();

type Props = Omit<PressableProps, 'style' | 'children'> & {
  place?: StyleProp<ViewStyle>;
  style?: StyleProp<ViewStyle>;
  /** The one primary action over the map: green glass, its label in onGo. */
  prominent?: boolean;
  children: ReactNode;
};

export function GlassButton({
  place,
  style,
  prominent,
  children,
  onPressIn,
  onPressOut,
  ...press
}: Props) {
  const go = solid(useColorScheme() === 'dark').goGlass;
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
      <Animated.View style={[glassLift, { transform: [{ scale }] }]}>
        {GLASS ? (
          <GlassView
            style={[style, glassEdge]}
            glassEffectStyle="regular"
            tintColor={prominent ? go : undefined}
            isInteractive
          >
            {children}
            {prominent && <View style={bezel} />}
          </GlassView>
        ) : (
          <View
            style={[
              style,
              glassEdge,
              lift,
              { backgroundColor: prominent ? color.goBg : color.paperRaised },
            ]}
          >
            {children}
            {prominent && <View style={bezel} />}
          </View>
        )}
      </Animated.View>
    </Pressable>
  );
}

// The prominent one's gold bezel, 4pt in, as Button's go.
const bezel = {
  position: 'absolute' as const,
  top: 4,
  left: 4,
  right: 4,
  bottom: 4,
  borderRadius: radius.pill,
  borderWidth: 1,
  borderColor: color.goRim,
};

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
