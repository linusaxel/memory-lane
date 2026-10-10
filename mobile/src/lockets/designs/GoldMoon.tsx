import React from 'react';
import { useAnimatedProps } from 'react-native-reanimated';
import { Circle, ClipPath, G, Path, RadialGradient, Rect, Stop } from 'react-native-svg';
import { circlePath, eob, mMul, mRotate, mScale, mTranslate, seg } from '../math.ts';
import { AG, Chain, Clasp, Glow, Hinges, PlaceText, matrixProps } from '../parts.tsx';
import { font, metal } from '../../theme.ts';
import { PHASE, type DesignProps, type LocketDesign } from '../types.ts';

// Gold VIII · Moon phase — Victorian celestial locket with a watchmaker's moon-phase disc.
// Round case, seed-pearl border, purple-enamel night sky, mother-of-pearl moons.
// Hold: the disc turns — the new moon rises from behind the left hump, waxes across the window and
// settles full between the humps (slight overshoot); stars twinkle as they pass.

const SKY = '#2e2152';
const STAR = 'M0 -5 L1.2 -1.2 L5 0 L1.2 1.2 L0 5 L-1.2 1.2 L-5 0 L-1.2 -1.2 Z';
const STARS: Array<[number, number]> = [
  [118, 168],
  [182, 160],
  [104, 196],
  [196, 194],
  [150, 140],
  [150, 214],
];

function Defs() {
  return (
    <>
      <RadialGradient id="moonSky" cx="50%" cy="30%" r="75%">
        <Stop offset="0" stopColor="#4a3678" />
        <Stop offset="0.6" stopColor={SKY} />
        <Stop offset="1" stopColor="#1a1233" />
      </RadialGradient>
      <RadialGradient id="moonPearl" cx="36%" cy="32%" r="80%">
        <Stop offset="0" stopColor={metal.glow} />
        <Stop offset="0.55" stopColor="#efe9df" />
        <Stop offset="0.85" stopColor="#d9d3e6" />
        <Stop offset="1" stopColor="#c3b9cf" />
      </RadialGradient>
      <ClipPath id="moonAperture">
        <Path d="M96 202 A54 54 0 0 1 204 202 Z" />
      </ClipPath>
    </>
  );
}

function Back({ d, place }: DesignProps) {
  return (
    <>
      <Chain top={-24} count={5} ringY={40} />
      <Rect x={146} y={58} width={8} height={14} fill="url(#gBack)" />
      <Circle cx={150} cy={56} r={6} fill="url(#gLid)" stroke={metal.deep} strokeWidth={1} />
      <Circle cx={150} cy={170} r={100} fill="url(#gBack)" />
      <Circle cx={150} cy={170} r={90} fill={metal.glow} stroke={metal.deep} strokeWidth={1.5} />
      <Circle
        cx={150}
        cy={170}
        r={82}
        fill="none"
        stroke={metal.deep}
        strokeWidth={2.4}
        strokeDasharray="0.1 5"
        strokeLinecap="round"
      />
      <Glow cx={150} cy={170} rx={80} ry={80} op={d.glowOp} />
      <Path d="M150 118 A14 14 0 1 0 160 142 A11 11 0 1 1 150 118 Z" fill={metal.rim} />
      <PlaceText place={place} y={172} gap={20} />
    </>
  );
}

function Star({ i, m }: { i: number } & Pick<DesignProps, 'm'>) {
  const [x, y] = STARS[i];
  const props = useAnimatedProps(() => {
    const k =
      0.8 + 0.35 * Math.sin(m.t.value * 7 + i * 1.9) * (m.phase.value === PHASE.idle ? 0.3 : 1);
    return matrixProps(mMul(mMul(mTranslate(x, y), mRotate(i * 15)), mScale(k, k)));
  });
  return (
    <AG animatedProps={props}>
      <Path d={STAR} fill={metal.light} />
    </AG>
  );
}

function Moon({ cy, flip }: { cy: number; flip?: boolean }) {
  const s = flip ? -1 : 1;
  return (
    <>
      <Circle
        cx={150}
        cy={cy}
        r={18}
        fill="url(#moonPearl)"
        stroke={metal.deep}
        strokeWidth={0.8}
      />
      <G fill="#c3b9cf" opacity={0.55}>
        <Circle cx={150 - 6 * s} cy={cy - 4 * s} r={3} />
        <Circle cx={150 + 6 * s} cy={cy + 5 * s} r={2.2} />
        <Circle cx={150 + 3 * s} cy={cy - 9 * s} r={1.4} />
      </G>
    </>
  );
}

function Front({ m, d }: DesignProps) {
  const disc = useAnimatedProps(() => {
    const alpha = -95 + 95 * eob(seg(d.pp.value, 0.05, 0.85), 1.25);
    return matrixProps(mRotate(alpha, 150, 224));
  });
  return (
    <>
      <Circle cx={150} cy={170} r={100} fill="url(#gLid)" stroke={metal.deep} strokeWidth={1.5} />
      {/* seed pearls: 36 round dashes around r = 91 */}
      <Circle
        cx={150}
        cy={170}
        r={91}
        fill="none"
        stroke="#c9bfae"
        strokeWidth={7}
        strokeLinecap="round"
        strokeDasharray="0.01 15.87"
      />
      <Circle
        cx={150}
        cy={170}
        r={91}
        fill="none"
        stroke="#fbf8f1"
        strokeWidth={5.4}
        strokeLinecap="round"
        strokeDasharray="0.01 15.87"
      />
      <Circle cx={150} cy={170} r={84} fill="none" stroke={metal.deep} strokeWidth={0.8} />
      <Path d="M90 202 A60 60 0 0 1 210 202" fill="none" stroke={metal.deep} strokeWidth={5} />
      <Path
        d="M90 202 A60 60 0 0 1 210 202"
        fill="none"
        stroke={metal.hi}
        strokeWidth={1.6}
        strokeDasharray="4 3"
      />
      <G clipPath="url(#moonAperture)">
        <AG animatedProps={disc}>
          <Circle cx={150} cy={224} r={80} fill="url(#moonSky)" />
          {STARS.map((_, i) => (
            <Star key={i} i={i} m={m} />
          ))}
          <G fill={metal.light}>
            <Circle cx={132} cy={184} r={1} />
            <Circle cx={170} cy={186} r={1} />
            <Circle cx={96} cy={250} r={1} />
            <Circle cx={204} cy={254} r={1} />
            <Circle cx={150} cy={300} r={1} />
          </G>
          <Moon cy={172} />
          <Moon cy={276} flip />
        </AG>
      </G>
      <Circle cx={122} cy={202} r={22} fill="url(#gLid)" />
      <Circle cx={178} cy={202} r={22} fill="url(#gLid)" />
      <Path
        d="M100 202 A22 22 0 0 1 144 202 M156 202 A22 22 0 0 1 200 202"
        fill="none"
        stroke={metal.deep}
        strokeWidth={1.2}
      />
      <Path
        d="M106 196 A16 16 0 0 1 120 184 M162 196 A16 16 0 0 1 176 184"
        fill="none"
        stroke={metal.hi}
        strokeWidth={1}
        strokeLinecap="round"
        opacity={0.8}
      />
      <Path d="M96 202 A54 54 0 0 1 204 202" fill="none" stroke={metal.deep} strokeWidth={1.5} />
      <Path d="M90 202 H210" stroke={metal.deep} strokeWidth={1.2} />
      <Path d="M92 205 H208" stroke={metal.hi} strokeWidth={0.8} />
      <Path d="M80 212 Q150 296 220 212" fill="none" stroke={metal.deep} strokeWidth={0.8} />
      <Path
        d="M88 210 Q150 282 212 210"
        fill="none"
        stroke={metal.deep}
        strokeWidth={0.8}
        strokeDasharray="2 3"
      />
      <G fill="none" stroke={metal.deep} strokeWidth={1} strokeLinecap="round">
        <Path d="M110 222 V234 M104 225 L116 231 M104 231 L116 225" />
        <Path d="M190 222 V234 M184 225 L196 231 M184 231 L196 225" />
      </G>
      <Path d="M150 252 A7 7 0 1 0 155 264 A5.5 5.5 0 1 1 150 252 Z" fill={metal.deep} />
      <Hinges x={46} y1={150} y2={178} />
      <Clasp clasp={d.clasp}>
        <Rect
          x={245}
          y={162}
          width={10}
          height={16}
          rx={3}
          fill="url(#gLid)"
          stroke={metal.deep}
          strokeWidth={1}
        />
        <Circle cx={250} cy={170} r={2} fill={SKY} />
      </Clasp>
    </>
  );
}

function Inner(_: DesignProps) {
  return (
    <>
      <Circle cx={150} cy={170} r={100} fill="url(#gInner)" stroke={metal.deep} strokeWidth={1.5} />
      <Circle cx={150} cy={170} r={90} fill="none" stroke={metal.hi} strokeWidth={1} />
      <Circle
        cx={150}
        cy={170}
        r={82}
        fill="none"
        stroke={metal.deep}
        strokeWidth={2.2}
        strokeDasharray="0.1 5"
        strokeLinecap="round"
      />
    </>
  );
}

export const GoldMoon: LocketDesign = {
  id: 'moon',
  title: 'Gold VIII · Moon phase',
  period: "Victorian celestial, c. 1870–90, with a watchmaker's moon-phase disc",
  cx: 150,
  cy: 170,
  hingeX: 50,
  outline: circlePath(150, 170, 100),
  sparkles: [
    [256, 120],
    [258, 220],
    [204, 290],
    [62, 92],
    [226, 64],
  ],
  holdHaptics: [
    { at: 0.3, kind: 'soft' }, // first quarter
    { at: 0.45, kind: 'soft' }, // half
    { at: 0.6, kind: 'soft' }, // gibbous
    { at: 0.8, kind: 'rigid' }, // full
  ],
  tune: { clasp: [0.78, 0.95], crack: [0.85, 8] },
  Defs,
  Back,
  Front,
  Inner,
};
