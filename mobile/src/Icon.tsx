/** The app's own icons, one family: a 2pt ink line over one flat tone, chunky,
 *  as a game's items are (docs/10, "Dusk, and the map's dock"). Every button
 *  over the map, the walk and the planner, and the close circle everywhere.
 *  A toned icon is a sticker: charcoal line, cream tone, a cream halo, the same
 *  in both themes, so it never melts into the dark (docs/10, "Sticker icons").
 *  Line-only marks (close, back) take `color`. Rare states stay a Glyph (SF
 *  Symbol) in a palette colour. `filled` is the on state, the tone in the
 *  line's colour: hearted, or the map following you. `bounce` pops it each
 *  time its value changes, as Glyph's does. */

import { useEffect, useRef } from 'react';
import { Animated, type ColorValue } from 'react-native';
import Svg, { Path } from 'react-native-svg';

import { foil } from './theme';

const dot = (x: number, y: number, r: number) =>
  `M${x - r} ${y}a${r} ${r} 0 1 0 ${2 * r} 0a${r} ${r} 0 1 0 ${-2 * r} 0z`;
const GEAR =
  'M19.0 10.3L21.4 10.6L21.4 13.4L19.0 13.7L18.2 15.7L19.6 17.6L17.6 19.6L15.7 18.2L13.7 19.0L13.4 21.4L10.6 21.4L10.3 19.0L8.3 18.2L6.4 19.6L4.4 17.6L5.8 15.7L5.0 13.7L2.6 13.4L2.6 10.6L5.0 10.3L5.8 8.3L4.4 6.4L6.4 4.4L8.3 5.8L10.3 5.0L10.6 2.6L13.4 2.6L13.7 5.0L15.7 5.8L17.6 4.4L19.6 6.4L18.2 8.3z';
const HEART =
  'M12 20s-7.5-4.6-7.5-10.2A4.1 4.1 0 0 1 12 7.4a4.1 4.1 0 0 1 7.5 2.4C19.5 15.4 12 20 12 20z';
const ARROW = 'M20 4L4 11l7.2 1.8L13 20z';
const LOCKET = 'M5 13.8a7 8.2 0 1 0 14 0a7 8.2 0 1 0 -14 0z';
const MAP = 'M3 6.5l6-2.5 6 2.5 6-2.5v13.5l-6 2.5-6-2.5-6 2.5z';

/** `tone` is filled, `line` stroked, `solid` filled in the line's colour. */
const ICONS = {
  journal: {
    tone: 'M6 4h11a2 2 0 0 1 2 2v10H8a2 2 0 0 0-2 2z',
    line: 'M6 4h11a2 2 0 0 1 2 2v14H8a2 2 0 0 1-2-2V4zM6 18a2 2 0 0 1 2-2h11M12.5 6.8l2.2 2.5-2.2 2.5-2.2-2.5z',
  },
  map: { tone: MAP, line: `${MAP}M9 4v13.5M15 6.5v13.5` },
  add: { tone: LOCKET, line: `${dot(12, 3.4, 1.7)}${LOCKET}M12 10.3v7M8.5 13.8h7` },
  locate: { tone: ARROW, line: ARROW },
  heart: { tone: HEART, line: HEART },
  settings: { tone: GEAR, line: GEAR + dot(12, 12, 3) },
  close: { line: 'M7 7l10 10M17 7L7 17' },
  more: { solid: dot(5.5, 12, 1.8) + dot(12, 12, 1.8) + dot(18.5, 12, 1.8) },
  back: { line: 'M15 5l-7 7 7 7' },
  forward: { line: 'M9 5l7 7-7 7' },
  shuffle: {
    line: 'M3.5 7h3c5.5 0 5.5 10 11 10h3M3.5 17h3c5.5 0 5.5-10 11-10h3M17.5 4l3 3-3 3M17.5 14l3 3-3 3',
  },
  slide: { line: 'M5 6l6 6-6 6M12 6l6 6-6 6' },
  customize: {
    tone: dot(9, 6.5, 2.2) + dot(15.5, 12, 2.2) + dot(7.5, 17.5, 2.2),
    line:
      'M3.5 6.5h3.3M11.2 6.5h9.3M3.5 12h9.8M17.7 12h2.8M3.5 17.5h1.8M9.7 17.5h10.8' +
      dot(9, 6.5, 2.2) +
      dot(15.5, 12, 2.2) +
      dot(7.5, 17.5, 2.2),
  },
  key: {
    tone: dot(7, 12, 4),
    line: `${dot(7, 12, 4)}M11 12h10M17.5 12v3.5M20.5 12v2.5`,
  },
} satisfies Record<string, { tone?: string; line?: string; solid?: string }>;

export type IconName = keyof typeof ICONS;

type Props = {
  name: IconName;
  size: number;
  color: ColorValue;
  /** The flat fill under the line, for an icon on a foil chip: no sticker. */
  tone?: ColorValue;
  filled?: boolean;
  bounce?: unknown;
};

export default function Icon({ name, size, color, tone, filled, bounce }: Props) {
  const scale = useRef(new Animated.Value(1)).current;
  const first = useRef(true);
  useEffect(() => {
    if (first.current) {
      first.current = false;
      return;
    }
    scale.setValue(0.8);
    Animated.spring(scale, {
      toValue: 1,
      speed: 30,
      bounciness: 14,
      useNativeDriver: true,
    }).start();
  }, [bounce, scale]);
  const icon: { tone?: string; line?: string; solid?: string } = ICONS[name];
  const sticker = !!icon.tone && !tone;
  const line = sticker ? foil.text : color;
  return (
    <Animated.View style={{ transform: [{ scale }] }}>
      <Svg width={size} height={size} viewBox="0 0 24 24">
        {sticker && (
          <>
            <Path d={icon.tone} fill={foil.colors[0]} />
            <Path
              d={icon.line}
              fill="none"
              stroke={foil.colors[0]}
              strokeWidth={4.5}
              strokeLinecap="round"
              strokeLinejoin="round"
            />
          </>
        )}
        {icon.tone && <Path d={icon.tone} fill={filled ? line : (tone ?? foil.colors[1])} />}
        {icon.line && (
          <Path
            d={icon.line}
            fill="none"
            stroke={line}
            strokeWidth={2}
            strokeLinecap="round"
            strokeLinejoin="round"
          />
        )}
        {icon.solid && <Path d={icon.solid} fill={line} />}
      </Svg>
    </Animated.View>
  );
}
