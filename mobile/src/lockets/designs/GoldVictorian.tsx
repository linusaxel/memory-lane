import React from 'react';
import { useAnimatedProps } from 'react-native-reanimated';
import { Circle, Ellipse, G, Path, RadialGradient, Rect, Stop } from 'react-native-svg';
import { eio, ellipsePath, mMul, mRotate, mScale, mTranslate, seg } from '../math.ts';
import {
  AEllipse,
  AG,
  Chain,
  Clasp,
  Glow,
  Hinges,
  PlaceText,
  SPARKLE,
  matrixProps,
} from '../parts.tsx';
import { font, metal } from '../../theme.ts';
import { PHASE, type DesignProps, type LocketDesign, type Motion } from '../types.ts';

// Gold IV · Victorian garnet — rope-twist border, beaded milgrain, six-leaf rosette around a set garnet.
// Hold: the locket turns 40° over in your fingers to show its depth; the garnet catches the light at
// the turn (a glint), then it faces you again and opens.

/** 0 → 1 as the locket turns over and back during the first 75% of the hold */
function turnPhase(m: Motion): number {
  'worklet';
  const ph = m.phase.value;
  return ph === PHASE.commit || ph === PHASE.open ? 1 : eio(seg(m.p.value, 0, 0.75));
}

function Defs() {
  return (
    <RadialGradient id="vicStone" cx="38%" cy="32%" r="75%">
      <Stop offset="0" stopColor="#e2603f" />
      <Stop offset="0.45" stopColor={metal.north} />
      <Stop offset="1" stopColor="#4a1a0e" />
    </RadialGradient>
  );
}

function Back({ d, place }: DesignProps) {
  return (
    <>
      <Chain top={-24} count={5} ringY={40} knobY={54} />
      <Ellipse cx={150} cy={160} rx={80} ry={102} fill="url(#gBack)" />
      <Ellipse
        cx={150}
        cy={160}
        rx={70}
        ry={92}
        fill={metal.glow}
        stroke={metal.deep}
        strokeWidth={1.5}
      />
      <Ellipse
        cx={150}
        cy={160}
        rx={62}
        ry={83}
        fill="none"
        stroke={metal.deep}
        strokeWidth={2.4}
        strokeDasharray="0.1 5"
        strokeLinecap="round"
      />
      <Glow cx={150} cy={160} rx={66} ry={86} op={d.glowOp} />
      <PlaceText place={place} y={152} gap={28} rule="M130 162 C140 158 160 166 170 162" />
    </>
  );
}

const LEAVES = [
  'M150 82 C162 92 160 104 150 108 C140 104 138 92 150 82',
  'M150 238 C162 228 160 216 150 212 C140 216 138 228 150 238',
  'M104 112 C116 100 132 106 126 118 C120 126 110 120 116 114',
  'M196 112 C184 100 168 106 174 118 C180 126 190 120 184 114',
  'M104 208 C116 220 132 214 126 202 C120 194 110 200 116 206',
  'M196 208 C184 220 168 214 174 202 C180 194 190 200 184 206',
];
const PETAL = 'M150 146 C156 136 156 122 150 114 C144 122 144 136 150 146 Z';
const BEADS: Array<[number, number]> = [
  [150, 145],
  [163, 152.5],
  [163, 167.5],
  [150, 175],
  [137, 167.5],
  [137, 152.5],
];

function Front({ m, d }: DesignProps) {
  const highlight = useAnimatedProps(() => ({ cx: 146 + 6 * Math.sin(Math.PI * turnPhase(m)) }));
  const glint = useAnimatedProps(() => {
    const g = Math.max(0, Math.sin(Math.PI * seg(turnPhase(m), 0.35, 0.75)));
    const s = Math.max(0.0001, 1.1 * g);
    return matrixProps(mMul(mMul(mTranslate(156, 154), mRotate(60 * g)), mScale(s, s)));
  });
  return (
    <>
      <Ellipse
        cx={150}
        cy={160}
        rx={80}
        ry={102}
        fill="url(#gLid)"
        stroke={metal.deep}
        strokeWidth={1.5}
      />
      <Ellipse cx={150} cy={160} rx={74} ry={96} fill="none" stroke={metal.deep} strokeWidth={6} />
      <Ellipse
        cx={150}
        cy={160}
        rx={74}
        ry={96}
        fill="none"
        stroke={metal.hi}
        strokeWidth={2.5}
        strokeDasharray="5 4"
      />
      <Ellipse
        cx={150}
        cy={160}
        rx={66}
        ry={88}
        fill="none"
        stroke={metal.deep}
        strokeWidth={2.6}
        strokeDasharray="0.1 5"
        strokeLinecap="round"
      />
      <G fill="none" stroke={metal.deep} strokeWidth={1.2} strokeLinecap="round">
        {LEAVES.map((p, i) => (
          <Path key={i} d={p} />
        ))}
      </G>
      <G fill="url(#gLid)" stroke={metal.deep} strokeWidth={1}>
        {[0, 60, 120, 180, 240, 300].map((r) => (
          <Path key={r} d={PETAL} transform={`rotate(${r} 150 160)`} />
        ))}
      </G>
      <G stroke={metal.deep} strokeWidth={0.8}>
        {[0, 60, 120, 180, 240, 300].map((r) => (
          <Path key={r} d="M150 144 V118" transform={`rotate(${r} 150 160)`} />
        ))}
      </G>
      <Circle cx={150} cy={160} r={15} fill="url(#gLid)" stroke={metal.deep} strokeWidth={1} />
      <G fill={metal.deep}>
        {BEADS.map(([x, y], i) => (
          <Circle key={i} cx={x} cy={y} r={2.4} />
        ))}
      </G>
      <Circle cx={150} cy={160} r={11} fill="url(#vicStone)" />
      <AEllipse
        animatedProps={highlight}
        cy={155}
        rx={4}
        ry={2.4}
        fill={metal.glow}
        opacity={0.75}
      />
      <AG animatedProps={glint}>
        <Path d={SPARKLE} fill={metal.glow} />
      </AG>
      <Hinges x={66} y1={130} y2={178} />
      <Clasp clasp={d.clasp}>
        <Rect
          x={226}
          y={152}
          width={10}
          height={16}
          rx={3}
          fill="url(#gLid)"
          stroke={metal.deep}
          strokeWidth={1}
        />
        <Circle cx={231} cy={160} r={2} fill={metal.north} />
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
        rx={80}
        ry={102}
        fill="url(#gInner)"
        stroke={metal.deep}
        strokeWidth={1.5}
      />
      <Ellipse cx={150} cy={160} rx={70} ry={92} fill="none" stroke={metal.hi} strokeWidth={1} />
      <Ellipse
        cx={150}
        cy={160}
        rx={62}
        ry={83}
        fill="none"
        stroke={metal.deep}
        strokeWidth={2.2}
        strokeDasharray="0.1 5"
        strokeLinecap="round"
      />
    </>
  );
}

export const GoldVictorian: LocketDesign = {
  id: 'victorian',
  title: 'Gold IV · Victorian garnet',
  period: 'Mid-Victorian, c. 1860–1880 (rope twist, milgrain, set garnet)',
  cx: 150,
  cy: 160,
  hingeX: 70,
  outline: ellipsePath(150, 160, 80, 102),
  sparkles: [
    [244, 96],
    [250, 214],
    [198, 284],
    [70, 72],
    [212, 40],
  ],
  holdHaptics: [
    { at: 0.2, kind: 'soft' },
    { at: 0.39, kind: 'rigid' }, // the garnet glints at the turn
    { at: 0.75, kind: 'soft' }, // faces you again
    { at: 0.86, kind: 'light' }, // clasp
  ],
  tune: {
    clasp: [0.72, 0.92],
    crack: [0.8, 8],
    tiltFn: (p, _pp, done) => {
      'worklet';
      const tp = done ? 1 : eio(seg(p, 0, 0.75));
      return -40 * Math.sin(Math.PI * tp);
    },
  },
  Defs,
  Back,
  Front,
  Inner,
};
