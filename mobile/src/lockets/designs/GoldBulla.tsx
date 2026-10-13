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
import { clamp, eob, seg } from '../math.ts';
import { Dyn, useVals, type DynState, type Vals } from '../dyn.tsx';
import { Clasp, Glow, PlaceText } from '../parts.tsx';
import type { DesignProps, LocketDesign } from '../types.ts';

// Gold XV · Etruscan bulla — Etruscan Revival (Castellani, Rome), 1860s, 22k.
// Hold: grains of gold roll into place round the outer, middle and inner rings, a loose grain bouncing at the front; then the boss blooms into a rosette.
// Generated from the canvas board GoldBulla.dc.html by convert.py; the maths in `vals` is the board's own.

const OUTLINE = 'M54 174A96 96 0 1 0 246 174A96 96 0 1 0 54 174Z';

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

  // hold: the goldsmith granulates the bulla — tiny gold grains roll into place one after another,
  // sweeping round the outer ring, then the middle, then the inner, a loose grain bouncing at the
  // front of each sweep; then the boss in the centre blooms into a rosette of grains.
  const f1 = seg(pp, 0.02, 0.34),
    f2 = seg(pp, 0.3, 0.56),
    f3 = seg(pp, 0.52, 0.74);
  const cur = f1 < 1 ? [f1, 82] : f2 < 1 ? [f2, 63.5] : [f3, 45];
  const ga = ((-90 + 360 * cur[0]) * Math.PI) / 180;
  const hop = 6 * Math.abs(Math.sin(cur[0] * 60));
  const filling = ph === 'holding' && cur[0] > 0 && cur[0] < 1;
  const boss = seg(pp, 0.76, 0.9),
    bk = boss > 0 ? Math.max(0.001, eob(boss, 2)) : 0.001;
  const arc = (f: number, cx: number, cy: number, r: number) => {
    if (f <= 0.001) return 'M' + cx + ' ' + (cy - r);
    if (f >= 0.999)
      return (
        'M' +
        cx +
        ' ' +
        (cy - r) +
        ' A' +
        r +
        ' ' +
        r +
        ' 0 1 1 ' +
        cx +
        ' ' +
        (cy + r) +
        ' A' +
        r +
        ' ' +
        r +
        ' 0 1 1 ' +
        cx +
        ' ' +
        (cy - r)
      );
    const a = ((-90 + 360 * f) * Math.PI) / 180;
    return (
      'M' +
      cx +
      ' ' +
      (cy - r) +
      ' A' +
      r +
      ' ' +
      r +
      ' 0 ' +
      (f > 0.5 ? 1 : 0) +
      ' 1 ' +
      (cx + r * Math.cos(a)).toFixed(2) +
      ' ' +
      (cy + r * Math.sin(a)).toFixed(2)
    );
  };
  return Object.assign(
    {},
    {
      a1: arc(f1, 150, 174, 82),
      a1h: arc(f1, 149.3, 173.3, 82),
      a2: arc(f2, 150, 174, 63.5),
      a2h: arc(f2, 149.3, 173.3, 63.5),
      a3: arc(f3, 150, 174, 45),
      a3h: arc(f3, 149.3, 173.3, 45),
      gx: (150 + cur[1] * Math.cos(ga)).toFixed(2),
      gy: (174 + cur[1] * Math.sin(ga) - hop).toFixed(2),
      gOp: filling ? 1 : 0,
      bossT: 'translate(150 174) scale(' + bk.toFixed(3) + ') translate(-150 -174)',
      bossOp: boss > 0 ? 1 : 0,
    },
  );
}

function Defs() {
  return (
    <>
      <LinearGradient id="g15Lid" x1="0%" y1="0%" x2="100%" y2="100%">
        <Stop offset={0} stopColor="#fff0b8" />
        <Stop offset={0.3} stopColor="#f7cd63" />
        <Stop offset={0.65} stopColor="#e3a632" />
        <Stop offset={1} stopColor="#b97a17" />
      </LinearGradient>
      <LinearGradient id="g15Back" x1="100%" y1="0%" x2="0%" y2="100%">
        <Stop offset={0} stopColor="#e3a632" />
        <Stop offset={1} stopColor="#6e430b" />
      </LinearGradient>
      <LinearGradient id="g15Inner" x1="0%" y1="0%" x2="100%" y2="100%">
        <Stop offset={0} stopColor="#fff0b8" />
        <Stop offset={0.5} stopColor="#f2c35b" />
        <Stop offset={1} stopColor="#d69a2a" />
      </LinearGradient>
      <LinearGradient id="g15Tube" x1="0%" y1="0%" x2="100%" y2="0%">
        <Stop offset={0} stopColor="#b97a17" />
        <Stop offset={0.35} stopColor="#fff0b8" />
        <Stop offset={0.6} stopColor="#f7cd63" />
        <Stop offset={1} stopColor="#8a5510" />
      </LinearGradient>
      <RadialGradient id="g15Dome" cx="38%" cy="32%" r="80%">
        <Stop offset={0} stopColor="#fff6d6" />
        <Stop offset={0.45} stopColor="#f7cd63" />
        <Stop offset={1} stopColor="#b97a17" />
      </RadialGradient>
      <RadialGradient id="g15Glow">
        <Stop offset={0} stopColor="#fffaf0" stopOpacity={1} />
        <Stop offset={1} stopColor="#fffaf0" stopOpacity={0} />
      </RadialGradient>
      <ClipPath id="g15Clip">
        <Circle cx={150} cy={174} r={96} />
      </ClipPath>
    </>
  );
}

function Back({ d, place }: DesignProps) {
  return (
    <>
      <G fill="none" stroke="#e3a632" strokeWidth={2.5}>
        <Ellipse cx={150} cy={-24} rx={4} ry={7} />
        <Ellipse cx={150} cy={-12} rx={3} ry={6} stroke="#b97a17" />
        <Ellipse cx={150} cy={0} rx={4} ry={7} />
        <Ellipse cx={150} cy={12} rx={3} ry={6} stroke="#b97a17" />
        <Ellipse cx={150} cy={24} rx={4} ry={7} />
      </G>
      <Circle cx={150} cy={40} r={9} fill="none" stroke="url(#g15Lid)" strokeWidth={4} />
      <Rect
        x={130}
        y={50}
        width={40}
        height={32}
        rx={10}
        fill="url(#g15Tube)"
        stroke="#8a5510"
        strokeWidth={1}
      />
      <Path
        d="M137 51 V81 M143.5 50 V82 M150 50 V82 M156.5 50 V82 M163 51 V81"
        stroke="#8a5510"
        strokeWidth={1}
        opacity={0.7}
      />
      <Path
        d="M131 56 H169 M131 76 H169"
        stroke="#fff0b8"
        strokeWidth={1.6}
        strokeDasharray="0.01 3.4"
        strokeLinecap="round"
      />
      <Circle cx={150} cy={174} r={96} fill="url(#g15Back)" />
      <Circle cx={150} cy={174} r={86} fill="#fffbf2" stroke="#b97a17" strokeWidth={1.6} />
      <Circle
        cx={150}
        cy={174}
        r={78}
        fill="none"
        stroke="#e3a632"
        strokeWidth={2.6}
        strokeDasharray="0.1 5"
        strokeLinecap="round"
      />
      <Glow cx={150} cy={174} rx={76} ry={76} op={d.glowOp} fill="url(#g15Glow)" />
      <PlaceText place={place} y={170} gap={26} />
      <Path
        d="M126 180 H174"
        stroke="#e3a632"
        strokeWidth={1}
        strokeDasharray="0.01 3.2"
        strokeLinecap="round"
      />
    </>
  );
}

function Front({ m, d }: DesignProps) {
  const v = useVals(m, vals);
  return (
    <>
      <Circle cx={150} cy={174} r={96} fill="url(#g15Lid)" stroke="#b97a17" strokeWidth={1.5} />
      <G fill="none">
        <Circle cx={150} cy={174} r={91} stroke="#8a5510" strokeWidth={3.4} />
        <Circle
          cx={150}
          cy={174}
          r={91}
          stroke="#fff0b8"
          strokeWidth={1.4}
          strokeDasharray="2.4 1.6"
        />
        <Circle cx={150} cy={174} r={73} stroke="#8a5510" strokeWidth={3} />
        <Circle
          cx={150}
          cy={174}
          r={73}
          stroke="#fff0b8"
          strokeWidth={1.2}
          strokeDasharray="2.2 1.6"
        />
        <Circle cx={150} cy={174} r={54} stroke="#8a5510" strokeWidth={3} />
        <Circle
          cx={150}
          cy={174}
          r={54}
          stroke="#fff0b8"
          strokeWidth={1.2}
          strokeDasharray="2.2 1.6"
        />
        <Circle cx={150} cy={174} r={36} stroke="#8a5510" strokeWidth={2.6} />
        <Circle cx={150} cy={174} r={36} stroke="#fff0b8" strokeWidth={1} strokeDasharray="2 1.5" />
      </G>
      <G fill="none" strokeLinecap="round">
        <G>
          <Dyn
            v={v}
            el="path"
            a={{ d: 'a1' }}
            stroke="#8a5510"
            strokeWidth={6}
            strokeDasharray="0.01 9.2"
          />
          <Dyn
            v={v}
            el="path"
            a={{ d: 'a1' }}
            stroke="#f7cd63"
            strokeWidth={4.6}
            strokeDasharray="0.01 9.2"
          />
          <Dyn
            v={v}
            el="path"
            a={{ d: 'a1h' }}
            stroke="#fff6d6"
            strokeWidth={1.8}
            strokeDasharray="0.01 9.2"
          />
        </G>
        <G>
          <Dyn
            v={v}
            el="path"
            a={{ d: 'a2' }}
            stroke="#8a5510"
            strokeWidth={5.6}
            strokeDasharray="0.01 9.07"
          />
          <Dyn
            v={v}
            el="path"
            a={{ d: 'a2' }}
            stroke="#f7cd63"
            strokeWidth={4.2}
            strokeDasharray="0.01 9.07"
          />
          <Dyn
            v={v}
            el="path"
            a={{ d: 'a2h' }}
            stroke="#fff6d6"
            strokeWidth={1.6}
            strokeDasharray="0.01 9.07"
          />
        </G>
        <G>
          <Dyn
            v={v}
            el="path"
            a={{ d: 'a3' }}
            stroke="#8a5510"
            strokeWidth={5.2}
            strokeDasharray="0.01 8.84"
          />
          <Dyn
            v={v}
            el="path"
            a={{ d: 'a3' }}
            stroke="#f7cd63"
            strokeWidth={3.8}
            strokeDasharray="0.01 8.84"
          />
          <Dyn
            v={v}
            el="path"
            a={{ d: 'a3h' }}
            stroke="#fff6d6"
            strokeWidth={1.4}
            strokeDasharray="0.01 8.84"
          />
        </G>
      </G>
      <Dyn
        v={v}
        el="circle"
        a={{ cx: 'gx', cy: 'gy', opacity: 'gOp' }}
        r={3.4}
        fill="url(#g15Dome)"
        stroke="#8a5510"
        strokeWidth={0.8}
      />
      <Circle cx={150} cy={174} r={26} fill="url(#g15Dome)" stroke="#8a5510" strokeWidth={1.2} />
      <Circle
        cx={150}
        cy={174}
        r={21}
        fill="none"
        stroke="#fff0b8"
        strokeWidth={0.9}
        opacity={0.7}
      />
      <Dyn v={v} el="g" t="bossT" a={{ opacity: 'bossOp' }}>
        <G fill="url(#g15Dome)" stroke="#8a5510" strokeWidth={0.6}>
          <Circle cx={150} cy={174} r={3.4} />
          <Circle cx={150} cy={166.5} r={3} />
          <Circle cx={156.5} cy={170.2} r={3} />
          <Circle cx={156.5} cy={177.8} r={3} />
          <Circle cx={150} cy={181.5} r={3} />
          <Circle cx={143.5} cy={177.8} r={3} />
          <Circle cx={143.5} cy={170.2} r={3} />
          <Circle cx={150} cy={158.5} r={2.6} />
          <Circle cx={158} cy={160.6} r={2.6} />
          <Circle cx={163.9} cy={166.5} r={2.6} />
          <Circle cx={166} cy={174} r={2.6} />
          <Circle cx={163.9} cy={181.5} r={2.6} />
          <Circle cx={158} cy={187.4} r={2.6} />
          <Circle cx={150} cy={189.5} r={2.6} />
          <Circle cx={142} cy={187.4} r={2.6} />
          <Circle cx={136.1} cy={181.5} r={2.6} />
          <Circle cx={134} cy={174} r={2.6} />
          <Circle cx={136.1} cy={166.5} r={2.6} />
          <Circle cx={142} cy={160.6} r={2.6} />
        </G>
      </Dyn>
      <Rect x={50} y={150} width={8} height={12} rx={2} fill="#b97a17" />
      <Rect x={50} y={186} width={8} height={12} rx={2} fill="#b97a17" />
      <Clasp clasp={d.clasp}>
        <Rect
          x={242}
          y={166}
          width={10}
          height={16}
          rx={5}
          fill="url(#g15Tube)"
          stroke="#8a5510"
          strokeWidth={1}
        />
      </Clasp>
    </>
  );
}

function Inner(_: DesignProps) {
  return (
    <>
      <Circle cx={150} cy={174} r={96} fill="url(#g15Inner)" stroke="#b97a17" strokeWidth={1.5} />
      <Circle cx={150} cy={174} r={86} fill="none" stroke="#fff0b8" strokeWidth={1} />
      <Circle
        cx={150}
        cy={174}
        r={78}
        fill="none"
        stroke="#b97a17"
        strokeWidth={2.2}
        strokeDasharray="0.1 5"
        strokeLinecap="round"
      />
    </>
  );
}

export const GoldBulla: LocketDesign = {
  id: 'bulla',
  title: 'Gold XV · Etruscan bulla',
  period: 'Etruscan Revival (Castellani, Rome), 1860s, 22k',
  cx: 150,
  cy: 174,
  hingeX: 54,
  hingeY: 174,
  outline: OUTLINE,
  sparkles: [
    [256, 116],
    [258, 226],
    [204, 292],
    [52, 100],
    [222, 60],
  ],
  sparkleColors: ['#f7cd63', '#fff0b8', '#e3a632', '#f7cd63', '#fff0b8'],
  edge: ['#6e430b', '#b97a17', '#e3a632'],
  holdHaptics: [
    { at: 0.04, kind: 'selection' },
    { at: 0.062, kind: 'selection' },
    { at: 0.083, kind: 'selection' },
    { at: 0.105, kind: 'selection' },
    { at: 0.126, kind: 'selection' },
    { at: 0.148, kind: 'selection' },
    { at: 0.169, kind: 'selection' },
    { at: 0.191, kind: 'selection' },
    { at: 0.212, kind: 'selection' },
    { at: 0.234, kind: 'selection' },
    { at: 0.255, kind: 'selection' },
    { at: 0.277, kind: 'selection' },
    { at: 0.298, kind: 'selection' },
    { at: 0.32, kind: 'selection' },
    { at: 0.32, kind: 'selection' },
    { at: 0.342, kind: 'selection' },
    { at: 0.364, kind: 'selection' },
    { at: 0.386, kind: 'selection' },
    { at: 0.408, kind: 'selection' },
    { at: 0.43, kind: 'selection' },
    { at: 0.452, kind: 'selection' },
    { at: 0.474, kind: 'selection' },
    { at: 0.496, kind: 'selection' },
    { at: 0.518, kind: 'selection' },
    { at: 0.54, kind: 'selection' },
    { at: 0.54, kind: 'selection' },
    { at: 0.566, kind: 'selection' },
    { at: 0.591, kind: 'selection' },
    { at: 0.617, kind: 'selection' },
    { at: 0.643, kind: 'selection' },
    { at: 0.669, kind: 'selection' },
    { at: 0.694, kind: 'selection' },
    { at: 0.72, kind: 'selection' },
    { at: 0.34, kind: 'rigid' },
    { at: 0.56, kind: 'rigid' },
    { at: 0.74, kind: 'rigid' },
    { at: 0.83, kind: 'medium' },
  ],
  tune: { crack: [0.86, 8], clasp: [0.78, 0.95], shineOp: 0.36 },
  Defs,
  Back,
  Front,
  Inner,
};
