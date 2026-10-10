import React from 'react';
import { useAnimatedProps } from 'react-native-reanimated';
import { Circle, G, Path, RadialGradient, Rect, Stop } from 'react-native-svg';
import { eio, eob, inset, seg } from '../math.ts';
import { APath, Chain, Clasp, Glow, Hinges, PlaceText } from '../parts.tsx';
import { font, metal } from '../../theme.ts';
import type { DesignProps, LocketDesign } from '../types.ts';

// Gold VII · Celtic Revival knot — Liberty "Cymric", c. 1900–05 (Archibald Knox).
// Shield-drop case, green enamel boss, enamelled leaf at the tip.
// Hold: a plain gold ring splits into two strands that weave over-and-under into an endless knot,
// and the plait runs round the ring (a crossing passes 12 o'clock four times) before it locks.

const SHIELD =
  'M150 64 C220 64 250 104 250 160 C250 222 206 262 150 282 C94 262 50 222 50 160 C50 104 80 64 150 64 Z';
const ENAMEL = '#1f5a4a';
const N = 8;
const R = 66;
const CX = 150;
const CY = 162;

function Defs() {
  return (
    <RadialGradient id="celEnamel" cx="40%" cy="35%" r="70%">
      <Stop offset="0" stopColor="#3f8a72" />
      <Stop offset="0.55" stopColor={ENAMEL} />
      <Stop offset="1" stopColor="#0f3329" />
    </RadialGradient>
  );
}

function knot(pp: number) {
  'worklet';
  return { A: 9 * eob(seg(pp, 0, 0.55), 1.4), phi: 4 * Math.PI * eio(seg(pp, 0.05, 0.85)) };
}

/** whole strand: sg = +1 (strand A) or -1 (strand B) */
function strand(sg: number, A: number, phi: number) {
  'worklet';
  let d = '';
  for (let i = 0; i <= 160; i++) {
    const th = (i / 160) * Math.PI * 2;
    const r = R + sg * A * Math.sin(N * th + phi);
    d +=
      (i ? 'L' : 'M') +
      (CX + r * Math.cos(th)).toFixed(1) +
      ' ' +
      (CY + r * Math.sin(th)).toFixed(1);
  }
  return d + 'Z';
}

/** short over-patches at every other crossing, so the strands weave over and under */
function patches(sg: number, A: number, phi: number) {
  'worklet';
  let out = '';
  for (let k = 0; k < 2 * N; k++) {
    const own = k % 2 ? -1 : 1;
    if (own !== sg) continue;
    const th0 = (k * Math.PI - phi) / N;
    for (let j = -3; j <= 3; j++) {
      const th = th0 + j * 0.04;
      const r = R + sg * A * Math.sin(N * th + phi);
      out +=
        (j > -3 ? 'L' : 'M') +
        (CX + r * Math.cos(th)).toFixed(1) +
        ' ' +
        (CY + r * Math.sin(th)).toFixed(1);
    }
  }
  return out;
}

function KnotPath({
  d,
  sg,
  patch,
  stroke,
  width,
  opacity = 1,
}: {
  d: DesignProps['d'];
  sg: number;
  patch: boolean;
  stroke: string;
  width: number;
  opacity?: number;
}) {
  const props = useAnimatedProps(() => {
    const k = knot(d.pp.value);
    return { d: patch ? patches(sg, k.A, k.phi) : strand(sg, k.A, k.phi) };
  });
  return (
    <APath
      animatedProps={props}
      fill="none"
      stroke={stroke}
      strokeWidth={width}
      opacity={opacity}
      strokeLinejoin="round"
      strokeLinecap="butt"
    />
  );
}

function Back({ d, place }: DesignProps) {
  return (
    <>
      <Chain top={-24} count={5} ringY={40} />
      <Rect x={147} y={56} width={6} height={10} fill="url(#gBack)" />
      <Circle cx={150} cy={54} r={5} fill="url(#gLid)" stroke={metal.deep} strokeWidth={1} />
      <Path d={SHIELD} fill="url(#gBack)" />
      <Path
        d={SHIELD}
        fill={metal.glow}
        stroke={metal.deep}
        strokeWidth={1.6}
        transform={inset(150, 166, 0.9)}
      />
      <Path
        d={SHIELD}
        fill="none"
        stroke={metal.deep}
        strokeWidth={2.6}
        strokeDasharray="0.1 5"
        strokeLinecap="round"
        transform={inset(150, 166, 0.82)}
      />
      <Glow cx={150} cy={164} rx={78} ry={88} op={d.glowOp} />
      <PlaceText place={place} y={160} gap={28} rule="M126 170 C138 164 162 176 174 170" />
    </>
  );
}

function Front(props: DesignProps) {
  const { d } = props;
  const dark = metal.engrave;
  const core = '#ebc977';
  return (
    <>
      <Path d={SHIELD} fill="url(#gLid)" stroke={metal.deep} strokeWidth={1.5} />
      <Path
        d={SHIELD}
        fill="none"
        stroke={metal.hi}
        strokeWidth={1.5}
        transform={inset(150, 166, 0.95)}
      />
      <Path
        d={SHIELD}
        fill="none"
        stroke={metal.deep}
        strokeWidth={0.8}
        transform={inset(150, 166, 0.92)}
      />
      <KnotPath d={d} sg={-1} patch={false} stroke={dark} width={8.5} />
      <KnotPath d={d} sg={-1} patch={false} stroke={core} width={5.5} />
      <KnotPath d={d} sg={1} patch={false} stroke={dark} width={8.5} />
      <KnotPath d={d} sg={1} patch={false} stroke={core} width={5.5} />
      <KnotPath d={d} sg={1} patch={false} stroke={metal.hi} width={1.2} opacity={0.7} />
      <KnotPath d={d} sg={-1} patch stroke={dark} width={8.5} />
      <KnotPath d={d} sg={-1} patch stroke={core} width={5.5} />
      <KnotPath d={d} sg={1} patch stroke={dark} width={8.5} />
      <KnotPath d={d} sg={1} patch stroke={core} width={5.5} />
      <KnotPath d={d} sg={1} patch stroke={metal.hi} width={1.2} opacity={0.7} />
      <Circle cx={150} cy={162} r={29} fill="url(#gLid)" stroke={metal.deep} strokeWidth={1} />
      <Circle
        cx={150}
        cy={162}
        r={23}
        fill="url(#celEnamel)"
        stroke={metal.engrave}
        strokeWidth={1.2}
      />
      <Path
        d="M140 148 C146 144 154 144 160 148"
        fill="none"
        stroke="#9fd0bd"
        strokeWidth={1.2}
        strokeLinecap="round"
        opacity={0.6}
      />
      <G fill="url(#gLid)" stroke={metal.engrave} strokeWidth={0.8}>
        <Circle cx={150} cy={162} r={6} />
        <Circle cx={150} cy={148} r={2.2} />
        <Circle cx={164} cy={162} r={2.2} />
        <Circle cx={150} cy={176} r={2.2} />
        <Circle cx={136} cy={162} r={2.2} />
      </G>
      <Path
        d="M150 276 C142 266 140 256 150 248 C160 256 158 266 150 276 Z"
        fill="url(#celEnamel)"
        stroke={metal.engrave}
        strokeWidth={1}
      />
      <Path d="M150 272 V252" stroke={metal.rim} strokeWidth={0.8} />
      <Hinges x={46} y1={138} y2={172} />
      <Clasp clasp={d.clasp}>
        <Rect
          x={244}
          y={152}
          width={10}
          height={16}
          rx={3}
          fill="url(#gLid)"
          stroke={metal.deep}
          strokeWidth={1}
        />
        <Circle cx={249} cy={160} r={2} fill={ENAMEL} />
      </Clasp>
    </>
  );
}

function Inner(_: DesignProps) {
  return (
    <>
      <Path d={SHIELD} fill="url(#gInner)" stroke={metal.deep} strokeWidth={1.5} />
      <Path
        d={SHIELD}
        fill="none"
        stroke={metal.hi}
        strokeWidth={1}
        transform={inset(150, 166, 0.9)}
      />
      <Path
        d={SHIELD}
        fill="none"
        stroke={metal.deep}
        strokeWidth={2.2}
        strokeDasharray="0.1 5"
        strokeLinecap="round"
        transform={inset(150, 166, 0.82)}
      />
    </>
  );
}

export const GoldCeltic: LocketDesign = {
  id: 'celtic',
  title: 'Gold VII · Celtic Revival knot',
  period: 'Liberty "Cymric" Celtic Revival, c. 1900–05 (Archibald Knox)',
  cx: 150,
  cy: 162,
  hingeX: 50,
  hingeY: 160,
  outline: SHIELD,
  sparkles: [
    [252, 100],
    [258, 214],
    [200, 282],
    [52, 92],
    [214, 50],
  ],
  holdHaptics: [
    { at: 0.367, kind: 'soft' }, // a crossing passes 12 o'clock
    { at: 0.45, kind: 'soft' },
    { at: 0.532, kind: 'soft' },
    { at: 0.85, kind: 'rigid' }, // the weave locks
  ],
  Defs,
  Back,
  Front,
  Inner,
};
