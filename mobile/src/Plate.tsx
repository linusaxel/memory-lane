/** The Collector's framed plate: a raised card, a double gold rule and a
 *  diamond at each corner, like a portrait in an old book. The portrait on
 *  its page, the class crests and the rank-up all stand in one (UI.md, "The
 *  Collector"). Svg takes no dynamic colour, so the corners are the locket's
 *  metal, the same in both themes. */

import type { ReactNode } from 'react';
import { StyleSheet, View } from 'react-native';
import Svg, { Path } from 'react-native-svg';

import { color, metal } from './theme.ts';

type Props = {
  /** The inner square, what stands in it. */
  size: number;
  /** Chosen, or the one standing now: the rule in full gold. */
  on?: boolean;
  children: ReactNode;
};

export default function Plate({ size, on, children }: Props) {
  const pad = Math.round(size * 0.08);
  const corner = Math.max(10, Math.round(size * 0.09));
  return (
    <View style={[styles.plate, { padding: pad }, on && styles.on]}>
      <View style={[styles.inner, on && styles.innerOn, { width: size, height: size }]}>
        {children}
      </View>
      {CORNERS.map((at) => (
        <Svg
          key={at.key}
          width={corner}
          height={corner}
          viewBox="0 0 10 10"
          style={[styles.corner, at.place(corner)]}
        >
          <Path d="M5 0 L10 5 L5 10 L0 5 Z" fill={on ? metal.mid : metal.rim} />
          <Path d="M5 2.5 L7.5 5 L5 7.5 L2.5 5 Z" fill={metal.hi} />
        </Svg>
      ))}
    </View>
  );
}

const CORNERS = [
  { key: 'tl', place: (s: number) => ({ top: -s / 2, left: -s / 2 }) },
  { key: 'tr', place: (s: number) => ({ top: -s / 2, right: -s / 2 }) },
  { key: 'bl', place: (s: number) => ({ bottom: -s / 2, left: -s / 2 }) },
  { key: 'br', place: (s: number) => ({ bottom: -s / 2, right: -s / 2 }) },
];

const styles = StyleSheet.create({
  plate: {
    backgroundColor: color.paperRaised,
    borderRadius: 6,
    borderWidth: StyleSheet.hairlineWidth,
    borderColor: color.goldLine,
  },
  on: { borderWidth: 2, borderColor: color.gold },
  inner: {
    alignItems: 'center',
    justifyContent: 'center',
    borderRadius: 3,
    borderWidth: StyleSheet.hairlineWidth,
    borderColor: color.goldLine,
  },
  innerOn: { borderColor: color.gold },
  corner: { position: 'absolute' },
});
