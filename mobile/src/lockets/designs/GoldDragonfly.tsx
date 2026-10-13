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

// Gold XIII · Green-gold dragonfly — Art Nouveau, c. 1895–1905, plique-à-jour.
// Hold: the wings unfold from along the body, beat three times (flashing violet), and settle spread flat; on open they flick once.
// Generated from the canvas board GoldDragonfly.dc.html by convert.py; the maths in `vals` is the board's own.

const OUTLINE =
  'M234.0 165.0L235.0 169.7L235.4 174.4L235.1 179.1L233.9 183.7L232.2 188.0L230.2 192.1L228.5 196.2L227.2 200.5L226.4 204.9L225.8 209.6L225.2 214.4L224.1 219.0L222.4 223.2L220.0 226.8L217.0 229.9L213.9 232.6L210.8 235.3L208.1 238.3L205.7 241.7L203.6 245.6L201.4 249.6L199.0 253.3L196.1 256.4L192.8 258.5L189.1 259.9L185.4 260.7L181.6 261.4L178.1 262.4L174.8 264.1L171.5 266.3L168.2 268.7L164.8 270.9L161.2 272.3L157.5 272.8L153.7 272.2L150.0 271.0L146.4 269.6L142.8 268.4L139.3 267.9L135.6 267.9L131.9 268.3L128.0 268.5L124.2 268.1L120.6 266.8L117.4 264.5L114.4 261.4L111.6 258.1L108.8 255.0L105.9 252.4L102.6 250.4L99.2 248.6L95.6 246.8L92.2 244.6L89.3 241.6L87.0 237.9L85.2 233.6L83.7 229.2L82.4 224.8L80.7 220.7L78.6 217.0L76.2 213.5L73.6 210.0L71.2 206.2L69.4 202.0L68.3 197.5L68.0 192.7L68.1 187.9L68.4 183.1L68.5 178.5L68.0 174.0L67.1 169.6L66.0 165.0L65.0 160.3L64.6 155.6L64.9 150.9L66.1 146.3L67.8 142.0L69.8 137.9L71.5 133.8L72.8 129.5L73.6 125.1L74.2 120.4L74.8 115.6L75.9 111.0L77.6 106.8L80.0 103.2L83.0 100.1L86.1 97.4L89.2 94.7L91.9 91.7L94.3 88.3L96.4 84.4L98.6 80.4L101.0 76.7L103.9 73.6L107.2 71.5L110.9 70.1L114.6 69.3L118.4 68.6L121.9 67.6L125.2 65.9L128.5 63.7L131.8 61.3L135.2 59.1L138.8 57.7L142.5 57.2L146.3 57.8L150.0 59.0L153.6 60.4L157.2 61.6L160.7 62.1L164.4 62.1L168.1 61.7L172.0 61.5L175.8 61.9L179.4 63.2L182.6 65.5L185.6 68.6L188.4 71.9L191.2 75.0L194.1 77.6L197.4 79.6L200.8 81.4L204.4 83.2L207.8 85.4L210.7 88.4L213.0 92.1L214.8 96.4L216.3 100.8L217.6 105.2L219.3 109.3L221.4 113.0L223.8 116.5L226.4 120.0L228.8 123.8L230.6 128.0L231.7 132.5L232.0 137.3L231.9 142.1L231.6 146.9L231.5 151.5L232.0 156.0L232.9 160.4Z';

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

  // hold: the dragonfly wakes — its plique-à-jour wings unfold from along its body, beat three times
  // (the enamel shimmers violet as they catch the light), and settle spread flat. On open they flick once.
  const u = eob(seg(pp, 0.04, 0.42), 1.2);
  const beat = seg(pp, 0.42, 0.8);
  const flap = beat > 0 && beat < 1 ? 16 * Math.sin(beat * Math.PI * 6) * (1 - beat) : 0;
  const flick = open ? 10 * Math.sin(Math.PI * seg(oa, 0, 0.35)) : 0;
  const front = 72 + (-10 - 72) * u - flap - flick;
  const hind = 84 + (16 - 84) * u - 0.8 * flap - flick;
  const wing = (x: number, y: number, a: number, mirror: boolean) =>
    'translate(' +
    x +
    ' ' +
    y +
    ')' +
    (mirror ? ' scale(-1 1)' : '') +
    ' rotate(' +
    a.toFixed(2) +
    ')';
  return Object.assign(
    {},
    {
      wFR: wing(150, 120, front, false),
      wFL: wing(150, 120, front, true),
      wHR: wing(150, 131, hind, false),
      wHL: wing(150, 131, hind, true),
      irisOp: (beat > 0 ? Math.abs(Math.sin(beat * Math.PI * 6)) * (1 - 0.6 * beat) : 0).toFixed(3),
    },
  );
}

function Defs() {
  return (
    <>
      <LinearGradient id="g13Lid" x1="0%" y1="0%" x2="100%" y2="100%">
        <Stop offset={0} stopColor="#f4f4cc" />
        <Stop offset={0.3} stopColor="#dcdc9c" />
        <Stop offset={0.65} stopColor="#b6b464" />
        <Stop offset={1} stopColor="#7f7d33" />
      </LinearGradient>
      <LinearGradient id="g13Back" x1="100%" y1="0%" x2="0%" y2="100%">
        <Stop offset={0} stopColor="#b6b464" />
        <Stop offset={1} stopColor="#4f4e1c" />
      </LinearGradient>
      <LinearGradient id="g13Inner" x1="0%" y1="0%" x2="100%" y2="100%">
        <Stop offset={0} stopColor="#f4f4cc" />
        <Stop offset={0.5} stopColor="#d0cf8a" />
        <Stop offset={1} stopColor="#a6a456" />
      </LinearGradient>
      <LinearGradient id="g13WingFill" x1="0%" y1="0%" x2="100%" y2="0%">
        <Stop offset={0} stopColor="#3a9d94" stopOpacity={0.75} />
        <Stop offset={0.6} stopColor="#5fb8c4" stopOpacity={0.55} />
        <Stop offset={1} stopColor="#8a74c8" stopOpacity={0.6} />
      </LinearGradient>
      <LinearGradient id="g13Iris" x1="0%" y1="0%" x2="100%" y2="0%">
        <Stop offset={0} stopColor="#c58fd8" stopOpacity={0} />
        <Stop offset={0.5} stopColor="#e2a8e0" stopOpacity={0.8} />
        <Stop offset={1} stopColor="#8fd0e8" stopOpacity={0} />
      </LinearGradient>
      <RadialGradient id="g13Eye" cx="35%" cy="30%" r="80%">
        <Stop offset={0} stopColor="#9be3d4" />
        <Stop offset={0.5} stopColor="#2f8f87" />
        <Stop offset={1} stopColor="#144743" />
      </RadialGradient>
      <RadialGradient id="g13Glow">
        <Stop offset={0} stopColor="#fbfdf2" stopOpacity={1} />
        <Stop offset={1} stopColor="#fbfdf2" stopOpacity={0} />
      </RadialGradient>
      <ClipPath id="g13Clip">
        <Path d={OUTLINE} />
      </ClipPath>
    </>
  );
}

function Back({ d, place }: DesignProps) {
  return (
    <>
      <G fill="none" stroke="#b6b464" strokeWidth={2.5}>
        <Ellipse cx={150} cy={-30} rx={4} ry={7} />
        <Ellipse cx={150} cy={-18} rx={3} ry={6} stroke="#8c873e" />
        <Ellipse cx={150} cy={-6} rx={4} ry={7} />
        <Ellipse cx={150} cy={6} rx={3} ry={6} stroke="#8c873e" />
        <Ellipse cx={150} cy={18} rx={4} ry={7} />
      </G>
      <Circle cx={150} cy={31} r={7} fill="none" stroke="url(#g13Lid)" strokeWidth={3.6} />
      <Path
        d="M150 60 C141 53 142 44 150 39 C158 44 159 53 150 60 Z"
        fill="url(#g13Lid)"
        stroke="#7f7d33"
        strokeWidth={1}
      />
      <Path d="M150 58 V43" stroke="#7f7d33" strokeWidth={0.8} />
      <Path d={OUTLINE} fill="url(#g13Back)" />
      <Path
        d={OUTLINE}
        fill="#fdfdf6"
        stroke="#8c873e"
        strokeWidth={1.6}
        transform="translate(150 165) scale(0.9) translate(-150 -165)"
      />
      <Path
        d={OUTLINE}
        fill="none"
        stroke="#5fb8c4"
        strokeWidth={2.4}
        strokeDasharray="0.1 5"
        strokeLinecap="round"
        transform="translate(150 165) scale(0.82) translate(-150 -165)"
      />
      <Glow cx={150} cy={165} rx={70} ry={88} op={d.glowOp} fill="url(#g13Glow)" />
      <PlaceText place={place} y={160} gap={28} />
      <Path
        d="M120 170 C132 162 140 176 150 170 C160 164 168 176 180 168"
        fill="none"
        stroke="#5fb8c4"
        strokeWidth={1}
      />
    </>
  );
}

function Front({ m, d }: DesignProps) {
  const v = useVals(m, vals);
  return (
    <>
      <Path d={OUTLINE} fill="url(#g13Lid)" stroke="#7f7d33" strokeWidth={1.5} />
      <Path
        d={OUTLINE}
        fill="none"
        stroke="#f4f4cc"
        strokeWidth={1.5}
        transform="translate(150 165) scale(0.95) translate(-150 -165)"
      />
      <Path
        d={OUTLINE}
        fill="none"
        stroke="#7f7d33"
        strokeWidth={0.8}
        transform="translate(150 165) scale(0.91) translate(-150 -165)"
      />
      <G fill="none" stroke="#7f7d33" strokeWidth={1.1} strokeLinecap="round">
        <Path d="M150 262 C132 250 104 248 96 228 C90 212 104 200 116 210 C124 217 116 226 108 222" />
        <Path d="M150 262 C168 250 196 248 204 228 C210 212 196 200 184 210 C176 217 184 226 192 222" />
        <Path d="M128 246 C122 238 124 230 130 228 M172 246 C178 238 176 230 170 228" />
        <Ellipse cx={112} cy={238} rx={7} ry={4} transform="rotate(-30 112 238)" />
        <Ellipse cx={188} cy={238} rx={7} ry={4} transform="rotate(30 188 238)" />
      </G>
      <G fill="none" stroke="#c9b85a" strokeWidth={0.9} strokeLinejoin="round">
        <Dyn v={v} el="g" t="wHL">
          <Path
            fill="url(#g13WingFill)"
            d="M0 0 C18 -15 56 -18 78 -8 C84 -4 81 3 72 6 C52 11 22 8 0 0 Z"
          />
          <Dyn
            v={v}
            el="path"
            a={{ opacity: 'irisOp' }}
            fill="url(#g13Iris)"
            d="M0 0 C18 -15 56 -18 78 -8 C84 -4 81 3 72 6 C52 11 22 8 0 0 Z"
          />
          <Path d="M0 0 C25 -5 50 -7 72 -3 M14 2 C32 0 50 -1 66 3 M18 -8 L20 4 M32 -11 L34 6 M46 -12 L47 6 M60 -10 L60 5" />
        </Dyn>
        <Dyn v={v} el="g" t="wHR">
          <Path
            fill="url(#g13WingFill)"
            d="M0 0 C18 -15 56 -18 78 -8 C84 -4 81 3 72 6 C52 11 22 8 0 0 Z"
          />
          <Dyn
            v={v}
            el="path"
            a={{ opacity: 'irisOp' }}
            fill="url(#g13Iris)"
            d="M0 0 C18 -15 56 -18 78 -8 C84 -4 81 3 72 6 C52 11 22 8 0 0 Z"
          />
          <Path d="M0 0 C25 -5 50 -7 72 -3 M14 2 C32 0 50 -1 66 3 M18 -8 L20 4 M32 -11 L34 6 M46 -12 L47 6 M60 -10 L60 5" />
        </Dyn>
        <Dyn v={v} el="g" t="wFL">
          <Path
            fill="url(#g13WingFill)"
            d="M0 0 C18 -15 56 -18 78 -8 C84 -4 81 3 72 6 C52 11 22 8 0 0 Z"
          />
          <Dyn
            v={v}
            el="path"
            a={{ opacity: 'irisOp' }}
            fill="url(#g13Iris)"
            d="M0 0 C18 -15 56 -18 78 -8 C84 -4 81 3 72 6 C52 11 22 8 0 0 Z"
          />
          <Path d="M0 0 C25 -5 50 -7 72 -3 M14 2 C32 0 50 -1 66 3 M18 -8 L20 4 M32 -11 L34 6 M46 -12 L47 6 M60 -10 L60 5" />
        </Dyn>
        <Dyn v={v} el="g" t="wFR">
          <Path
            fill="url(#g13WingFill)"
            d="M0 0 C18 -15 56 -18 78 -8 C84 -4 81 3 72 6 C52 11 22 8 0 0 Z"
          />
          <Dyn
            v={v}
            el="path"
            a={{ opacity: 'irisOp' }}
            fill="url(#g13Iris)"
            d="M0 0 C18 -15 56 -18 78 -8 C84 -4 81 3 72 6 C52 11 22 8 0 0 Z"
          />
          <Path d="M0 0 C25 -5 50 -7 72 -3 M14 2 C32 0 50 -1 66 3 M18 -8 L20 4 M32 -11 L34 6 M46 -12 L47 6 M60 -10 L60 5" />
        </Dyn>
      </G>
      <G stroke="#5e5c22" strokeWidth={0.8}>
        <Ellipse cx={150} cy={145} rx={5} ry={7.5} fill="url(#g13Lid)" />
        <Ellipse cx={150} cy={158} rx={4.4} ry={6.5} fill="#2f8f87" />
        <Ellipse cx={150} cy={170} rx={4} ry={6.2} fill="url(#g13Lid)" />
        <Ellipse cx={150} cy={182} rx={3.6} ry={6} fill="#2f8f87" />
        <Ellipse cx={150} cy={193.5} rx={3.3} ry={5.8} fill="url(#g13Lid)" />
        <Ellipse cx={150} cy={204.5} rx={3} ry={5.6} fill="#2f8f87" />
        <Ellipse cx={150} cy={215} rx={2.7} ry={5.2} fill="url(#g13Lid)" />
        <Ellipse cx={150} cy={225} rx={2.4} ry={5} fill="#2f8f87" />
        <Path d="M148 230 L150 240 L152 230 Z" fill="url(#g13Lid)" />
        <Ellipse cx={150} cy={126} rx={9} ry={13} fill="url(#g13Lid)" />
        <Path
          d="M144 120 C148 124 152 124 156 120 M144 130 C148 134 152 134 156 130"
          fill="none"
          stroke="#7f7d33"
        />
        <Circle cx={150} cy={108} r={6.5} fill="url(#g13Lid)" />
        <Circle cx={145} cy={105} r={4.6} fill="url(#g13Eye)" />
        <Circle cx={155} cy={105} r={4.6} fill="url(#g13Eye)" />
      </G>
      <Circle cx={143.6} cy={103.6} r={1.2} fill="#ffffff" />
      <Circle cx={153.6} cy={103.6} r={1.2} fill="#ffffff" />
      <Rect x={61} y={142} width={8} height={12} rx={2} fill="#7f7d33" />
      <Rect x={61} y={176} width={8} height={12} rx={2} fill="#7f7d33" />
      <Clasp clasp={d.clasp}>
        <Rect
          x={231}
          y={157}
          width={10}
          height={16}
          rx={3}
          fill="url(#g13Lid)"
          stroke="#7f7d33"
          strokeWidth={1}
        />
        <Circle cx={236} cy={165} r={2} fill="#2f8f87" />
      </Clasp>
    </>
  );
}

function Inner(_: DesignProps) {
  return (
    <>
      <Path d={OUTLINE} fill="url(#g13Inner)" stroke="#7f7d33" strokeWidth={1.5} />
      <Path
        d={OUTLINE}
        fill="none"
        stroke="#f4f4cc"
        strokeWidth={1}
        transform="translate(150 165) scale(0.9) translate(-150 -165)"
      />
      <Path
        d={OUTLINE}
        fill="none"
        stroke="#5fb8c4"
        strokeWidth={2.2}
        strokeDasharray="0.1 5"
        strokeLinecap="round"
        transform="translate(150 165) scale(0.82) translate(-150 -165)"
      />
    </>
  );
}

export const GoldDragonfly: LocketDesign = {
  id: 'dragonfly',
  title: 'Gold XIII · Green-gold dragonfly',
  period: 'Art Nouveau, c. 1895\u20131905, plique-\u00e0-jour',
  cx: 150,
  cy: 165,
  hingeX: 65,
  hingeY: 165,
  outline: OUTLINE,
  sparkles: [
    [250, 100],
    [256, 214],
    [200, 284],
    [52, 96],
    [214, 44],
  ],
  sparkleColors: ['#dcdc9c', '#5fb8c4', '#8a74c8', '#dcdc9c', '#5fb8c4'],
  edge: ['#4f4e1c', '#7f7d33', '#b6b464'],
  holdHaptics: [
    { at: 0.42, kind: 'soft' },
    { at: 0.452, kind: 'light' },
    { at: 0.578, kind: 'light' },
    { at: 0.705, kind: 'light' },
  ],
  tune: { crack: [0.86, 8], clasp: [0.78, 0.95], shineOp: 0.38 },
  Defs,
  Back,
  Front,
  Inner,
};
