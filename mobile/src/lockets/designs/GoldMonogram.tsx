import React from 'react';
import { useAnimatedProps } from 'react-native-reanimated';
import { Ellipse, G, Path, Rect, Text as SvgText } from 'react-native-svg';
import { eio, eob, mScale, roundRectPath, seg } from '../math.ts';
import { AG, APath, Chain, Clasp, Glow, Hinges, PlaceText, matrixProps } from '../parts.tsx';
import { font, metal } from '../../theme.ts';
import type { DesignProps, LocketDesign } from '../types.ts';

// Gold V · Monogram cushion — rounded-rectangle case with rope border and corner fleurons.
// Hold: an engraver's hand cuts the two flourishes, then the place's initial is struck into the
// cartouche — a tiny press-down of the whole locket on the strike.

function Back({ d, place }: DesignProps) {
  return (
    <>
      <Chain top={-12} count={5} ringY={52} ringR={8} />
      <Rect x={82} y={64} width={136} height={192} rx={30} fill="url(#gBack)" />
      <Rect
        x={91}
        y={73}
        width={118}
        height={174}
        rx={22}
        fill={metal.glow}
        stroke={metal.deep}
        strokeWidth={1.5}
      />
      <Rect
        x={99}
        y={81}
        width={102}
        height={158}
        rx={16}
        fill="none"
        stroke={metal.inner}
        strokeWidth={1}
      />
      <Glow cx={150} cy={160} rx={60} ry={80} op={d.glowOp} />
      <PlaceText place={place} y={154} gap={26} rule="M124 164 H176" />
    </>
  );
}

const FLEURONS = [
  'M108 92 C116 92 120 96 120 104 M108 92 C108 100 112 104 120 104 M110 94 L116 100',
  'M192 92 C184 92 180 96 180 104 M192 92 C192 100 188 104 180 104 M190 94 L184 100',
  'M108 228 C116 228 120 224 120 216 M108 228 C108 220 112 216 120 216 M110 226 L116 220',
  'M192 228 C184 228 180 224 180 216 M192 228 C192 220 188 216 180 216 M190 226 L184 220',
];

function Front({ d, place }: DesignProps) {
  const flA = useAnimatedProps(() => ({
    strokeDashoffset: 80 * (1 - eio(seg(d.pp.value, 0, 0.4))),
  }));
  const flB = useAnimatedProps(() => ({
    strokeDashoffset: 76 * (1 - eio(seg(d.pp.value, 0.2, 0.6))),
  }));
  const mono = useAnimatedProps(() => {
    const strike = seg(d.pp.value, 0.55, 0.75);
    const s = 1.25 - 0.25 * eob(strike, 2);
    return { ...matrixProps(mScale(s, s, 150, 160)), opacity: Math.min(1, strike * 4) };
  });
  const initial = (place.name.trim()[0] ?? 'K').toUpperCase();
  return (
    <>
      <Rect
        x={82}
        y={64}
        width={136}
        height={192}
        rx={30}
        fill="url(#gLid)"
        stroke={metal.deep}
        strokeWidth={1.5}
      />
      <Rect
        x={89}
        y={71}
        width={122}
        height={178}
        rx={24}
        fill="none"
        stroke={metal.deep}
        strokeWidth={6}
      />
      <Rect
        x={89}
        y={71}
        width={122}
        height={178}
        rx={24}
        fill="none"
        stroke={metal.hi}
        strokeWidth={2.5}
        strokeDasharray="5 4"
      />
      <Rect
        x={98}
        y={80}
        width={104}
        height={160}
        rx={17}
        fill="none"
        stroke={metal.deep}
        strokeWidth={2.4}
        strokeDasharray="0.1 5"
        strokeLinecap="round"
      />
      <G fill="none" stroke={metal.deep} strokeWidth={1.2} strokeLinecap="round">
        {FLEURONS.map((p, i) => (
          <Path key={i} d={p} />
        ))}
      </G>
      <Ellipse
        cx={150}
        cy={160}
        rx={34}
        ry={44}
        fill="url(#gLid)"
        stroke={metal.deep}
        strokeWidth={1.2}
      />
      <Ellipse cx={150} cy={160} rx={29} ry={39} fill="none" stroke={metal.hi} strokeWidth={1} />
      <AG animatedProps={mono}>
        <SvgText
          x={150}
          y={172}
          textAnchor="middle"
          fontFamily={font.title.fontFamily}
          fontSize={38}
          fill={metal.engrave}
        >
          {initial}
        </SvgText>
      </AG>
      <G fill="none" stroke={metal.engrave} strokeWidth={1.3} strokeLinecap="round">
        <APath
          animatedProps={flA}
          d="M120 214 C130 224 142 220 150 210 C158 220 170 224 180 214"
          strokeDasharray="80 80"
        />
        <APath
          animatedProps={flB}
          d="M124 106 C134 98 144 102 150 110 C156 102 166 98 176 106"
          strokeDasharray="76 76"
        />
      </G>
      <Hinges x={78} y1={128} y2={180} />
      <Clasp clasp={d.clasp}>
        <Rect
          x={214}
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
      <Rect
        x={82}
        y={64}
        width={136}
        height={192}
        rx={30}
        fill="url(#gInner)"
        stroke={metal.deep}
        strokeWidth={1.5}
      />
      <Rect
        x={92}
        y={74}
        width={116}
        height={172}
        rx={22}
        fill="none"
        stroke={metal.hi}
        strokeWidth={1}
      />
    </>
  );
}

export const GoldMonogram: LocketDesign = {
  id: 'monogram',
  title: 'Gold V · Monogram cushion',
  period: 'Late Victorian cushion locket with cartouche, c. 1880–1900',
  cx: 150,
  cy: 160,
  hingeX: 82,
  outline: roundRectPath(82, 64, 136, 192, 30),
  sparkles: [
    [232, 92],
    [236, 214],
    [190, 274],
    [74, 70],
    [206, 48],
  ],
  holdHaptics: [
    { at: 0.12, kind: 'selection' },
    { at: 0.28, kind: 'selection' },
    { at: 0.45, kind: 'selection' },
    { at: 0.62, kind: 'rigid' }, // the initial is struck
    { at: 0.86, kind: 'soft' },
  ],
  tune: {
    scaleFn: (_p, pp) => {
      'worklet';
      return 1 - 0.02 * Math.sin(Math.PI * seg(pp, 0.55, 0.75));
    },
  },
  Back,
  Front,
  Inner,
};
