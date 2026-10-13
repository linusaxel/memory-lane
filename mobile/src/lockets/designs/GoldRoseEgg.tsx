import React from 'react';
import {
  Circle,
  ClipPath,
  Ellipse,
  G,
  LinearGradient,
  Path,
  RadialGradient,
  Rect,
  Stop,
} from 'react-native-svg';
import { clamp, eio, eob, eoc, seg } from '../math.ts';
import { Dyn, useVals, type DynState, type Vals } from '../dyn.tsx';
import { Clasp, Glow, PlaceText } from '../parts.tsx';
import type { DesignProps, LocketDesign } from '../types.ts';

// Gold XII · Rose-gold guilloché egg — Imperial Russian enamel style, c. 1900.
// Hold: the engine-turned rings under the pink enamel flow outward, a ring of light reaches the rim, the white-gold border lights, the rosette clicks.
// Generated from the canvas board GoldRoseEgg.dc.html by convert.py; the maths in `vals` is the board's own.

const OUTLINE =
  'M150 58 C200 58 238 120 238 178 C238 236 200 272 150 272 C100 272 62 236 62 178 C62 120 100 58 150 58 Z';

function vals(S: DynState): Vals {
  'worklet';
  const p = S.p,
    o = S.o,
    t = S.t,
    ph = S.phase;
  const open = ph === 'open',
    done = ph === 'commit' || open;
  const pp = done ? 1 : clamp(p, 0, 1);
  const oa = open ? seg(o, 0, 0.45) : 0;

  // hold: the engine-turned rings under the pink enamel start to flow outward like ripples on a pond,
  // a bright ring of light travels from the centre to the rim, the white-gold border lights up as it
  // arrives, and the white-gold rosette clicks an eighth of a turn.
  const R: Vals = {};
  const flow = 18 * eio(seg(pp, 0, 0.9));
  for (let i = 0; i < 16; i++) {
    const r = ((i * 6.2 + flow) % 99.2) + 2;
    R['r' + i] = r.toFixed(2);
    R['o' + i] = (0.62 * Math.sin(Math.PI * clamp(r / 100, 0, 1))).toFixed(3);
  }
  const w = seg(pp, 0.05, 0.78);
  const rosT =
    'rotate(' + (22.5 * (pp > 0.82 ? eob(seg(pp, 0.82, 0.92), 2) : 0)).toFixed(2) + ' 150 168)';
  return Object.assign({}, R, {
    waveR: (4 + 100 * eoc(w)).toFixed(2),
    waveOp: (w > 0 && w < 1 ? 0.7 * Math.sin(Math.PI * w) : 0).toFixed(3),
    diaOp: (0.15 + 0.85 * seg(pp, 0.55, 0.8) * (0.75 + 0.25 * Math.sin(t * 9))).toFixed(3),
    rosT,
  });
}

function Defs() {
  return (
    <>
      <LinearGradient id="g12Lid" x1="0%" y1="0%" x2="100%" y2="100%">
        <Stop offset={0} stopColor="#ffe6da" />
        <Stop offset={0.3} stopColor="#f5c3ab" />
        <Stop offset={0.65} stopColor="#dc957a" />
        <Stop offset={1} stopColor="#a95f48" />
      </LinearGradient>
      <LinearGradient id="g12Back" x1="100%" y1="0%" x2="0%" y2="100%">
        <Stop offset={0} stopColor="#dc957a" />
        <Stop offset={1} stopColor="#6e3a2a" />
      </LinearGradient>
      <LinearGradient id="g12Inner" x1="0%" y1="0%" x2="100%" y2="100%">
        <Stop offset={0} stopColor="#ffe6da" />
        <Stop offset={0.5} stopColor="#eeb39b" />
        <Stop offset={1} stopColor="#cf876b" />
      </LinearGradient>
      <RadialGradient id="g12Enamel" cx="45%" cy="40%" r="70%">
        <Stop offset={0} stopColor="#fbd3db" />
        <Stop offset={0.6} stopColor="#ec9fb0" />
        <Stop offset={1} stopColor="#c9667f" />
      </RadialGradient>
      <LinearGradient id="g12Wht" x1="0%" y1="0%" x2="100%" y2="100%">
        <Stop offset={0} stopColor="#ffffff" />
        <Stop offset={0.5} stopColor="#e2e5e9" />
        <Stop offset={1} stopColor="#9aa1a8" />
      </LinearGradient>
      <RadialGradient id="g12Glow">
        <Stop offset={0} stopColor="#fff6f2" stopOpacity={1} />
        <Stop offset={1} stopColor="#fff6f2" stopOpacity={0} />
      </RadialGradient>
      <ClipPath id="g12Clip">
        <Path d={OUTLINE} />
      </ClipPath>
      <ClipPath id="g12Panel">
        <Path d={OUTLINE} transform="translate(150 168) scale(0.8) translate(-150 -168)" />
      </ClipPath>
    </>
  );
}

function Back({ d, place }: DesignProps) {
  return (
    <>
      <G fill="none" stroke="#dc957a" strokeWidth={2.5}>
        <Ellipse cx={150} cy={-24} rx={4} ry={7} />
        <Ellipse cx={150} cy={-12} rx={3} ry={6} stroke="#b06a52" />
        <Ellipse cx={150} cy={0} rx={4} ry={7} />
        <Ellipse cx={150} cy={12} rx={3} ry={6} stroke="#b06a52" />
        <Ellipse cx={150} cy={24} rx={4} ry={7} />
      </G>
      <Circle cx={150} cy={40} r={9} fill="none" stroke="url(#g12Lid)" strokeWidth={4} />
      <Path
        d="M142 58 L146 50 L150 54 L154 50 L158 58 Z"
        fill="url(#g12Wht)"
        stroke="#8d949b"
        strokeWidth={0.9}
      />
      <Path d={OUTLINE} fill="url(#g12Back)" />
      <Path
        d={OUTLINE}
        fill="#fffaf7"
        stroke="#b06a52"
        strokeWidth={1.6}
        transform="translate(150 168) scale(0.9) translate(-150 -168)"
      />
      <Path
        d={OUTLINE}
        fill="none"
        stroke="#dc957a"
        strokeWidth={2.6}
        strokeDasharray="0.1 5"
        strokeLinecap="round"
        transform="translate(150 168) scale(0.82) translate(-150 -168)"
      />
      <Glow cx={150} cy={168} rx={70} ry={86} op={d.glowOp} fill="url(#g12Glow)" />
      <PlaceText place={place} y={164} gap={26} />
      <Path d="M130 174 H170" stroke="#dc957a" strokeWidth={1} />
    </>
  );
}

function Front({ m, d }: DesignProps) {
  const v = useVals(m, vals);
  return (
    <>
      <Path d={OUTLINE} fill="url(#g12Lid)" stroke="#a95f48" strokeWidth={1.5} />
      <Path
        d={OUTLINE}
        fill="none"
        stroke="#ffe6da"
        strokeWidth={1.5}
        transform="translate(150 168) scale(0.96) translate(-150 -168)"
      />
      <Path
        d={OUTLINE}
        fill="none"
        stroke="#8d949b"
        strokeWidth={7.2}
        strokeLinecap="round"
        strokeDasharray="0.01 23.676"
        transform="translate(150 168) scale(0.885) translate(-150 -168)"
      />
      <Path
        d={OUTLINE}
        fill="none"
        stroke="url(#g12Wht)"
        strokeWidth={5.6}
        strokeLinecap="round"
        strokeDasharray="0.01 23.676"
        transform="translate(150 168) scale(0.885) translate(-150 -168)"
      />
      <Dyn
        v={v}
        el="path"
        a={{ opacity: 'diaOp' }}
        d={OUTLINE}
        fill="none"
        stroke="#ffffff"
        strokeWidth={2.4}
        strokeLinecap="round"
        strokeDasharray="0.01 23.676"
        transform="translate(150 168) scale(0.885) translate(-150 -168)"
      />
      <Path
        d={OUTLINE}
        fill="#f1b9a3"
        stroke="#a95f48"
        strokeWidth={1}
        transform="translate(150 168) scale(0.8) translate(-150 -168)"
      />
      <G clipPath="url(#g12Panel)" fill="none" stroke="#a9586a" strokeWidth={1.3}>
        <Dyn v={v} el="circle" a={{ r: 'r0', opacity: 'o0' }} cx={150} cy={168} />
        <Dyn v={v} el="circle" a={{ r: 'r1', opacity: 'o1' }} cx={150} cy={168} />
        <Dyn v={v} el="circle" a={{ r: 'r2', opacity: 'o2' }} cx={150} cy={168} />
        <Dyn v={v} el="circle" a={{ r: 'r3', opacity: 'o3' }} cx={150} cy={168} />
        <Dyn v={v} el="circle" a={{ r: 'r4', opacity: 'o4' }} cx={150} cy={168} />
        <Dyn v={v} el="circle" a={{ r: 'r5', opacity: 'o5' }} cx={150} cy={168} />
        <Dyn v={v} el="circle" a={{ r: 'r6', opacity: 'o6' }} cx={150} cy={168} />
        <Dyn v={v} el="circle" a={{ r: 'r7', opacity: 'o7' }} cx={150} cy={168} />
        <Dyn v={v} el="circle" a={{ r: 'r8', opacity: 'o8' }} cx={150} cy={168} />
        <Dyn v={v} el="circle" a={{ r: 'r9', opacity: 'o9' }} cx={150} cy={168} />
        <Dyn v={v} el="circle" a={{ r: 'r10', opacity: 'o10' }} cx={150} cy={168} />
        <Dyn v={v} el="circle" a={{ r: 'r11', opacity: 'o11' }} cx={150} cy={168} />
        <Dyn v={v} el="circle" a={{ r: 'r12', opacity: 'o12' }} cx={150} cy={168} />
        <Dyn v={v} el="circle" a={{ r: 'r13', opacity: 'o13' }} cx={150} cy={168} />
        <Dyn v={v} el="circle" a={{ r: 'r14', opacity: 'o14' }} cx={150} cy={168} />
        <Dyn v={v} el="circle" a={{ r: 'r15', opacity: 'o15' }} cx={150} cy={168} />
        <Dyn
          v={v}
          el="circle"
          a={{ r: 'waveR', opacity: 'waveOp' }}
          cx={150}
          cy={168}
          stroke="#ffffff"
          strokeWidth={5}
        />
      </G>
      <Path
        d={OUTLINE}
        fill="url(#g12Enamel)"
        opacity={0.62}
        transform="translate(150 168) scale(0.8) translate(-150 -168)"
      />
      <Path
        d="M108 108 C122 88 146 80 166 84"
        fill="none"
        stroke="#ffffff"
        strokeWidth={3}
        strokeLinecap="round"
        opacity={0.45}
        transform="translate(150 168) scale(0.8) translate(-150 -168)"
      />
      <Dyn v={v} el="g" t="rosT">
        <G fill="url(#g12Wht)" stroke="#8d949b" strokeWidth={0.8}>
          <Ellipse cx={150} cy={156} rx={5} ry={10} />
          <Ellipse cx={150} cy={156} rx={5} ry={10} transform="rotate(45 150 168)" />
          <Ellipse cx={150} cy={156} rx={5} ry={10} transform="rotate(90 150 168)" />
          <Ellipse cx={150} cy={156} rx={5} ry={10} transform="rotate(135 150 168)" />
          <Ellipse cx={150} cy={156} rx={5} ry={10} transform="rotate(180 150 168)" />
          <Ellipse cx={150} cy={156} rx={5} ry={10} transform="rotate(225 150 168)" />
          <Ellipse cx={150} cy={156} rx={5} ry={10} transform="rotate(270 150 168)" />
          <Ellipse cx={150} cy={156} rx={5} ry={10} transform="rotate(315 150 168)" />
        </G>
      </Dyn>
      <Circle cx={150} cy={168} r={6} fill="#fbf8f1" stroke="#c9bfae" strokeWidth={0.8} />
      <Circle cx={148.4} cy={166.4} r={1.8} fill="#ffffff" />
      <Rect x={58} y={146} width={8} height={12} rx={2} fill="#a95f48" />
      <Rect x={58} y={184} width={8} height={12} rx={2} fill="#a95f48" />
      <Clasp clasp={d.clasp}>
        <Rect
          x={234}
          y={160}
          width={10}
          height={16}
          rx={3}
          fill="url(#g12Lid)"
          stroke="#a95f48"
          strokeWidth={1}
        />
        <Circle cx={239} cy={168} r={2} fill="#ec9fb0" />
      </Clasp>
    </>
  );
}

function Inner(_: DesignProps) {
  return (
    <>
      <Path d={OUTLINE} fill="url(#g12Inner)" stroke="#a95f48" strokeWidth={1.5} />
      <Path
        d={OUTLINE}
        fill="none"
        stroke="#ffe6da"
        strokeWidth={1}
        transform="translate(150 168) scale(0.9) translate(-150 -168)"
      />
      <Path
        d={OUTLINE}
        fill="none"
        stroke="#a95f48"
        strokeWidth={2.2}
        strokeDasharray="0.1 5"
        strokeLinecap="round"
        transform="translate(150 168) scale(0.82) translate(-150 -168)"
      />
    </>
  );
}

export const GoldRoseEgg: LocketDesign = {
  id: 'roseEgg',
  title: 'Gold XII · Rose-gold guilloché egg',
  period: 'Imperial Russian enamel style, c. 1900',
  cx: 150,
  cy: 168,
  hingeX: 62,
  hingeY: 168,
  outline: OUTLINE,
  sparkles: [
    [252, 104],
    [256, 222],
    [196, 286],
    [52, 96],
    [210, 48],
  ],
  sparkleColors: ['#f5c3ab', '#ec9fb0', '#e2e5e9', '#f5c3ab', '#ec9fb0'],
  edge: ['#6e3a2a', '#a95f48', '#dc957a'],
  holdHaptics: [
    { at: 0.06, kind: 'soft' },
    { at: 0.145, kind: 'soft' },
    { at: 0.23, kind: 'soft' },
    { at: 0.315, kind: 'soft' },
    { at: 0.4, kind: 'soft' },
    { at: 0.485, kind: 'soft' },
    { at: 0.57, kind: 'soft' },
    { at: 0.655, kind: 'soft' },
    { at: 0.74, kind: 'soft' },
    { at: 0.83, kind: 'rigid' },
  ],
  tune: { crack: [0.86, 8], clasp: [0.78, 0.95], shineOp: 0.38 },
  Defs,
  Back,
  Front,
  Inner,
};
