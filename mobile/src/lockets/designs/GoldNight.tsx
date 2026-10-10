import React from 'react';
import { useAnimatedProps } from 'react-native-reanimated';
import { Circle, Ellipse, G, Path, RadialGradient, Rect, Stop } from 'react-native-svg';
import { clamp, eio, eob, eoc, ellipsePath, mScale, seg } from '../math.ts';
import { ACircle, AEllipse, AG, Clasp, Glow, PlaceText, matrixProps } from '../parts.tsx';
import { font, metal } from '../../theme.ts';
import { PHASE, type DesignProps, type LocketDesign } from '../types.ts';

// Gold VI · Gold line, night — dark mode. The locket is drawn in a single gold line as you hold:
// outer edge one way, inner edge the other, then the lozenge springs in.
// Open: a warm gold glow and rising motes.

const CASE = '#201d19';
const SEAM = '#332e27';
const OUT_LEN = 586.4; // perimeter of the 82×104 ellipse
const IN_LEN = 523.8; // perimeter of the 72×94 ellipse

function Defs() {
  return (
    <RadialGradient id="nightGlow" cx="50%" cy="50%" r="50%">
      <Stop offset="0" stopColor={metal.light} stopOpacity={0.95} />
      <Stop offset="0.55" stopColor={metal.rim} stopOpacity={0.35} />
      <Stop offset="1" stopColor={metal.rim} stopOpacity={0} />
    </RadialGradient>
  );
}

const SEEDS: Array<[number, number, number]> = [
  [120, 200, 1.8],
  [176, 210, 1.2],
  [140, 190, 1.6],
  [168, 180, 1.1],
  [128, 176, 1.5],
  [158, 214, 1.2],
];

function Mote({ i, m }: { i: number } & Pick<DesignProps, 'm'>) {
  const [x, y, r] = SEEDS[i];
  const props = useAnimatedProps(() => {
    const k = m.phase.value === PHASE.open ? seg(m.o.value, 0.1 + i * 0.05, 0.6 + i * 0.05) : 0;
    return {
      cx: x + Math.sin(k * 6 + i) * 6,
      cy: y - 110 * eoc(k),
      opacity: k > 0 ? Math.sin(Math.PI * k) : 0,
    };
  });
  return <ACircle animatedProps={props} r={r} fill={metal.light} />;
}

function Back({ m, d, place }: DesignProps) {
  return (
    <>
      <Path d="M150 -20 V40" stroke={metal.rim} strokeWidth={1.2} strokeDasharray="5 3" />
      <Circle cx={150} cy={48} r={8} fill="none" stroke={metal.inner} strokeWidth={1.5} />
      <Ellipse
        cx={150}
        cy={160}
        rx={82}
        ry={104}
        fill={CASE}
        stroke={metal.rim}
        strokeWidth={1.5}
      />
      <Glow cx={150} cy={160} rx={110} ry={130} op={d.glowOp} fill="url(#nightGlow)" />
      <Ellipse cx={150} cy={160} rx={72} ry={94} fill="none" stroke={metal.rim} strokeWidth={1} />
      <PlaceText
        place={place}
        y={154}
        gap={26}
        color={metal.nightText}
        faded={metal.nightFaded}
        rule="M130 164 H170"
      />
      {SEEDS.map((_, i) => (
        <Mote key={i} i={i} m={m} />
      ))}
    </>
  );
}

function Front({ d }: DesignProps) {
  const outer = useAnimatedProps(() => ({
    strokeDashoffset: OUT_LEN * (1 - eio(seg(d.pp.value, 0, 0.6))),
  }));
  const inner = useAnimatedProps(() => ({
    strokeDashoffset: IN_LEN * (1 - eio(seg(d.pp.value, 0.15, 0.75))),
  }));
  const motif = useAnimatedProps(() => {
    const mo = eob(seg(d.pp.value, 0.55, 0.85), 1.6);
    const s = Math.max(0.001, mo);
    return { ...matrixProps(mScale(s, s, 150, 160)), opacity: clamp(mo, 0, 1) };
  });
  return (
    <>
      <Ellipse cx={150} cy={160} rx={82} ry={104} fill={CASE} stroke={SEAM} strokeWidth={1} />
      <G fill="none">
        {/* soft halo under the line (stands in for the canvas blur filter) */}
        <AEllipse
          animatedProps={outer}
          cx={150}
          cy={160}
          rx={82}
          ry={104}
          stroke={metal.inner}
          strokeWidth={5}
          opacity={0.18}
          strokeDasharray={`${OUT_LEN} ${OUT_LEN}`}
        />
        <AEllipse
          animatedProps={outer}
          cx={150}
          cy={160}
          rx={82}
          ry={104}
          stroke={metal.inner}
          strokeWidth={1.6}
          strokeDasharray={`${OUT_LEN} ${OUT_LEN}`}
        />
        <G transform="translate(300 0) scale(-1 1)">
          <AEllipse
            animatedProps={inner}
            cx={150}
            cy={160}
            rx={72}
            ry={94}
            stroke={metal.rim}
            strokeWidth={1}
            strokeDasharray={`${IN_LEN} ${IN_LEN}`}
          />
        </G>
      </G>
      <AG animatedProps={motif}>
        <G fill="none" stroke={metal.inner} strokeWidth={1.2}>
          <Path d="M150 112 L178 160 L150 208 L122 160 Z" />
          <Path d="M150 128 L166 160 L150 192 L134 160 Z" stroke={metal.rim} />
          <Path d="M150 96 V112 M150 208 V224 M106 160 H122 M178 160 H194" stroke={metal.rim} />
        </G>
        <Circle cx={150} cy={160} r={3} fill={metal.inner} />
      </AG>
      <Rect
        x={64}
        y={134}
        width={8}
        height={10}
        rx={2}
        fill="none"
        stroke={metal.rim}
        strokeWidth={1}
      />
      <Rect
        x={64}
        y={176}
        width={8}
        height={10}
        rx={2}
        fill="none"
        stroke={metal.rim}
        strokeWidth={1}
      />
      <Clasp clasp={d.clasp}>
        <Rect
          x={228}
          y={153}
          width={9}
          height={14}
          rx={3}
          fill={CASE}
          stroke={metal.inner}
          strokeWidth={1.2}
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
        fill={CASE}
        stroke={metal.rim}
        strokeWidth={1.5}
      />
      <Ellipse
        cx={150}
        cy={160}
        rx={66}
        ry={86}
        fill="none"
        stroke={metal.rim}
        strokeWidth={0.8}
        opacity={0.7}
      />
    </>
  );
}

export const GoldNight: LocketDesign = {
  id: 'night',
  title: 'Gold VI · Gold line, night',
  period: 'Line-drawn modern take, for dark mode',
  cx: 150,
  cy: 160,
  hingeX: 68,
  outline: ellipsePath(150, 160, 82, 104),
  sparkles: [],
  edge: [SEAM, SEAM, metal.engrave],
  holdHaptics: [
    { at: 0.3, kind: 'soft' },
    { at: 0.6, kind: 'soft' }, // outer line closes
    { at: 0.75, kind: 'rigid' }, // lozenge springs in
  ],
  tune: { noShine: true },
  Defs,
  Back,
  Front,
  Inner,
};
