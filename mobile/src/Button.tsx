/** The app's buttons, one meaning each (docs/10, "Jewel Box"): `go` starts or
 *  moves on, `foil` keeps something, `quiet` is the way back or aside, and
 *  `text` is a gold word. Go and foil stand on a 4pt ledge, a border and not a
 *  shadow (docs/10, "Game menus"). A press squishes it to 0.94. Where it sits (margin,
 *  flex, alignSelf) is the caller's, through `place`. */

import type { ComponentProps, ReactNode } from 'react';
import {
  ActivityIndicator,
  Pressable,
  StyleSheet,
  Text,
  View,
  type PressableProps,
  type StyleProp,
  type ViewStyle,
} from 'react-native';
import { Foil } from './Game.tsx';
import Glyph from './Glyph.tsx';
import { buttonText, color, foil, metal, radius } from './theme.ts';

type Kind = 'go' | 'foil' | 'quiet' | 'text';

type Props = Omit<PressableProps, 'style' | 'children'> & {
  kind: Kind;
  label: string;
  busy?: boolean;
  /** An SF Symbol before the label. */
  glyph?: ComponentProps<typeof Glyph>['name'];
  /** An SF Symbol after it: Next's chevron. */
  trailing?: ComponentProps<typeof Glyph>['name'];
  place?: StyleProp<ViewStyle>;
  children?: ReactNode;
};

const ink = { go: color.onGo, foil: foil.text, quiet: color.ink, text: color.gold };

export default function Button({
  kind,
  label,
  busy,
  glyph,
  trailing,
  place,
  children,
  ...press
}: Props) {
  const tint = ink[kind];
  return (
    <Pressable
      accessibilityRole="button"
      accessibilityLabel={label}
      {...press}
      style={({ pressed }) => [styles.box, styles[kind], place, pressed && styles.pressed]}
    >
      {kind === 'foil' && (
        <>
          <Foil style={StyleSheet.absoluteFill} />
          <View style={styles.highlight} />
        </>
      )}
      {(kind === 'go' || kind === 'foil') && (
        <View style={[styles.ring, kind === 'foil' && styles.foilRing]} />
      )}
      {busy ? (
        <ActivityIndicator color={tint} />
      ) : (
        <>
          {glyph && <Glyph name={glyph} size={15} weight="bold" color={tint} />}
          {label !== '' && (
            <Text style={[styles.label, { color: tint }]} numberOfLines={1}>
              {label}
            </Text>
          )}
          {children}
          {trailing && <Glyph name={trailing} size={15} weight="bold" color={tint} />}
        </>
      )}
    </Pressable>
  );
}

const styles = StyleSheet.create({
  box: {
    minHeight: 56,
    paddingHorizontal: 24,
    borderRadius: radius.pill,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 8,
    overflow: 'hidden',
  },
  go: { backgroundColor: color.goBg, borderBottomWidth: 4, borderBottomColor: color.goLedge },
  foil: { borderBottomWidth: 4, borderBottomColor: metal.dark },
  quiet: { backgroundColor: color.quiet, borderWidth: 1, borderColor: color.quietEdge },
  text: { minHeight: 44, paddingHorizontal: 8 },
  pressed: { transform: [{ scale: 0.94 }] },
  // Enamel set in a thin gold bezel, 4pt in from the edge.
  ring: {
    position: 'absolute',
    top: 4,
    left: 4,
    right: 4,
    bottom: 4,
    borderRadius: radius.pill,
    borderWidth: 1,
    borderColor: color.goRim,
  },
  foilRing: { borderColor: foil.ring },
  highlight: {
    position: 'absolute',
    top: 1,
    left: 20,
    right: 20,
    height: 1,
    backgroundColor: foil.highlight,
  },
  label: buttonText,
});
