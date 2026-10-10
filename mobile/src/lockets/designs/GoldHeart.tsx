import React from 'react';
import { useAnimatedProps } from 'react-native-reanimated';
import { Circle, Ellipse, G, Path, RadialGradient, Rect, Stop } from 'react-native-svg';
import { bump, eoc, inset, mScale, seg } from '../math.ts';
import { ACircle, AG, Chain, Clasp, Glow, PlaceText, matrixProps } from '../parts.tsx';
import { font, metal } from '../../theme.ts';
import { PHASE, type DesignProps, type LocketDesign } from '../types.ts';

// Gold X · Sweetheart — Victorian puffed heart, c. 1880–90.
// Domed heart, bright-cut forget-me-not with a seed-pearl centre, seed-pearl border.
// Hold: the heart beats in your hand — four lub-dubs, faster each time; each sends an outline ripple
// out and blooms the pearl. Then it holds its breath.

const HEART =
  'M150 118 C150 92 124 76 102 82 C74 90 58 120 66 152 C76 196 118 230 150 266 C182 230 224 196 234 152 C242 120 226 90 198 82 C176 76 150 92 150 118 Z';
const BEATS = [0.04, 0.3, 0.52, 0.7];
const PEARL_DASH = '0.01 24.96'; // 24 pearls along the heart (local length 599.3)

function Defs() {
  return (
    <>
      <RadialGradient id="heartDome" cx="36%" cy="30%" r="85%">
        <Stop offset="0" stopColor={metal.hi} />
        <Stop offset="0.3" stopColor={metal.light} />
        <Stop offset="0.68" stopColor={metal.mid} />
        <Stop offset="1" stopColor={metal.deep} />
      </RadialGradient>
      <RadialGradient id="heartPearl" cx="36%" cy="32%" r="80%">
        <Stop offset="0" stopColor="#ffffff" />
        <Stop offset="0.6" stopColor="#f1ebe0" />
        <Stop offset="1" stopColor="#cfc4b2" />
      </RadialGradient>
    </>
  );
}

/** the beat's pulse amount at hold progress pp (lub 5.5%, dub 3.2%) */
function pulseAt(pp: number) {
  'worklet';
  let s = 0;
  for (let i = 0; i < BEATS.length; i++)
    s += 0.055 * bump(pp - BEATS[i], 0.07) + 0.032 * bump(pp - BEATS[i] - 0.09, 0.06);
  return s;
}

function Ripple({ i, m, d }: { i: number } & DesignProps) {
  const b = BEATS[i];
  const props = useAnimatedProps(() => {
    const holding = m.phase.value === PHASE.holding;
    const r = holding && d.pp.value > b ? seg(d.pp.value - b, 0, 0.24) : 0;
    const s = 1 + 0.22 * eoc(r);
    return { ...matrixProps(mScale(s, s, 150, 172)), opacity: r > 0 && r < 1 ? 0.6 * (1 - r) : 0 };
  });
  return (
    <AG animatedProps={props}>
      <Path d={HEART} fill="none" stroke={metal.rim} strokeWidth={1.4} />
    </AG>
  );
}

function Back(props: DesignProps) {
  const { d, place } = props;
  return (
    <>
      {BEATS.map((_, i) => (
        <Ripple key={i} i={i} {...props} />
      ))}
      <Chain top={8} count={5} ringY={74} />
      <Rect x={147} y={94} width={6} height={24} fill="url(#gBack)" />
      <Circle cx={150} cy={92} r={5} fill="url(#gLid)" stroke={metal.deep} strokeWidth={1} />
      <Path d={HEART} fill="url(#gBack)" />
      <Path
        d={HEART}
        fill={metal.glow}
        stroke={metal.deep}
        strokeWidth={1.6}
        transform={inset(150, 168, 0.9)}
      />
      <Path
        d={HEART}
        fill="none"
        stroke={metal.deep}
        strokeWidth={2.6}
        strokeDasharray="0.1 5"
        strokeLinecap="round"
        transform={inset(150, 168, 0.82)}
      />
      <Glow cx={150} cy={160} rx={70} ry={64} op={d.glowOp} />
      <PlaceText place={place} y={158} gap={18} />
      <Path
        d="M150 200 C150 194 144 192 141 195 C138 198 141 204 150 210 C159 204 162 198 159 195 C156 192 150 194 150 200 Z"
        fill="none"
        stroke={metal.red}
        strokeWidth={1}
      />
    </>
  );
}

const SPRAY = [
  'M136 178 C124 190 110 192 98 186',
  'M164 178 C176 190 190 192 202 186',
  'M120 188 l-3 -8 M110 190 l-4 -7 M126 184 l-1 -8',
  'M180 188 l3 -8 M190 190 l4 -7 M174 184 l1 -8',
  'M114 194 l-2 6 M186 194 l2 6',
];

function Front({ d }: DesignProps) {
  const bloom = useAnimatedProps(() => {
    let b = 0;
    for (let i = 0; i < BEATS.length; i++)
      b = Math.max(
        b,
        bump(d.pp.value - BEATS[i], 0.07),
        0.7 * bump(d.pp.value - BEATS[i] - 0.09, 0.06),
      );
    return { r: 5.5 + 7 * b, opacity: 0.55 * b };
  });
  return (
    <>
      <Path d={HEART} fill="url(#heartDome)" stroke={metal.deep} strokeWidth={1.5} />
      <Path
        d={HEART}
        fill="none"
        stroke={metal.hi}
        strokeWidth={1.4}
        transform={inset(150, 168, 0.94)}
      />
      <Path
        d={HEART}
        fill="none"
        stroke={metal.deep}
        strokeWidth={0.8}
        transform={inset(150, 168, 0.9)}
      />
      <Path
        d={HEART}
        fill="none"
        stroke="#c9bfae"
        strokeWidth={7}
        strokeLinecap="round"
        strokeDasharray={PEARL_DASH}
        transform={inset(150, 168, 0.82)}
      />
      <Path
        d={HEART}
        fill="none"
        stroke="#fbf8f1"
        strokeWidth={5.6}
        strokeLinecap="round"
        strokeDasharray={PEARL_DASH}
        transform={inset(150, 168, 0.82)}
      />
      <G fill="none" stroke={metal.deep} strokeWidth={1.1} strokeLinecap="round">
        {SPRAY.map((p, i) => (
          <Path key={i} d={p} />
        ))}
      </G>
      <G fill="url(#gLid)" stroke={metal.deep} strokeWidth={1}>
        {[0, 72, 144, 216, 288].map((r) => (
          <Ellipse key={r} cx={150} cy={150} rx={7.5} ry={10} transform={`rotate(${r} 150 162)`} />
        ))}
      </G>
      <G stroke={metal.deep} strokeWidth={0.7}>
        {[0, 72, 144, 216, 288].map((r) => (
          <Path key={r} d="M150 155 V144" transform={`rotate(${r} 150 162)`} />
        ))}
      </G>
      <Circle
        cx={150}
        cy={162}
        r={5.5}
        fill="url(#heartPearl)"
        stroke="#c9bfae"
        strokeWidth={0.8}
      />
      <ACircle animatedProps={bloom} cx={150} cy={162} fill={metal.glow} />
      <Rect x={60} y={128} width={8} height={12} rx={2} fill={metal.deep} />
      <Rect x={61} y={160} width={8} height={12} rx={2} fill={metal.deep} />
      <Clasp clasp={d.clasp}>
        <Rect
          x={228}
          y={142}
          width={10}
          height={16}
          rx={3}
          fill="url(#gLid)"
          stroke={metal.deep}
          strokeWidth={1}
        />
        <Circle cx={233} cy={150} r={2} fill="#fbf8f1" stroke="#c9bfae" strokeWidth={0.6} />
      </Clasp>
    </>
  );
}

function Inner(_: DesignProps) {
  return (
    <>
      <Path d={HEART} fill="url(#gInner)" stroke={metal.deep} strokeWidth={1.5} />
      <Path
        d={HEART}
        fill="none"
        stroke={metal.hi}
        strokeWidth={1}
        transform={inset(150, 168, 0.9)}
      />
      <Path
        d={HEART}
        fill="none"
        stroke={metal.deep}
        strokeWidth={2.2}
        strokeDasharray="0.1 5"
        strokeLinecap="round"
        transform={inset(150, 168, 0.82)}
      />
    </>
  );
}

export const GoldHeart: LocketDesign = {
  id: 'heart',
  title: 'Gold X · Sweetheart',
  period: 'Victorian puffed heart, c. 1880–90',
  cx: 150,
  cy: 172,
  hingeX: 64,
  hingeY: 150,
  outline: HEART,
  sparkles: [
    [246, 96],
    [252, 206],
    [196, 270],
    [58, 96],
    [218, 56],
  ],
  // a lub-dub pair per beat
  holdHaptics: BEATS.flatMap((b) => [
    { at: b + 0.02, kind: 'light' as const },
    { at: b + 0.11, kind: 'soft' as const },
  ]),
  tune: {
    clasp: [0.8, 0.95],
    crack: [0.84, 8],
    scaleFn: (_p, pp) => {
      'worklet';
      return 1 + pulseAt(pp);
    },
  },
  Defs,
  Back,
  Front,
  Inner,
};
