import React from 'react';
import { useAnimatedProps, useDerivedValue, type SharedValue } from 'react-native-reanimated';
import { ClipPath, Ellipse, G, Path, Pattern, RadialGradient, Rect, Stop } from 'react-native-svg';
import { eio, eob, ellipsePath, seg } from '../math.ts';
import { ACircle, APath, Chain, Clasp, Glow, Hinges, PlaceText } from '../parts.tsx';
import { font, metal } from '../../theme.ts';
import type { DesignProps, LocketDesign } from '../types.ts';

// Gold IX · Lover's eye — Georgian, c. 1790–1820.
// Horizontal oval, painted eye miniature in a seed-pearl surround; plaited hair under glass inside the lid.
// Hold: the eye wakes — the lid lifts, it glances left, then right (saccades with a settle), finds you,
// the pupil widens, and it blinks once. The blink is the commit.

const LID_INK = '#3a2a20';

function Defs() {
  return (
    <>
      {/* userSpaceOnUse so the skin colour matches across the miniature and the eyelid covers */}
      <RadialGradient id="eyeSkin" gradientUnits="userSpaceOnUse" cx={150} cy={165} r={78}>
        <Stop offset="0" stopColor="#f8eee2" />
        <Stop offset="0.7" stopColor="#efdcc8" />
        <Stop offset="1" stopColor="#e2c9b0" />
      </RadialGradient>
      <RadialGradient id="eyeIris" cx="50%" cy="50%" r="50%">
        <Stop offset="0" stopColor="#6f9a6a" />
        <Stop offset="0.45" stopColor="#2f5d47" />
        <Stop offset="1" stopColor="#16352a" />
      </RadialGradient>
      <Pattern
        id="eyeHair"
        width={7}
        height={7}
        patternUnits="userSpaceOnUse"
        patternTransform="rotate(45)"
      >
        <Rect width={7} height={7} fill="#7a5634" />
        <Path d="M0 1.75 H3.5 M3.5 5.25 H7" stroke="#4e3420" strokeWidth={1.4} />
        <Path d="M3.5 0 V3.5 M0 3.5 V7 M7 3.5 V7" stroke="#a07a52" strokeWidth={1} />
      </Pattern>
      <ClipPath id="eyeMini">
        <Ellipse cx={150} cy={170} rx={79} ry={53} />
      </ClipPath>
    </>
  );
}

function Back({ d, place }: DesignProps) {
  return (
    <>
      <Chain top={0} count={5} ringY={64} />
      <Rect x={147} y={82} width={6} height={12} fill="url(#gBack)" />
      <Ellipse
        cx={150}
        cy={79}
        rx={5.5}
        ry={5.5}
        fill="#fbf8f1"
        stroke={metal.deep}
        strokeWidth={1.2}
      />
      <Ellipse cx={150} cy={170} rx={104} ry={78} fill="url(#gBack)" />
      <Ellipse
        cx={150}
        cy={170}
        rx={94}
        ry={68}
        fill={metal.glow}
        stroke={metal.deep}
        strokeWidth={1.5}
      />
      <Ellipse
        cx={150}
        cy={170}
        rx={86}
        ry={60}
        fill="none"
        stroke={metal.deep}
        strokeWidth={2.4}
        strokeDasharray="0.1 5"
        strokeLinecap="round"
      />
      <Glow cx={150} cy={170} rx={84} ry={58} op={d.glowOp} />
      <PlaceText place={place} y={168} gap={18} />
    </>
  );
}

type EyeState = { open: number; ix: number; iy: number; pupil: number };

function useEye(pp: SharedValue<number>) {
  return useDerivedValue<EyeState>(() => {
    const p = pp.value;
    const wake = eio(seg(p, 0.04, 0.28));
    const open = wake * (1 - Math.sin(Math.PI * seg(p, 0.86, 1)));
    const gx =
      -14 * eob(seg(p, 0.32, 0.39), 1.5) +
      28 * eob(seg(p, 0.48, 0.55), 1.5) -
      14 * eob(seg(p, 0.64, 0.71), 1.5);
    return { open, ix: 150 + gx, iy: 170 - 2 * wake, pupil: 5.5 + 2.6 * eio(seg(p, 0.7, 0.84)) };
  });
}

function Front({ d }: DesignProps) {
  const eye = useEye(d.pp);
  const U = () => {
    'worklet';
    return 196 - 70 * eye.value.open;
  };
  const iris = useAnimatedProps(() => ({ cx: eye.value.ix, cy: eye.value.iy }));
  const irisRim = useAnimatedProps(() => ({ cx: eye.value.ix, cy: eye.value.iy }));
  const pupil = useAnimatedProps(() => ({
    cx: eye.value.ix,
    cy: eye.value.iy,
    r: eye.value.pupil,
  }));
  const glint = useAnimatedProps(() => ({ cx: eye.value.ix + 5.5, cy: eye.value.iy - 5.5 }));
  const shade = useAnimatedProps(() => ({ d: `M100 174 Q150 ${(U() + 4).toFixed(2)} 200 174` }));
  const cover = useAnimatedProps(() => ({
    d: `M100 172 Q150 ${U().toFixed(2)} 200 172 L232 172 L232 110 L68 110 L68 172 Z`,
  }));
  const lid = useAnimatedProps(() => ({ d: `M100 172 Q150 ${U().toFixed(2)} 200 172` }));
  const crease = useAnimatedProps(() => ({
    d: `M104 166 Q150 ${(U() - 16).toFixed(2)} 196 166`,
    opacity: 0.8 * eye.value.open,
  }));
  const lashes = useAnimatedProps(() => ({ opacity: 1 - eye.value.open }));
  return (
    <>
      <Ellipse
        cx={150}
        cy={170}
        rx={104}
        ry={78}
        fill="url(#gLid)"
        stroke={metal.deep}
        strokeWidth={1.5}
      />
      <Ellipse
        cx={150}
        cy={170}
        rx={99}
        ry={73}
        fill="none"
        stroke={metal.deep}
        strokeWidth={0.8}
      />
      {/* 28 seed pearls (ellipse perimeter 493.5 / 28) */}
      <Ellipse
        cx={150}
        cy={170}
        rx={91}
        ry={65}
        fill="none"
        stroke="#c9bfae"
        strokeWidth={10.5}
        strokeLinecap="round"
        strokeDasharray="0.01 17.61"
      />
      <Ellipse
        cx={150}
        cy={170}
        rx={91}
        ry={65}
        fill="none"
        stroke="#fbf8f1"
        strokeWidth={8.6}
        strokeLinecap="round"
        strokeDasharray="0.01 17.61"
      />
      <Ellipse
        cx={149}
        cy={168.5}
        rx={91}
        ry={65}
        fill="none"
        stroke="#ffffff"
        strokeWidth={2.6}
        strokeLinecap="round"
        strokeDasharray="0.01 17.61"
      />
      <Ellipse cx={150} cy={170} rx={81} ry={55} fill={metal.engrave} />
      <Ellipse cx={150} cy={170} rx={79} ry={53} fill="url(#eyeSkin)" />
      <Path
        d="M94 140 Q150 110 206 136"
        fill="none"
        stroke="#7a5a3e"
        strokeWidth={3.2}
        strokeLinecap="round"
        opacity={0.55}
      />
      <Path
        d="M100 140 Q150 116 200 137"
        fill="none"
        stroke="#7a5a3e"
        strokeWidth={1}
        strokeLinecap="round"
        opacity={0.5}
      />
      <Path d="M100 172 Q150 126 200 172 Q150 196 100 172 Z" fill="#fbf8f1" />
      <ACircle animatedProps={iris} r={16} fill="url(#eyeIris)" />
      <ACircle animatedProps={irisRim} r={16} fill="none" stroke="#10261e" strokeWidth={1.2} />
      <ACircle animatedProps={pupil} fill={metal.ink} />
      <ACircle animatedProps={glint} r={2.6} fill="#ffffff" />
      <APath animatedProps={shade} fill="none" stroke="#c9b6a0" strokeWidth={5} opacity={0.45} />
      <G clipPath="url(#eyeMini)">
        <APath animatedProps={cover} fill="url(#eyeSkin)" />
        <Path
          d="M100 172 Q150 196 200 172 L232 172 L232 232 L68 232 L68 172 Z"
          fill="url(#eyeSkin)"
        />
      </G>
      <APath
        animatedProps={crease}
        fill="none"
        stroke="#b89a80"
        strokeWidth={1.1}
        strokeLinecap="round"
      />
      <APath
        animatedProps={lid}
        fill="none"
        stroke={LID_INK}
        strokeWidth={1.8}
        strokeLinecap="round"
      />
      <Path
        d="M100 172 Q150 196 200 172"
        fill="none"
        stroke="#a08470"
        strokeWidth={1}
        strokeLinecap="round"
      />
      <APath
        animatedProps={lashes}
        d="M118 181 l-3 5 M132 183.5 l-1.5 6 M150 184.5 l0 6 M168 183.5 l1.5 6 M182 181 l3 5"
        fill="none"
        stroke={LID_INK}
        strokeWidth={1.1}
        strokeLinecap="round"
      />
      <Path
        d="M92 150 Q110 124 150 118"
        fill="none"
        stroke="#ffffff"
        strokeWidth={2}
        strokeLinecap="round"
        opacity={0.35}
      />
      <Hinges x={42} y1={148} y2={180} />
      <Clasp clasp={d.clasp}>
        <Rect
          x={249}
          y={162}
          width={10}
          height={16}
          rx={3}
          fill="url(#gLid)"
          stroke={metal.deep}
          strokeWidth={1}
        />
        <Ellipse
          cx={254}
          cy={170}
          rx={2}
          ry={2}
          fill="#fbf8f1"
          stroke="#c9bfae"
          strokeWidth={0.6}
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
        cy={170}
        rx={104}
        ry={78}
        fill="url(#gInner)"
        stroke={metal.deep}
        strokeWidth={1.5}
      />
      <Ellipse cx={150} cy={170} rx={94} ry={68} fill="none" stroke={metal.hi} strokeWidth={1} />
      {/* a lock of plaited hair under glass */}
      <Ellipse
        cx={150}
        cy={170}
        rx={72}
        ry={48}
        fill="url(#eyeHair)"
        stroke={metal.deep}
        strokeWidth={2.5}
      />
      <Ellipse
        cx={150}
        cy={170}
        rx={76}
        ry={52}
        fill="none"
        stroke={metal.deep}
        strokeWidth={2.2}
        strokeDasharray="0.1 5"
        strokeLinecap="round"
      />
      <Path
        d="M98 158 Q118 132 162 128"
        fill="none"
        stroke="#ffffff"
        strokeWidth={2.4}
        strokeLinecap="round"
        opacity={0.45}
      />
    </>
  );
}

export const GoldEye: LocketDesign = {
  id: 'eye',
  title: "Gold IX · Lover's eye",
  period: "Georgian lover's eye miniature, c. 1790–1820",
  cx: 150,
  cy: 170,
  hingeX: 46,
  inside: 68,
  outline: ellipsePath(150, 170, 104, 78),
  sparkles: [
    [262, 120],
    [262, 222],
    [204, 262],
    [40, 110],
    [222, 82],
  ],
  holdHaptics: [
    { at: 0.16, kind: 'light' }, // wakes
    { at: 0.36, kind: 'light' }, // glance left
    { at: 0.52, kind: 'light' }, // glance right
    { at: 0.68, kind: 'soft' }, // finds you
    { at: 0.93, kind: 'rigid' }, // the blink
  ],
  tune: { clasp: [0.75, 0.92], crack: [0.86, 8] },
  Defs,
  Back,
  Front,
  Inner,
};
