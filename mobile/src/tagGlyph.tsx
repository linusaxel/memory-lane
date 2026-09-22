/** One small mark per tag, for the corner of a pin that has nothing else in
 *  it. Monochrome, drawn only in palette colours - a tag glyph is texture, not
 *  a second accent, so it never reaches for `seal`.
 *
 *  ponytail: only the tags the dev seed actually has get real art. Everything
 *  else falls back to a plain dot. Add a case here as a tag needs one - there
 *  is no reason to hand-draw all eighteen before a single one has shipped.
 */

import { Circle, Line, Path, Svg } from 'react-native-svg';
import type { ColorValue } from 'react-native';

type Props = { tag: string; size: number; color: ColorValue };

export default function TagGlyph({ tag, size, color }: Props) {
  const stroke = { stroke: color, strokeWidth: 1.6, strokeLinecap: 'round' as const };
  const inner = size * 0.62;
  const box = { width: size, height: size, viewBox: `0 0 ${inner} ${inner}` };

  switch (tag) {
    case 'food':
      // A fork: three tines and a handle.
      return (
        <Svg {...box}>
          <Line x1={inner * 0.3} y1={0} x2={inner * 0.3} y2={inner * 0.45} {...stroke} />
          <Line x1={inner * 0.5} y1={0} x2={inner * 0.5} y2={inner * 0.45} {...stroke} />
          <Line x1={inner * 0.7} y1={0} x2={inner * 0.7} y2={inner * 0.45} {...stroke} />
          <Line x1={inner * 0.5} y1={inner * 0.45} x2={inner * 0.5} y2={inner} {...stroke} />
        </Svg>
      );
    case 'drink':
      // A glass: a trapezoid with a stem.
      return (
        <Svg {...box}>
          <Path
            d={`M${inner * 0.2},0 L${inner * 0.8},0 L${inner * 0.55},${inner * 0.5} L${inner * 0.55},${inner} M${inner * 0.45},${inner * 0.5} L${inner * 0.45},${inner}`}
            fill="none"
            {...stroke}
          />
        </Svg>
      );
    case 'nightlife':
      // A crescent moon.
      return (
        <Svg {...box}>
          <Path
            d={`M${inner * 0.65},${inner * 0.1} A${inner * 0.42},${inner * 0.42} 0 1 0 ${inner * 0.65},${inner * 0.9} A${inner * 0.32},${inner * 0.32} 0 1 1 ${inner * 0.65},${inner * 0.1} Z`}
            fill={color}
          />
        </Svg>
      );
    case 'music':
      // A single note.
      return (
        <Svg {...box}>
          <Circle cx={inner * 0.3} cy={inner * 0.8} r={inner * 0.18} fill={color} />
          <Line x1={inner * 0.46} y1={inner * 0.8} x2={inner * 0.46} y2={0} {...stroke} />
          <Line x1={inner * 0.46} y1={0} x2={inner * 0.8} y2={inner * 0.16} {...stroke} />
        </Svg>
      );
    case 'nature':
      // A leaf: two arcs meeting at the tip, with a spine.
      return (
        <Svg {...box}>
          <Path
            d={`M${inner * 0.5},0 C${inner},0 ${inner},${inner} ${inner * 0.5},${inner} C0,${inner} 0,0 ${inner * 0.5},0 Z`}
            fill="none"
            {...stroke}
          />
          <Line x1={inner * 0.5} y1={inner * 0.1} x2={inner * 0.5} y2={inner * 0.9} {...stroke} />
        </Svg>
      );
    case 'family':
      // Two overlapping figures.
      return (
        <Svg {...box}>
          <Circle cx={inner * 0.35} cy={inner * 0.25} r={inner * 0.16} fill={color} />
          <Path d={`M${inner * 0.1},${inner} C${inner * 0.1},${inner * 0.55} ${inner * 0.6},${inner * 0.55} ${inner * 0.6},${inner}`} fill="none" {...stroke} />
          <Circle cx={inner * 0.72} cy={inner * 0.35} r={inner * 0.13} fill={color} />
        </Svg>
      );
    case 'history':
      // A clock face.
      return (
        <Svg {...box}>
          <Circle cx={inner / 2} cy={inner / 2} r={inner * 0.46} fill="none" {...stroke} />
          <Line x1={inner / 2} y1={inner / 2} x2={inner / 2} y2={inner * 0.2} {...stroke} />
          <Line x1={inner / 2} y1={inner / 2} x2={inner * 0.7} y2={inner / 2} {...stroke} />
        </Svg>
      );
    case 'personal':
      // A single figure.
      return (
        <Svg {...box}>
          <Circle cx={inner / 2} cy={inner * 0.22} r={inner * 0.2} fill={color} />
          <Path
            d={`M${inner * 0.15},${inner} C${inner * 0.15},${inner * 0.5} ${inner * 0.85},${inner * 0.5} ${inner * 0.85},${inner}`}
            fill="none"
            {...stroke}
          />
        </Svg>
      );
    default:
      return null;
  }
}
