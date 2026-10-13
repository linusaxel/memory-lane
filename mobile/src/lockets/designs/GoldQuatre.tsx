import React from 'react';
import {
  Circle,
  ClipPath,
  Ellipse,
  G,
  LinearGradient,
  Path,
  Pattern,
  RadialGradient,
  Rect,
  Stop,
} from 'react-native-svg';
import { clamp, eio, eob, seg } from '../math.ts';
import { Dyn, useVals, type DynState, type Vals } from '../dyn.tsx';
import { Clasp, Glow, PlaceText } from '../parts.tsx';
import type { DesignProps, LocketDesign } from '../types.ts';

// Gold XI · Quatre-couleur garland — Louis XVI four-colour gold, Paris, c. 1770–90.
// Hold: green-gold stems grow up both sides, leaves and rose-gold buds pop in pairs, a white-gold bow ties itself, the rose blooms.
// Generated from the canvas board GoldQuatre.dc.html by convert.py; the maths in `vals` is the board's own.

const OUTLINE =
  'M83 60 H217 A18 18 0 0 0 235 78 V252 A18 18 0 0 0 217 270 H83 A18 18 0 0 0 65 252 V78 A18 18 0 0 0 83 60 Z';

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

  // hold: a garland grows up both sides of the cartouche from the bottom, leaf by leaf — green-gold leaves,
  // rose-gold buds — a white-gold ribbon ties itself at the top, then the rose-gold rose in the centre blooms.
  const L: Vals = {};
  for (let k = 0; k < 20; k++) {
    const side = k < 10 ? 1 : -1,
      i = k % 10;
    const th = ((90 + side * 17 * (i + 0.5)) * Math.PI) / 180;
    const nx = Math.cos(th) / 68,
      ny = Math.sin(th) / 88,
      nl = Math.hypot(nx, ny);
    const off = i % 2 ? 4.5 : -4.5;
    const x = 150 + 68 * Math.cos(th) + (off * nx) / nl,
      y = 165 + 88 * Math.sin(th) + (off * ny) / nl;
    let ang = (Math.atan2(88 * Math.cos(th), -68 * Math.sin(th)) * 180) / Math.PI;
    if (side < 0) ang += 180;
    ang += (i % 2 ? 28 : -28) * side;
    const g = seg(pp, 0.04 + i * 0.058, 0.12 + i * 0.058);
    const s = g > 0 ? Math.max(0.001, eob(g, 2)) : 0.001;
    L['lf' + k] =
      'translate(' +
      x.toFixed(2) +
      ' ' +
      y.toFixed(2) +
      ') rotate(' +
      ang.toFixed(1) +
      ') scale(' +
      s.toFixed(3) +
      ')';
  }
  const bow = seg(pp, 0.64, 0.76),
    bk = bow > 0 ? Math.max(0.001, eob(bow, 2.2)) : 0.001;
  const bloom = seg(pp, 0.72, 0.92),
    bo = 0.28 + 0.72 * (bloom > 0 ? eob(bloom, 1.6) : 0);
  const bi = 0.5 + 0.5 * (bloom > 0 ? eob(seg(pp, 0.78, 0.95), 1.6) : 0);
  const roseT = (k: number, r: number) =>
    'translate(150 165) rotate(' +
    r.toFixed(1) +
    ') scale(' +
    k.toFixed(3) +
    ') translate(-150 -165)';
  return Object.assign({}, L, {
    stemOff: (100 * (1 - eio(seg(pp, 0, 0.66)))).toFixed(2),
    bowT: 'translate(150 80) scale(' + bk.toFixed(3) + ')',
    roseO: roseT(bo, 20 * (1 - bloom)),
    roseI: roseT(bi, -14 * (1 - bloom)),
  });
}

function Defs() {
  return (
    <>
      <LinearGradient id="g11Yel" x1="0%" y1="0%" x2="100%" y2="100%">
        <Stop offset={0} stopColor="#fff1c1" />
        <Stop offset={0.3} stopColor="#f2d58a" />
        <Stop offset={0.65} stopColor="#d4af5a" />
        <Stop offset={1} stopColor="#a8822e" />
      </LinearGradient>
      <LinearGradient id="g11Back" x1="100%" y1="0%" x2="0%" y2="100%">
        <Stop offset={0} stopColor="#d4af5a" />
        <Stop offset={1} stopColor="#6e5216" />
      </LinearGradient>
      <LinearGradient id="g11Inner" x1="0%" y1="0%" x2="100%" y2="100%">
        <Stop offset={0} stopColor="#fff1c1" />
        <Stop offset={0.5} stopColor="#e8c77a" />
        <Stop offset={1} stopColor="#c9a24a" />
      </LinearGradient>
      <LinearGradient id="g11Grn" x1="0%" y1="0%" x2="100%" y2="100%">
        <Stop offset={0} stopColor="#f1f2c4" />
        <Stop offset={0.5} stopColor="#bfc271" />
        <Stop offset={1} stopColor="#7b8233" />
      </LinearGradient>
      <RadialGradient id="g11Rose" cx="40%" cy="35%" r="75%">
        <Stop offset={0} stopColor="#ffe2d4" />
        <Stop offset={0.5} stopColor="#e9a389" />
        <Stop offset={1} stopColor="#a65a44" />
      </RadialGradient>
      <LinearGradient id="g11Wht" x1="0%" y1="0%" x2="100%" y2="100%">
        <Stop offset={0} stopColor="#ffffff" />
        <Stop offset={0.5} stopColor="#dfe2e6" />
        <Stop offset={1} stopColor="#9aa1a8" />
      </LinearGradient>
      <Pattern id="g11Lines" width={4} height={4} patternUnits="userSpaceOnUse">
        <Path d="M0 2 H4" stroke="#a8822e" strokeWidth={0.6} />
      </Pattern>
      <RadialGradient id="g11Glow">
        <Stop offset={0} stopColor="#fffdf9" stopOpacity={1} />
        <Stop offset={1} stopColor="#fffdf9" stopOpacity={0} />
      </RadialGradient>
      <ClipPath id="g11Clip">
        <Path d={OUTLINE} />
      </ClipPath>
    </>
  );
}

function Back({ d, place }: DesignProps) {
  return (
    <>
      <G fill="none" stroke="#c9a24a" strokeWidth={2.5}>
        <Ellipse cx={150} cy={-24} rx={4} ry={7} />
        <Ellipse cx={150} cy={-12} rx={3} ry={6} stroke="#a8822e" />
        <Ellipse cx={150} cy={0} rx={4} ry={7} />
        <Ellipse cx={150} cy={12} rx={3} ry={6} stroke="#a8822e" />
        <Ellipse cx={150} cy={24} rx={4} ry={7} />
      </G>
      <Circle cx={150} cy={40} r={9} fill="none" stroke="url(#g11Yel)" strokeWidth={4} />
      <Circle cx={150} cy={54} r={5} fill="url(#g11Rose)" stroke="#a65a44" strokeWidth={1} />
      <Path d={OUTLINE} fill="url(#g11Back)" />
      <Path
        d={OUTLINE}
        fill="#fffdf9"
        stroke="#a8822e"
        strokeWidth={1.6}
        transform="translate(150 165) scale(0.9) translate(-150 -165)"
      />
      <Path
        d={OUTLINE}
        fill="none"
        stroke="#bfc271"
        strokeWidth={2.6}
        strokeDasharray="0.1 5"
        strokeLinecap="round"
        transform="translate(150 165) scale(0.82) translate(-150 -165)"
      />
      <Glow cx={150} cy={165} rx={70} ry={90} op={d.glowOp} fill="url(#g11Glow)" />
      <PlaceText place={place} y={160} gap={28} />
      <Path
        d="M124 170 C134 164 142 172 150 168 C158 172 166 164 176 170"
        fill="none"
        stroke="#bfc271"
        strokeWidth={1}
      />
    </>
  );
}

function Front({ m, d }: DesignProps) {
  const v = useVals(m, vals);
  return (
    <>
      <Path d={OUTLINE} fill="url(#g11Yel)" stroke="#a8822e" strokeWidth={1.5} />
      <Path
        d={OUTLINE}
        fill="none"
        stroke="#fff1c1"
        strokeWidth={1.5}
        transform="translate(150 165) scale(0.95) translate(-150 -165)"
      />
      <Path
        d={OUTLINE}
        fill="none"
        stroke="#a8822e"
        strokeWidth={0.8}
        transform="translate(150 165) scale(0.92) translate(-150 -165)"
      />
      <Path
        d={OUTLINE}
        fill="none"
        stroke="#a8822e"
        strokeWidth={3.2}
        strokeDasharray="0.8 2.6"
        transform="translate(150 165) scale(0.875) translate(-150 -165)"
      />
      <Ellipse cx={150} cy={165} rx={56} ry={76} fill="#f6dc97" stroke="#a8822e" strokeWidth={1} />
      <Ellipse cx={150} cy={165} rx={56} ry={76} fill="url(#g11Lines)" opacity={0.55} />
      <Ellipse cx={150} cy={165} rx={52} ry={72} fill="none" stroke="#fff1c1" strokeWidth={1} />
      <G fill="none" stroke="#7b8233" strokeWidth={1.4} strokeLinecap="round">
        <Dyn
          v={v}
          el="path"
          a={{ strokeDashoffset: ['stemOff', 2.46087] }}
          d="M150 253 A68 88 0 0 1 150 77"
          strokeDasharray="246.09 246.09"
        />
        <Dyn
          v={v}
          el="path"
          a={{ strokeDashoffset: ['stemOff', 2.46087] }}
          d="M150 253 A68 88 0 0 0 150 77"
          strokeDasharray="246.09 246.09"
        />
      </G>
      <G stroke="#6f7a2c" strokeWidth={0.6}>
        <Dyn v={v} el="g" t="lf0">
          <Ellipse rx={7.5} ry={3.2} fill="url(#g11Grn)" />
          <Path d="M-6.5 0 H6.5" strokeWidth={0.5} />
        </Dyn>
        <Dyn v={v} el="g" t="lf1">
          <Ellipse rx={7.5} ry={3.2} fill="url(#g11Grn)" />
          <Path d="M-6.5 0 H6.5" strokeWidth={0.5} />
        </Dyn>
        <Dyn v={v} el="g" t="lf2">
          <Circle r={4.6} fill="url(#g11Rose)" stroke="#a65a44" />
          <Path
            d="M-2.6 -0.6 C-1 -3 1 -3 2.6 -0.6 M-2 1.6 C-0.6 0.2 0.6 0.2 2 1.6"
            fill="none"
            stroke="#a65a44"
          />
        </Dyn>
        <Dyn v={v} el="g" t="lf3">
          <Ellipse rx={7.5} ry={3.2} fill="url(#g11Grn)" />
          <Path d="M-6.5 0 H6.5" strokeWidth={0.5} />
        </Dyn>
        <Dyn v={v} el="g" t="lf4">
          <Ellipse rx={7.5} ry={3.2} fill="url(#g11Grn)" />
          <Path d="M-6.5 0 H6.5" strokeWidth={0.5} />
        </Dyn>
        <Dyn v={v} el="g" t="lf5">
          <Circle r={4.6} fill="url(#g11Rose)" stroke="#a65a44" />
          <Path
            d="M-2.6 -0.6 C-1 -3 1 -3 2.6 -0.6 M-2 1.6 C-0.6 0.2 0.6 0.2 2 1.6"
            fill="none"
            stroke="#a65a44"
          />
        </Dyn>
        <Dyn v={v} el="g" t="lf6">
          <Ellipse rx={7.5} ry={3.2} fill="url(#g11Grn)" />
          <Path d="M-6.5 0 H6.5" strokeWidth={0.5} />
        </Dyn>
        <Dyn v={v} el="g" t="lf7">
          <Ellipse rx={7.5} ry={3.2} fill="url(#g11Grn)" />
          <Path d="M-6.5 0 H6.5" strokeWidth={0.5} />
        </Dyn>
        <Dyn v={v} el="g" t="lf8">
          <Circle r={4.6} fill="url(#g11Rose)" stroke="#a65a44" />
          <Path
            d="M-2.6 -0.6 C-1 -3 1 -3 2.6 -0.6 M-2 1.6 C-0.6 0.2 0.6 0.2 2 1.6"
            fill="none"
            stroke="#a65a44"
          />
        </Dyn>
        <Dyn v={v} el="g" t="lf9">
          <Ellipse rx={7.5} ry={3.2} fill="url(#g11Grn)" />
          <Path d="M-6.5 0 H6.5" strokeWidth={0.5} />
        </Dyn>
        <Dyn v={v} el="g" t="lf10">
          <Ellipse rx={7.5} ry={3.2} fill="url(#g11Grn)" />
          <Path d="M-6.5 0 H6.5" strokeWidth={0.5} />
        </Dyn>
        <Dyn v={v} el="g" t="lf11">
          <Ellipse rx={7.5} ry={3.2} fill="url(#g11Grn)" />
          <Path d="M-6.5 0 H6.5" strokeWidth={0.5} />
        </Dyn>
        <Dyn v={v} el="g" t="lf12">
          <Circle r={4.6} fill="url(#g11Rose)" stroke="#a65a44" />
          <Path
            d="M-2.6 -0.6 C-1 -3 1 -3 2.6 -0.6 M-2 1.6 C-0.6 0.2 0.6 0.2 2 1.6"
            fill="none"
            stroke="#a65a44"
          />
        </Dyn>
        <Dyn v={v} el="g" t="lf13">
          <Ellipse rx={7.5} ry={3.2} fill="url(#g11Grn)" />
          <Path d="M-6.5 0 H6.5" strokeWidth={0.5} />
        </Dyn>
        <Dyn v={v} el="g" t="lf14">
          <Ellipse rx={7.5} ry={3.2} fill="url(#g11Grn)" />
          <Path d="M-6.5 0 H6.5" strokeWidth={0.5} />
        </Dyn>
        <Dyn v={v} el="g" t="lf15">
          <Circle r={4.6} fill="url(#g11Rose)" stroke="#a65a44" />
          <Path
            d="M-2.6 -0.6 C-1 -3 1 -3 2.6 -0.6 M-2 1.6 C-0.6 0.2 0.6 0.2 2 1.6"
            fill="none"
            stroke="#a65a44"
          />
        </Dyn>
        <Dyn v={v} el="g" t="lf16">
          <Ellipse rx={7.5} ry={3.2} fill="url(#g11Grn)" />
          <Path d="M-6.5 0 H6.5" strokeWidth={0.5} />
        </Dyn>
        <Dyn v={v} el="g" t="lf17">
          <Ellipse rx={7.5} ry={3.2} fill="url(#g11Grn)" />
          <Path d="M-6.5 0 H6.5" strokeWidth={0.5} />
        </Dyn>
        <Dyn v={v} el="g" t="lf18">
          <Circle r={4.6} fill="url(#g11Rose)" stroke="#a65a44" />
          <Path
            d="M-2.6 -0.6 C-1 -3 1 -3 2.6 -0.6 M-2 1.6 C-0.6 0.2 0.6 0.2 2 1.6"
            fill="none"
            stroke="#a65a44"
          />
        </Dyn>
        <Dyn v={v} el="g" t="lf19">
          <Ellipse rx={7.5} ry={3.2} fill="url(#g11Grn)" />
          <Path d="M-6.5 0 H6.5" strokeWidth={0.5} />
        </Dyn>
      </G>
      <Dyn v={v} el="g" t="bowT">
        <Path
          d="M0 0 C-10 -12 -26 -10 -22 0 C-20 6 -8 4 0 0 Z M0 0 C10 -12 26 -10 22 0 C20 6 8 4 0 0 Z"
          fill="url(#g11Wht)"
          stroke="#8d949b"
          strokeWidth={0.9}
        />
        <Path
          d="M0 0 C-4 8 -10 14 -14 20 M0 0 C4 8 10 14 14 20"
          fill="none"
          stroke="#8d949b"
          strokeWidth={3.2}
          strokeLinecap="round"
        />
        <Path
          d="M0 0 C-4 8 -10 14 -14 20 M0 0 C4 8 10 14 14 20"
          fill="none"
          stroke="#f4f6f8"
          strokeWidth={1.8}
          strokeLinecap="round"
        />
        <Ellipse rx={4} ry={3.4} fill="url(#g11Wht)" stroke="#8d949b" strokeWidth={0.9} />
      </Dyn>
      <Dyn v={v} el="g" t="roseO">
        <Ellipse
          cx={150}
          cy={151}
          rx={9}
          ry={13}
          fill="url(#g11Rose)"
          stroke="#a65a44"
          strokeWidth={0.9}
          transform="rotate(0 150 165)"
        />
        <Ellipse
          cx={150}
          cy={151}
          rx={9}
          ry={13}
          fill="url(#g11Rose)"
          stroke="#a65a44"
          strokeWidth={0.9}
          transform="rotate(72 150 165)"
        />
        <Ellipse
          cx={150}
          cy={151}
          rx={9}
          ry={13}
          fill="url(#g11Rose)"
          stroke="#a65a44"
          strokeWidth={0.9}
          transform="rotate(144 150 165)"
        />
        <Ellipse
          cx={150}
          cy={151}
          rx={9}
          ry={13}
          fill="url(#g11Rose)"
          stroke="#a65a44"
          strokeWidth={0.9}
          transform="rotate(216 150 165)"
        />
        <Ellipse
          cx={150}
          cy={151}
          rx={9}
          ry={13}
          fill="url(#g11Rose)"
          stroke="#a65a44"
          strokeWidth={0.9}
          transform="rotate(288 150 165)"
        />
      </Dyn>
      <Dyn v={v} el="g" t="roseI">
        <Ellipse
          cx={150}
          cy={158}
          rx={5.5}
          ry={8}
          fill="url(#g11Rose)"
          stroke="#a65a44"
          strokeWidth={0.8}
          transform="rotate(36 150 165)"
        />
        <Ellipse
          cx={150}
          cy={158}
          rx={5.5}
          ry={8}
          fill="url(#g11Rose)"
          stroke="#a65a44"
          strokeWidth={0.8}
          transform="rotate(108 150 165)"
        />
        <Ellipse
          cx={150}
          cy={158}
          rx={5.5}
          ry={8}
          fill="url(#g11Rose)"
          stroke="#a65a44"
          strokeWidth={0.8}
          transform="rotate(180 150 165)"
        />
        <Ellipse
          cx={150}
          cy={158}
          rx={5.5}
          ry={8}
          fill="url(#g11Rose)"
          stroke="#a65a44"
          strokeWidth={0.8}
          transform="rotate(252 150 165)"
        />
        <Ellipse
          cx={150}
          cy={158}
          rx={5.5}
          ry={8}
          fill="url(#g11Rose)"
          stroke="#a65a44"
          strokeWidth={0.8}
          transform="rotate(324 150 165)"
        />
      </Dyn>
      <Circle cx={150} cy={165} r={4.5} fill="url(#g11Rose)" stroke="#a65a44" strokeWidth={0.8} />
      <Path d="M147 163 C149 161 152 162 152 165" fill="none" stroke="#a65a44" strokeWidth={0.7} />
      <Rect x={61} y={140} width={8} height={12} rx={2} fill="#a8822e" />
      <Rect x={61} y={178} width={8} height={12} rx={2} fill="#a8822e" />
      <Clasp clasp={d.clasp}>
        <Rect
          x={231}
          y={157}
          width={10}
          height={16}
          rx={3}
          fill="url(#g11Rose)"
          stroke="#a65a44"
          strokeWidth={1}
        />
      </Clasp>
    </>
  );
}

function Inner(_: DesignProps) {
  return (
    <>
      <Path d={OUTLINE} fill="url(#g11Inner)" stroke="#a8822e" strokeWidth={1.5} />
      <Path
        d={OUTLINE}
        fill="none"
        stroke="#fff1c1"
        strokeWidth={1}
        transform="translate(150 165) scale(0.9) translate(-150 -165)"
      />
      <Path
        d={OUTLINE}
        fill="none"
        stroke="#bfc271"
        strokeWidth={2.2}
        strokeDasharray="0.1 5"
        strokeLinecap="round"
        transform="translate(150 165) scale(0.82) translate(-150 -165)"
      />
    </>
  );
}

export const GoldQuatre: LocketDesign = {
  id: 'quatre',
  title: 'Gold XI · Quatre-couleur garland',
  period: 'Louis XVI four-colour gold, Paris, c. 1770\u201390',
  cx: 150,
  cy: 165,
  hingeX: 65,
  hingeY: 165,
  outline: OUTLINE,
  sparkles: [
    [250, 100],
    [256, 214],
    [200, 284],
    [56, 92],
    [214, 46],
  ],
  sparkleColors: ['#e9a389', '#bfc271', '#dfe2e6', '#e8c77a', '#e9a389'],
  edge: ['#6e5216', '#a8822e', '#c9a24a'],
  holdHaptics: [
    { at: 0.07, kind: 'soft' },
    { at: 0.128, kind: 'soft' },
    { at: 0.186, kind: 'soft' },
    { at: 0.244, kind: 'soft' },
    { at: 0.302, kind: 'soft' },
    { at: 0.36, kind: 'soft' },
    { at: 0.418, kind: 'soft' },
    { at: 0.476, kind: 'soft' },
    { at: 0.534, kind: 'soft' },
    { at: 0.592, kind: 'soft' },
    { at: 0.7, kind: 'light' },
    { at: 0.8, kind: 'rigid' },
  ],
  tune: { crack: [0.86, 8], clasp: [0.78, 0.95], shineOp: 0.42 },
  Defs,
  Back,
  Front,
  Inner,
};
