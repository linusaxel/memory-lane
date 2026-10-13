import React from 'react';
import {
  Circle,
  ClipPath,
  G,
  LinearGradient,
  Path,
  RadialGradient,
  Rect,
  Stop,
} from 'react-native-svg';
import { clamp, eio, eob, seg } from '../math.ts';
import { Dyn, useVals, type DynState, type Vals } from '../dyn.tsx';
import { Clasp, Glow, PlaceText } from '../parts.tsx';
import type { DesignProps, LocketDesign } from '../types.ts';

// Gold XVI · Mokume-gane river — Japanese mokume-gane, Edo–Meiji.
// Hold: the folded layers of five golds and shakudō flow like a river under your thumb, then still, and a gold firefly lights in the grain.
// Generated from the canvas board GoldMokume.dc.html by convert.py; the maths in `vals` is the board's own.

const OUTLINE =
  'M257.0 168.0L256.8 172.7L256.2 177.3L255.2 181.8L253.8 186.3L252.0 190.6L250.0 194.8L247.7 198.8L245.1 202.6L242.4 206.3L239.5 209.7L236.6 213.1L233.6 216.2L230.5 219.3L227.5 222.3L224.5 225.2L221.6 228.1L218.6 230.9L215.8 233.8L212.9 236.6L210.1 239.6L207.2 242.5L204.3 245.5L201.3 248.5L198.2 251.6L195.1 254.6L191.7 257.5L188.3 260.4L184.6 263.1L180.8 265.7L176.8 268.0L172.6 270.0L168.3 271.8L163.8 273.2L159.3 274.2L154.7 274.8L150.0 275.0L145.3 274.8L140.7 274.2L136.2 273.2L131.7 271.8L127.4 270.0L123.2 268.0L119.2 265.7L115.4 263.1L111.7 260.4L108.3 257.5L104.9 254.6L101.8 251.6L98.7 248.5L95.7 245.5L92.8 242.5L89.9 239.6L87.1 236.6L84.2 233.8L81.4 230.9L78.4 228.1L75.5 225.2L72.5 222.3L69.5 219.3L66.4 216.3L63.4 213.1L60.5 209.7L57.6 206.3L54.9 202.6L52.3 198.8L50.0 194.8L48.0 190.6L46.2 186.3L44.8 181.8L43.8 177.3L43.2 172.7L43.0 168.0L43.2 163.3L43.8 158.7L44.8 154.2L46.2 149.7L48.0 145.4L50.0 141.2L52.3 137.2L54.9 133.4L57.6 129.7L60.5 126.3L63.4 122.9L66.4 119.7L69.5 116.7L72.5 113.7L75.5 110.8L78.4 107.9L81.4 105.1L84.2 102.2L87.1 99.4L89.9 96.4L92.8 93.5L95.7 90.5L98.7 87.5L101.7 84.4L104.9 81.4L108.3 78.5L111.7 75.6L115.4 72.9L119.2 70.3L123.2 68.0L127.4 66.0L131.7 64.2L136.2 62.8L140.7 61.8L145.3 61.2L150.0 61.0L154.7 61.2L159.3 61.8L163.8 62.8L168.3 64.2L172.6 66.0L176.8 68.0L180.8 70.3L184.6 72.9L188.3 75.6L191.7 78.5L195.1 81.4L198.2 84.4L201.3 87.5L204.3 90.5L207.2 93.5L210.1 96.4L212.9 99.4L215.8 102.2L218.6 105.1L221.6 107.9L224.5 110.8L227.5 113.7L230.5 116.7L233.6 119.8L236.6 122.9L239.5 126.3L242.4 129.7L245.1 133.4L247.7 137.2L250.0 141.2L252.0 145.4L253.8 149.7L255.2 154.2L256.2 158.7L256.8 163.3Z';

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

  // hold: the folded layers of red, yellow, rose, green and white gold and blue-black shakudō start to flow
  // like a river under your thumb — the wood-grain bands ripple and drift, the 'eye' of the grain wanders —
  // then the metal stills, and a single gold firefly lights in the grain.
  const flow =
    2.6 * eio(seg(pp, 0, 0.86)) +
    (ph === 'holding' ? 0.12 * Math.sin(t * 3.2) * seg(pp, 0.05, 0.3) : 0);
  const ex = 146 + 9 * Math.sin(flow * 0.9),
    ey = 172 + 6 * Math.cos(flow * 1.1) - 6;
  const B: Vals = {};
  for (let k = 0; k < 12; k++) {
    const R = 118 - k * 9.6,
      ph1 = k * 0.7,
      ph2 = k * 1.3;
    let d = '';
    for (let i = 0; i <= 64; i++) {
      const th = (i / 64) * Math.PI * 2;
      const r =
        R *
        (1 +
          0.14 * Math.sin(3 * th + ph1 + flow) +
          0.07 * Math.sin(5 * th - ph2 - 0.7 * flow) +
          0.035 * Math.sin(9 * th + 2 * flow + k));
      d +=
        (i ? 'L' : 'M') +
        (ex + r * Math.cos(th)).toFixed(1) +
        ' ' +
        (ey + r * 0.92 * Math.sin(th)).toFixed(1);
    }
    B['b' + k] = d + 'Z';
  }
  const fly = seg(pp, 0.84, 0.96);
  const pulse = 0.85 + 0.15 * Math.sin(t * 6);
  return Object.assign({}, B, {
    fx: (ex + 38).toFixed(2),
    fy: (ey - 36).toFixed(2),
    flyOp: (eob(fly, 1.5) * pulse * (fly > 0 ? 1 : 0)).toFixed(3),
    flyCore: fly > 0 ? Math.min(1, fly * 3).toFixed(3) : 0,
  });
}

function Defs() {
  return (
    <>
      <RadialGradient id="g16Shak" cx="35%" cy="30%" r="85%">
        <Stop offset={0} stopColor="#5a5f7c" />
        <Stop offset={0.45} stopColor="#2e3245" />
        <Stop offset={1} stopColor="#14161e" />
      </RadialGradient>
      <LinearGradient id="g16Back" x1="100%" y1="0%" x2="0%" y2="100%">
        <Stop offset={0} stopColor="#3a3f55" />
        <Stop offset={1} stopColor="#101218" />
      </LinearGradient>
      <LinearGradient id="g16Gold" x1="0%" y1="0%" x2="100%" y2="100%">
        <Stop offset={0} stopColor="#fff1c1" />
        <Stop offset={0.35} stopColor="#f2d58a" />
        <Stop offset={0.7} stopColor="#d4af5a" />
        <Stop offset={1} stopColor="#a8822e" />
      </LinearGradient>
      <LinearGradient id="g16Inner" x1="0%" y1="0%" x2="100%" y2="100%">
        <Stop offset={0} stopColor="#fff1c1" />
        <Stop offset={0.5} stopColor="#e8c77a" />
        <Stop offset={1} stopColor="#c9a24a" />
      </LinearGradient>
      <RadialGradient id="g16Red" cx="40%" cy="35%" r="75%">
        <Stop offset={0} stopColor="#f0a07a" />
        <Stop offset={0.55} stopColor="#c8643e" />
        <Stop offset={1} stopColor="#7c3218" />
      </RadialGradient>
      <RadialGradient id="g16Fly">
        <Stop offset={0} stopColor="#fff6c8" stopOpacity={1} />
        <Stop offset={0.35} stopColor="#f2d58a" stopOpacity={0.7} />
        <Stop offset={1} stopColor="#f2d58a" stopOpacity={0} />
      </RadialGradient>
      <RadialGradient id="g16Sheen" cx="30%" cy="25%" r="90%">
        <Stop offset={0} stopColor="#ffffff" stopOpacity={0.35} />
        <Stop offset={0.5} stopColor="#ffffff" stopOpacity={0.05} />
        <Stop offset={1} stopColor="#ffffff" stopOpacity={0} />
      </RadialGradient>
      <RadialGradient id="g16Glow">
        <Stop offset={0} stopColor="#fff8ea" stopOpacity={1} />
        <Stop offset={1} stopColor="#fff8ea" stopOpacity={0} />
      </RadialGradient>
      <ClipPath id="g16Clip">
        <Path d={OUTLINE} />
      </ClipPath>
      <ClipPath id="g16Panel">
        <Path d={OUTLINE} transform="translate(150 168) scale(0.8) translate(-150 -168)" />
      </ClipPath>
    </>
  );
}

function Back({ d, place }: DesignProps) {
  return (
    <>
      <Path
        d="M150 -34 C126 -14 128 26 146 46 M150 -34 C174 -14 172 26 154 46"
        fill="none"
        stroke="#7d221d"
        strokeWidth={4.4}
        strokeLinecap="round"
      />
      <Path
        d="M150 -34 C126 -14 128 26 146 46 M150 -34 C174 -14 172 26 154 46"
        fill="none"
        stroke="#c9463d"
        strokeWidth={2.4}
        strokeDasharray="3 2.4"
        strokeLinecap="round"
      />
      <Circle cx={150} cy={40} r={8} fill="url(#g16Red)" stroke="#7c3218" strokeWidth={1} />
      <Path d="M145 37 C147 35 151 35 153 37" fill="none" stroke="#f0a07a" strokeWidth={1} />
      <Rect
        x={143}
        y={48}
        width={14}
        height={14}
        rx={3}
        fill="url(#g16Shak)"
        stroke="#d4af5a"
        strokeWidth={1.2}
      />
      <Path d={OUTLINE} fill="url(#g16Back)" />
      <Path
        d={OUTLINE}
        fill="#fffbf4"
        stroke="#d4af5a"
        strokeWidth={1.6}
        transform="translate(150 168) scale(0.88) translate(-150 -168)"
      />
      <Path
        d={OUTLINE}
        fill="none"
        stroke="#c8643e"
        strokeWidth={2.4}
        strokeDasharray="0.1 5"
        strokeLinecap="round"
        transform="translate(150 168) scale(0.8) translate(-150 -168)"
      />
      <Glow cx={150} cy={168} rx={74} ry={74} op={d.glowOp} fill="url(#g16Glow)" />
      <PlaceText place={place} y={164} gap={28} />
      <Path
        d="M124 174 C136 168 144 180 150 174 C156 168 164 180 176 174"
        fill="none"
        stroke="#c8643e"
        strokeWidth={1}
      />
    </>
  );
}

function Front({ m, d }: DesignProps) {
  const v = useVals(m, vals);
  return (
    <>
      <Path d={OUTLINE} fill="url(#g16Shak)" stroke="#a8822e" strokeWidth={1.6} />
      <Path
        d={OUTLINE}
        fill="none"
        stroke="#d4af5a"
        strokeWidth={1.2}
        transform="translate(150 168) scale(0.94) translate(-150 -168)"
      />
      <Path
        d={OUTLINE}
        fill="none"
        stroke="#c8643e"
        strokeWidth={0.9}
        strokeDasharray="6 3"
        transform="translate(150 168) scale(0.885) translate(-150 -168)"
      />
      <G clipPath="url(#g16Panel)">
        <Dyn v={v} el="path" a={{ d: 'b0' }} fill="#c8643e" />
        <Dyn v={v} el="path" a={{ d: 'b1' }} fill="#e9c46a" />
        <Dyn v={v} el="path" a={{ d: 'b2' }} fill="#2c3040" />
        <Dyn v={v} el="path" a={{ d: 'b3' }} fill="#e3a088" />
        <Dyn v={v} el="path" a={{ d: 'b4' }} fill="#d9dbdf" />
        <Dyn v={v} el="path" a={{ d: 'b5' }} fill="#c8643e" />
        <Dyn v={v} el="path" a={{ d: 'b6' }} fill="#b7b46a" />
        <Dyn v={v} el="path" a={{ d: 'b7' }} fill="#2c3040" />
        <Dyn v={v} el="path" a={{ d: 'b8' }} fill="#e9c46a" />
        <Dyn v={v} el="path" a={{ d: 'b9' }} fill="#e3a088" />
        <Dyn v={v} el="path" a={{ d: 'b10' }} fill="#c8643e" />
        <Dyn v={v} el="path" a={{ d: 'b11' }} fill="#e9c46a" />
        <Rect x={40} y={58} width={220} height={220} fill="url(#g16Sheen)" />
        <Dyn
          v={v}
          el="circle"
          a={{ cx: 'fx', cy: 'fy', opacity: 'flyOp' }}
          r={16}
          fill="url(#g16Fly)"
        />
        <Dyn
          v={v}
          el="circle"
          a={{ cx: 'fx', cy: 'fy', opacity: 'flyCore' }}
          r={2.6}
          fill="#fff6c8"
          stroke="#a8822e"
          strokeWidth={0.6}
        />
      </G>
      <Path
        d={OUTLINE}
        fill="none"
        stroke="#a8822e"
        strokeWidth={2}
        transform="translate(150 168) scale(0.8) translate(-150 -168)"
      />
      <Path
        d={OUTLINE}
        fill="none"
        stroke="#fff1c1"
        strokeWidth={0.8}
        transform="translate(150 168) scale(0.81) translate(-150 -168)"
      />
      <Rect x={39} y={146} width={8} height={12} rx={2} fill="#a8822e" />
      <Rect x={39} y={178} width={8} height={12} rx={2} fill="#a8822e" />
      <Clasp clasp={d.clasp}>
        <Rect
          x={253}
          y={160}
          width={10}
          height={16}
          rx={3}
          fill="url(#g16Shak)"
          stroke="#d4af5a"
          strokeWidth={1}
        />
        <Circle cx={258} cy={168} r={1.8} fill="#f2d58a" />
      </Clasp>
    </>
  );
}

function Inner(_: DesignProps) {
  return (
    <>
      <Path d={OUTLINE} fill="url(#g16Inner)" stroke="#a8822e" strokeWidth={1.5} />
      <Path
        d={OUTLINE}
        fill="none"
        stroke="#2c3040"
        strokeWidth={3}
        transform="translate(150 168) scale(0.92) translate(-150 -168)"
      />
      <Path
        d={OUTLINE}
        fill="none"
        stroke="#c8643e"
        strokeWidth={2.2}
        strokeDasharray="0.1 5"
        strokeLinecap="round"
        transform="translate(150 168) scale(0.84) translate(-150 -168)"
      />
    </>
  );
}

export const GoldMokume: LocketDesign = {
  id: 'mokume',
  title: 'Gold XVI · Mokume-gane river',
  period: 'Japanese mokume-gane, Edo\u2013Meiji',
  cx: 150,
  cy: 168,
  hingeX: 43,
  hingeY: 168,
  outline: OUTLINE,
  sparkles: [
    [262, 112],
    [264, 224],
    [204, 292],
    [36, 100],
    [224, 54],
  ],
  sparkleColors: ['#c8643e', '#e9c46a', '#e3a088', '#b7b46a', '#d9dbdf'],
  edge: ['#101218', '#2c3040', '#a8822e'],
  holdHaptics: [
    { at: 0.1, kind: 'soft' },
    { at: 0.2, kind: 'soft' },
    { at: 0.3, kind: 'soft' },
    { at: 0.4, kind: 'soft' },
    { at: 0.5, kind: 'soft' },
    { at: 0.6, kind: 'soft' },
    { at: 0.7, kind: 'soft' },
    { at: 0.8, kind: 'soft' },
    { at: 0.9, kind: 'rigid' },
  ],
  tune: { crack: [0.88, 8], clasp: [0.8, 0.96], shineOp: 0.3 },
  Defs,
  Back,
  Front,
  Inner,
};
