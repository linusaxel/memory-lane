import React from 'react';
import { Ellipse, G, Rect } from 'react-native-svg';
import { ellipsePath } from '../math.ts';
import { Chain, Clasp, Glow, Hinges, PlaceText } from '../parts.tsx';
import { font, metal } from '../../theme.ts';
import type { DesignProps, LocketDesign } from '../types.ts';

// Gold I · Guilloché oval — engine-turned rosette lid.
// Hold: the clasp slides early, the locket turns a little further in your hand (12°), light runs across
// the guilloché and the lid trembles against the catch for the last third.

function Back({ d, place }: DesignProps) {
  return (
    <>
      <Chain top={-24} count={6} ringY={48} ringR={8} />
      <Ellipse cx={150} cy={160} rx={82} ry={104} fill="url(#gBack)" />
      <Ellipse
        cx={150}
        cy={160}
        rx={73}
        ry={95}
        fill={metal.glow}
        stroke={metal.deep}
        strokeWidth={1.5}
      />
      <Ellipse cx={150} cy={160} rx={64} ry={85} fill="none" stroke={metal.inner} strokeWidth={1} />
      <Glow cx={150} cy={160} rx={70} ry={90} op={d.glowOp} />
      <PlaceText place={place} y={152} gap={26} rule="M126 162 H174" />
    </>
  );
}

function Front({ d }: DesignProps) {
  return (
    <>
      <Ellipse
        cx={150}
        cy={160}
        rx={82}
        ry={104}
        fill="url(#gLid)"
        stroke={metal.deep}
        strokeWidth={1.5}
      />
      <Ellipse
        cx={150}
        cy={160}
        rx={74}
        ry={96}
        fill="none"
        stroke={metal.hi}
        strokeWidth={1.5}
        opacity={0.9}
      />
      <Ellipse
        cx={150}
        cy={160}
        rx={70}
        ry={92}
        fill="none"
        stroke={metal.deep}
        strokeWidth={0.8}
      />
      <G fill="none" stroke={metal.deep} strokeWidth={0.6} opacity={0.55}>
        {Array.from({ length: 12 }, (_, i) => (
          <Ellipse
            key={i}
            cx={150}
            cy={160}
            rx={58}
            ry={20}
            transform={`rotate(${i * 15} 150 160)`}
          />
        ))}
      </G>
      <Ellipse
        cx={150}
        cy={160}
        rx={18}
        ry={22}
        fill="url(#gLid)"
        stroke={metal.deep}
        strokeWidth={1}
      />
      <Ellipse cx={150} cy={160} rx={12} ry={15} fill="none" stroke={metal.hi} strokeWidth={1} />
      <Hinges x={64} y1={132} y2={176} />
      <Clasp clasp={d.clasp}>
        <Rect
          x={228}
          y={152}
          width={10}
          height={16}
          rx={3}
          fill="url(#gLid)"
          stroke={metal.deep}
          strokeWidth={1}
        />
      </Clasp>
    </>
  );
}

function Inner(_: DesignProps) {
  return (
    <>
      <Ellipse
        cx={150}
        cy={160}
        rx={82}
        ry={104}
        fill="url(#gInner)"
        stroke={metal.deep}
        strokeWidth={1.5}
      />
      <Ellipse cx={150} cy={160} rx={72} ry={94} fill="none" stroke={metal.hi} strokeWidth={1} />
      <Ellipse cx={150} cy={160} rx={62} ry={82} fill="none" stroke={metal.rim} strokeWidth={0.8} />
    </>
  );
}

export const GoldOval: LocketDesign = {
  id: 'oval',
  title: 'Gold I · Guilloché oval',
  period: 'Edwardian engine-turned (guilloché) locket, c. 1900–1910',
  cx: 150,
  cy: 160,
  hingeX: 68,
  outline: ellipsePath(150, 160, 82, 104),
  sparkles: [
    [232, 96],
    [244, 190],
    [196, 266],
    [92, 58],
    [214, 40],
  ],
  holdHaptics: [
    { at: 0.3, kind: 'rigid' },
    { at: 0.65, kind: 'soft' },
    { at: 0.8, kind: 'soft' },
  ],
  tune: { tilt: -12, crack: [0.35, 9], clasp: [0.05, 0.3], tremble: true },
  Back,
  Front,
  Inner,
};
