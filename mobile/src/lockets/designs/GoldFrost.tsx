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
import { clamp, eio, eob, seg } from '../math.ts';
import { Dyn, useVals, type DynState, type Vals } from '../dyn.tsx';
import { Clasp, Glow, PlaceText } from '../parts.tsx';
import type { DesignProps, LocketDesign } from '../types.ts';

// Gold XIV · White-gold frost — Art Deco white gold and rock crystal, c. 1925–35.
// Hold: frost creeps across the crystal from the four corners and branches, the pane mists, a snowflake snaps into being, the sapphire glints.
// Generated from the canvas board GoldFrost.dc.html by convert.py; the maths in `vals` is the board's own.

const OUTLINE =
  'M112 62 H188 V72 H204 V84 H220 V252 A14 14 0 0 1 206 266 H94 A14 14 0 0 1 80 252 V84 H96 V72 H112 Z';

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

  // hold: frost creeps across the rock-crystal window from all four corners, branching as it grows
  // (your warm thumb against cold white gold), the pane mists over, a six-armed crystal snaps into being
  // in the middle with a twist, and the step-cut sapphire below throws one glint.
  const grow = eio(seg(pp, 0, 0.62));
  const fd = (72 * grow).toFixed(2) + ' 400';
  const td = (17 * eio(seg(pp, 0.18, 0.66))).toFixed(2) + ' 400';
  const fl = seg(pp, 0.56, 0.82),
    fk = fl > 0 ? Math.max(0.001, eob(fl, 1.8)) : 0.001;
  const g = Math.max(0, Math.sin(Math.PI * seg(pp, 0.82, 1)));
  return Object.assign(
    {},
    {
      fd,
      td,
      bloomOp: (0.32 * eio(seg(pp, 0.3, 0.8))).toFixed(3),
      flakeT:
        'translate(150 167) rotate(' +
        (-30 * (1 - Math.min(1, fk))).toFixed(2) +
        ') scale(' +
        fk.toFixed(3) +
        ')',
      flakeOp: fl > 0 ? 1 : 0,
      glintT:
        'translate(156 248) rotate(' +
        (60 * g).toFixed(1) +
        ') scale(' +
        Math.max(0.001, 1.1 * g).toFixed(3) +
        ')',
      fdOff: 400 - parseFloat(fd),
      tdOff: 400 - parseFloat(td),
    },
  );
}

function Defs() {
  return (
    <>
      <LinearGradient id="g14Lid" x1="0%" y1="0%" x2="100%" y2="100%">
        <Stop offset={0} stopColor="#ffffff" />
        <Stop offset={0.3} stopColor="#eef1f4" />
        <Stop offset={0.65} stopColor="#cdd3da" />
        <Stop offset={1} stopColor="#97a0aa" />
      </LinearGradient>
      <LinearGradient id="g14Back" x1="100%" y1="0%" x2="0%" y2="100%">
        <Stop offset={0} stopColor="#cdd3da" />
        <Stop offset={1} stopColor="#5b636c" />
      </LinearGradient>
      <LinearGradient id="g14Inner" x1="0%" y1="0%" x2="100%" y2="100%">
        <Stop offset={0} stopColor="#ffffff" />
        <Stop offset={0.5} stopColor="#e3e7eb" />
        <Stop offset={1} stopColor="#b9c0c8" />
      </LinearGradient>
      <LinearGradient id="g14Crystal" x1="0%" y1="0%" x2="60%" y2="100%">
        <Stop offset={0} stopColor="#f6f9fc" />
        <Stop offset={0.5} stopColor="#d7e3ee" />
        <Stop offset={1} stopColor="#eaf1f7" />
      </LinearGradient>
      <LinearGradient id="g14Sapph" x1="0%" y1="0%" x2="100%" y2="100%">
        <Stop offset={0} stopColor="#7a9be2" />
        <Stop offset={0.5} stopColor="#2f56b0" />
        <Stop offset={1} stopColor="#172f6e" />
      </LinearGradient>
      <RadialGradient id="g14Glow">
        <Stop offset={0} stopColor="#f6faff" stopOpacity={1} />
        <Stop offset={1} stopColor="#f6faff" stopOpacity={0} />
      </RadialGradient>
      <ClipPath id="g14Clip">
        <Path d={OUTLINE} />
      </ClipPath>
      <ClipPath id="g14Pane">
        <Rect x={100} y={100} width={100} height={134} rx={4} />
      </ClipPath>
    </>
  );
}

function Back({ d, place }: DesignProps) {
  return (
    <>
      <G fill="none" stroke="#b9c0c8" strokeWidth={2.5}>
        <Ellipse cx={150} cy={-24} rx={4} ry={7} />
        <Ellipse cx={150} cy={-12} rx={3} ry={6} stroke="#97a0aa" />
        <Ellipse cx={150} cy={0} rx={4} ry={7} />
        <Ellipse cx={150} cy={12} rx={3} ry={6} stroke="#97a0aa" />
        <Ellipse cx={150} cy={24} rx={4} ry={7} />
      </G>
      <Rect
        x={139}
        y={32}
        width={22}
        height={16}
        rx={3}
        fill="none"
        stroke="url(#g14Lid)"
        strokeWidth={4}
      />
      <Rect
        x={144}
        y={48}
        width={12}
        height={8}
        fill="url(#g14Lid)"
        stroke="#97a0aa"
        strokeWidth={0.8}
      />
      <Rect
        x={140}
        y={55}
        width={20}
        height={8}
        fill="url(#g14Lid)"
        stroke="#97a0aa"
        strokeWidth={0.8}
      />
      <Path d={OUTLINE} fill="url(#g14Back)" />
      <Path
        d={OUTLINE}
        fill="#fbfcfd"
        stroke="#97a0aa"
        strokeWidth={1.6}
        transform="translate(150 164) scale(0.9) translate(-150 -164)"
      />
      <Path
        d={OUTLINE}
        fill="none"
        stroke="#7a9be2"
        strokeWidth={2.4}
        strokeDasharray="0.1 5"
        strokeLinecap="round"
        transform="translate(150 164) scale(0.82) translate(-150 -164)"
      />
      <Glow cx={150} cy={164} rx={60} ry={84} op={d.glowOp} fill="url(#g14Glow)" />
      <PlaceText place={place} y={160} gap={32} />
      <Path d="M126 170 H174 M136 175 H164" stroke="#7a9be2" strokeWidth={1} />
    </>
  );
}

function Front({ m, d }: DesignProps) {
  const v = useVals(m, vals);
  return (
    <>
      <Path d={OUTLINE} fill="url(#g14Lid)" stroke="#97a0aa" strokeWidth={1.5} />
      <Path
        d={OUTLINE}
        fill="none"
        stroke="#ffffff"
        strokeWidth={1.5}
        transform="translate(150 164) scale(0.95) translate(-150 -164)"
      />
      <G stroke="#97a0aa" strokeWidth={0.9}>
        <Path d="M88 96 V246 M92 96 V246 M208 96 V246 M212 96 V246" />
        <Path d="M104 80 H196 M104 86 H196" />
      </G>
      <G fill="url(#g14Sapph)" stroke="#172f6e" strokeWidth={0.6}>
        <Rect x={128} y={66} width={7} height={4} rx={0.6} />
        <Rect x={137} y={66} width={7} height={4} rx={0.6} />
        <Rect x={146.5} y={66} width={7} height={4} rx={0.6} />
        <Rect x={156} y={66} width={7} height={4} rx={0.6} />
        <Rect x={165} y={66} width={7} height={4} rx={0.6} />
      </G>
      <Rect
        x={98}
        y={98}
        width={104}
        height={138}
        rx={5}
        fill="url(#g14Lid)"
        stroke="#97a0aa"
        strokeWidth={1}
      />
      <Rect x={100} y={100} width={100} height={134} rx={4} fill="url(#g14Crystal)" />
      <G clipPath="url(#g14Pane)">
        <Path
          d="M100 150 L200 108 M100 200 L200 158"
          stroke="#ffffff"
          strokeWidth={8}
          opacity={0.35}
        />
        <Dyn
          v={v}
          el="rect"
          a={{ opacity: 'bloomOp' }}
          x={100}
          y={100}
          width={100}
          height={134}
          fill="#ffffff"
        />
        <G fill="none" strokeLinecap="round" strokeLinejoin="round">
          <G stroke="#a9c2da" strokeWidth={3} opacity={0.5}>
            <Dyn
              v={v}
              el="path"
              a={{ strokeDashoffset: 'fdOff' }}
              transform="translate(102 102)"
              strokeDasharray="400 400"
              d="M0 0 L46 54"
            />
            <Dyn
              v={v}
              el="path"
              a={{ strokeDashoffset: 'tdOff' }}
              transform="translate(102 102)"
              strokeDasharray="400 400"
              d="M13 15 L3 29 M13 15 L28 9 M8 9 L2 14 M26 30 L16 44 M26 30 L42 24 M20 23 L23 18 M38 44 L32 54 M38 44 L50 41"
            />
            <Dyn
              v={v}
              el="path"
              a={{ strokeDashoffset: 'fdOff' }}
              transform="translate(198 102) scale(-1 1)"
              strokeDasharray="400 400"
              d="M0 0 L46 54"
            />
            <Dyn
              v={v}
              el="path"
              a={{ strokeDashoffset: 'tdOff' }}
              transform="translate(198 102) scale(-1 1)"
              strokeDasharray="400 400"
              d="M13 15 L3 29 M13 15 L28 9 M8 9 L2 14 M26 30 L16 44 M26 30 L42 24 M20 23 L23 18 M38 44 L32 54 M38 44 L50 41"
            />
            <Dyn
              v={v}
              el="path"
              a={{ strokeDashoffset: 'fdOff' }}
              transform="translate(102 232) scale(1 -1)"
              strokeDasharray="400 400"
              d="M0 0 L46 54"
            />
            <Dyn
              v={v}
              el="path"
              a={{ strokeDashoffset: 'tdOff' }}
              transform="translate(102 232) scale(1 -1)"
              strokeDasharray="400 400"
              d="M13 15 L3 29 M13 15 L28 9 M8 9 L2 14 M26 30 L16 44 M26 30 L42 24 M20 23 L23 18 M38 44 L32 54 M38 44 L50 41"
            />
            <Dyn
              v={v}
              el="path"
              a={{ strokeDashoffset: 'fdOff' }}
              transform="translate(198 232) scale(-1 -1)"
              strokeDasharray="400 400"
              d="M0 0 L46 54"
            />
            <Dyn
              v={v}
              el="path"
              a={{ strokeDashoffset: 'tdOff' }}
              transform="translate(198 232) scale(-1 -1)"
              strokeDasharray="400 400"
              d="M13 15 L3 29 M13 15 L28 9 M8 9 L2 14 M26 30 L16 44 M26 30 L42 24 M20 23 L23 18 M38 44 L32 54 M38 44 L50 41"
            />
          </G>
          <G stroke="#ffffff" strokeWidth={1.3}>
            <Dyn
              v={v}
              el="path"
              a={{ strokeDashoffset: 'fdOff' }}
              transform="translate(102 102)"
              strokeDasharray="400 400"
              d="M0 0 L46 54"
            />
            <Dyn
              v={v}
              el="path"
              a={{ strokeDashoffset: 'tdOff' }}
              transform="translate(102 102)"
              strokeDasharray="400 400"
              d="M13 15 L3 29 M13 15 L28 9 M8 9 L2 14 M26 30 L16 44 M26 30 L42 24 M20 23 L23 18 M38 44 L32 54 M38 44 L50 41"
            />
            <Dyn
              v={v}
              el="path"
              a={{ strokeDashoffset: 'fdOff' }}
              transform="translate(198 102) scale(-1 1)"
              strokeDasharray="400 400"
              d="M0 0 L46 54"
            />
            <Dyn
              v={v}
              el="path"
              a={{ strokeDashoffset: 'tdOff' }}
              transform="translate(198 102) scale(-1 1)"
              strokeDasharray="400 400"
              d="M13 15 L3 29 M13 15 L28 9 M8 9 L2 14 M26 30 L16 44 M26 30 L42 24 M20 23 L23 18 M38 44 L32 54 M38 44 L50 41"
            />
            <Dyn
              v={v}
              el="path"
              a={{ strokeDashoffset: 'fdOff' }}
              transform="translate(102 232) scale(1 -1)"
              strokeDasharray="400 400"
              d="M0 0 L46 54"
            />
            <Dyn
              v={v}
              el="path"
              a={{ strokeDashoffset: 'tdOff' }}
              transform="translate(102 232) scale(1 -1)"
              strokeDasharray="400 400"
              d="M13 15 L3 29 M13 15 L28 9 M8 9 L2 14 M26 30 L16 44 M26 30 L42 24 M20 23 L23 18 M38 44 L32 54 M38 44 L50 41"
            />
            <Dyn
              v={v}
              el="path"
              a={{ strokeDashoffset: 'fdOff' }}
              transform="translate(198 232) scale(-1 -1)"
              strokeDasharray="400 400"
              d="M0 0 L46 54"
            />
            <Dyn
              v={v}
              el="path"
              a={{ strokeDashoffset: 'tdOff' }}
              transform="translate(198 232) scale(-1 -1)"
              strokeDasharray="400 400"
              d="M13 15 L3 29 M13 15 L28 9 M8 9 L2 14 M26 30 L16 44 M26 30 L42 24 M20 23 L23 18 M38 44 L32 54 M38 44 L50 41"
            />
          </G>
          <Dyn v={v} el="g" t="flakeT" a={{ opacity: 'flakeOp' }}>
            <G stroke="#a9c2da" strokeWidth={3} opacity={0.55}>
              <G>
                <Path d="M0 0 V-27 M0 -10 L-7 -16 M0 -10 L7 -16 M0 -19 L-5 -24 M0 -19 L5 -24" />
              </G>
              <G transform="rotate(60)">
                <Path d="M0 0 V-27 M0 -10 L-7 -16 M0 -10 L7 -16 M0 -19 L-5 -24 M0 -19 L5 -24" />
              </G>
              <G transform="rotate(120)">
                <Path d="M0 0 V-27 M0 -10 L-7 -16 M0 -10 L7 -16 M0 -19 L-5 -24 M0 -19 L5 -24" />
              </G>
              <G transform="rotate(180)">
                <Path d="M0 0 V-27 M0 -10 L-7 -16 M0 -10 L7 -16 M0 -19 L-5 -24 M0 -19 L5 -24" />
              </G>
              <G transform="rotate(240)">
                <Path d="M0 0 V-27 M0 -10 L-7 -16 M0 -10 L7 -16 M0 -19 L-5 -24 M0 -19 L5 -24" />
              </G>
              <G transform="rotate(300)">
                <Path d="M0 0 V-27 M0 -10 L-7 -16 M0 -10 L7 -16 M0 -19 L-5 -24 M0 -19 L5 -24" />
              </G>
            </G>
            <G stroke="#ffffff" strokeWidth={1.4}>
              <G>
                <Path d="M0 0 V-27 M0 -10 L-7 -16 M0 -10 L7 -16 M0 -19 L-5 -24 M0 -19 L5 -24" />
              </G>
              <G transform="rotate(60)">
                <Path d="M0 0 V-27 M0 -10 L-7 -16 M0 -10 L7 -16 M0 -19 L-5 -24 M0 -19 L5 -24" />
              </G>
              <G transform="rotate(120)">
                <Path d="M0 0 V-27 M0 -10 L-7 -16 M0 -10 L7 -16 M0 -19 L-5 -24 M0 -19 L5 -24" />
              </G>
              <G transform="rotate(180)">
                <Path d="M0 0 V-27 M0 -10 L-7 -16 M0 -10 L7 -16 M0 -19 L-5 -24 M0 -19 L5 -24" />
              </G>
              <G transform="rotate(240)">
                <Path d="M0 0 V-27 M0 -10 L-7 -16 M0 -10 L7 -16 M0 -19 L-5 -24 M0 -19 L5 -24" />
              </G>
              <G transform="rotate(300)">
                <Path d="M0 0 V-27 M0 -10 L-7 -16 M0 -10 L7 -16 M0 -19 L-5 -24 M0 -19 L5 -24" />
              </G>
            </G>
            <Circle r={3} fill="#ffffff" stroke="#a9c2da" strokeWidth={1} />
          </Dyn>
        </G>
      </G>
      <Rect
        x={138}
        y={242}
        width={24}
        height={16}
        rx={1.5}
        fill="url(#g14Lid)"
        stroke="#97a0aa"
        strokeWidth={1}
      />
      <Rect
        x={141}
        y={245}
        width={18}
        height={10}
        rx={1}
        fill="url(#g14Sapph)"
        stroke="#172f6e"
        strokeWidth={0.6}
      />
      <Path
        d="M141 245 L145 248 H155 L159 245 M141 255 L145 252 H155 L159 255 M145 248 V252 M155 248 V252"
        fill="none"
        stroke="#9fb8ee"
        strokeWidth={0.5}
      />
      <Dyn v={v} el="g" t="glintT">
        <Path d="M0 -8 L1.6 -1.6 L8 0 L1.6 1.6 L0 8 L-1.6 1.6 L-8 0 L-1.6 -1.6 Z" fill="#ffffff" />
      </Dyn>
      <Rect x={76} y={140} width={8} height={12} rx={1} fill="#97a0aa" />
      <Rect x={76} y={176} width={8} height={12} rx={1} fill="#97a0aa" />
      <Clasp clasp={d.clasp}>
        <Rect
          x={216}
          y={156}
          width={10}
          height={16}
          rx={1.5}
          fill="url(#g14Lid)"
          stroke="#97a0aa"
          strokeWidth={1}
        />
        <Rect x={219} y={161} width={4} height={6} fill="url(#g14Sapph)" />
      </Clasp>
    </>
  );
}

function Inner(_: DesignProps) {
  return (
    <>
      <Path d={OUTLINE} fill="url(#g14Inner)" stroke="#97a0aa" strokeWidth={1.5} />
      <Path
        d={OUTLINE}
        fill="none"
        stroke="#ffffff"
        strokeWidth={1}
        transform="translate(150 164) scale(0.9) translate(-150 -164)"
      />
      <Path
        d={OUTLINE}
        fill="none"
        stroke="#7a9be2"
        strokeWidth={2.2}
        strokeDasharray="0.1 5"
        strokeLinecap="round"
        transform="translate(150 164) scale(0.82) translate(-150 -164)"
      />
    </>
  );
}

export const GoldFrost: LocketDesign = {
  id: 'frost',
  title: 'Gold XIV · White-gold frost',
  period: 'Art Deco white gold and rock crystal, c. 1925\u201335',
  cx: 150,
  cy: 164,
  hingeX: 80,
  hingeY: 164,
  outline: OUTLINE,
  sparkles: [
    [240, 96],
    [246, 214],
    [196, 282],
    [60, 90],
    [210, 40],
  ],
  sparkleColors: ['#eef1f4', '#7a9be2', '#cdd3da', '#eef1f4', '#7a9be2'],
  edge: ['#5b636c', '#97a0aa', '#cdd3da'],
  holdHaptics: [
    { at: 0.2, kind: 'selection' },
    { at: 0.28, kind: 'selection' },
    { at: 0.36, kind: 'selection' },
    { at: 0.44, kind: 'selection' },
    { at: 0.52, kind: 'selection' },
    { at: 0.6, kind: 'selection' },
    { at: 0.7, kind: 'rigid' },
    { at: 0.91, kind: 'light' },
  ],
  tune: { crack: [0.86, 8], clasp: [0.78, 0.95], shineOp: 0.5 },
  Defs,
  Back,
  Front,
  Inner,
};
