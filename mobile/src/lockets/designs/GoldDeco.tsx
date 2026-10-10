import React from 'react';
import { useAnimatedProps } from 'react-native-reanimated';
import { ClipPath, G, Line, Path, Polygon, Rect } from 'react-native-svg';
import { eoc, polyPath, seg } from '../math.ts';
import { ALine, Chain, Clasp, Glow, Hinges, PlaceText } from '../parts.tsx';
import { font, metal } from '../../theme.ts';
import { PHASE, type DesignProps, type LocketDesign } from '../types.ts';

// Gold III · Deco sunburst — cut-corner octagon.
// Hold: the 13 sunburst rays light up in pairs from the outside in to the centre ray, one soft tap each.
// On open the rays pulse once.

const OUTER = '102,52 198,52 230,84 230,236 198,268 102,268 70,236 70,84';
const ORDER = [0, 12, 1, 11, 2, 10, 3, 9, 4, 8, 5, 7, 6];

function Defs() {
  return (
    <ClipPath id="decoInner">
      <Polygon points="108,66 192,66 216,90 216,230 192,254 108,254 84,230 84,90" />
    </ClipPath>
  );
}

function Back({ d, place }: DesignProps) {
  return (
    <>
      <Chain top={-18} count={4} />
      <Rect
        x={141}
        y={28}
        width={18}
        height={18}
        rx={2}
        fill="none"
        stroke="url(#gLid)"
        strokeWidth={4}
        transform="rotate(45 150 37)"
      />
      <Polygon points={OUTER} fill="url(#gBack)" />
      <Polygon
        points="108,62 192,62 220,90 220,230 192,258 108,258 80,230 80,90"
        fill={metal.glow}
        stroke={metal.deep}
        strokeWidth={1.5}
      />
      <Polygon
        points="114,72 186,72 210,96 210,224 186,248 114,248 90,224 90,96"
        fill="none"
        stroke={metal.inner}
        strokeWidth={1}
      />
      <Glow cx={150} cy={160} rx={70} ry={90} op={d.glowOp} />
      <PlaceText place={place} y={156} gap={32} rule="M120 166 H180 M130 171 H170" />
    </>
  );
}

function Ray({ i, m, d }: { i: number } & DesignProps) {
  const a = ((200 + i * (140 / 12)) * Math.PI) / 180;
  const x2 = 150 + 200 * Math.cos(a);
  const y2 = 236 + 200 * Math.sin(a);
  const rank = ORDER.indexOf(i);
  const lit = useAnimatedProps(() => {
    const ph = m.phase.value;
    const done = ph === PHASE.commit || ph === PHASE.open;
    const g = done ? 1 : seg(m.p.value, rank * 0.06, rank * 0.06 + 0.08);
    const pulse =
      ph === PHASE.open
        ? Math.sin(Math.PI * seg(d.oa.value, 0.05 + rank * 0.02, 0.35 + rank * 0.02))
        : 0;
    return { opacity: seg(g, 0.3, 0.7), strokeWidth: 1 + 1.6 * eoc(g) + 1.5 * pulse };
  });
  return (
    <>
      <Line
        x1={150}
        y1={236}
        x2={x2}
        y2={y2}
        stroke={metal.deep}
        strokeWidth={1}
        strokeLinecap="round"
      />
      <ALine
        animatedProps={lit}
        x1={150}
        y1={236}
        x2={x2}
        y2={y2}
        stroke={metal.hi}
        strokeLinecap="round"
      />
    </>
  );
}

function Front(props: DesignProps) {
  return (
    <>
      <Polygon points={OUTER} fill="url(#gLid)" stroke={metal.deep} strokeWidth={1.5} />
      <Polygon
        points="105,59 195,59 223,87 223,233 195,261 105,261 77,233 77,87"
        fill="none"
        stroke={metal.hi}
        strokeWidth={1.5}
      />
      <Polygon
        points="108,66 192,66 216,90 216,230 192,254 108,254 84,230 84,90"
        fill="none"
        stroke={metal.deep}
        strokeWidth={1}
      />
      <G clipPath="url(#decoInner)">
        {Array.from({ length: 13 }, (_, i) => (
          <Ray key={i} i={i} {...props} />
        ))}
        <Path d="M84 240 H216 M84 246 H216" stroke={metal.deep} strokeWidth={1} />
      </G>
      <Path
        d="M118 236 A32 32 0 0 1 182 236 Z"
        fill="url(#gLid)"
        stroke={metal.deep}
        strokeWidth={1.2}
      />
      <Path d="M128 236 A22 22 0 0 1 172 236" fill="none" stroke={metal.hi} strokeWidth={1} />
      <Path d="M138 236 A12 12 0 0 1 162 236" fill="none" stroke={metal.deep} strokeWidth={1} />
      <Hinges x={66} y1={128} y2={180} />
      <Clasp clasp={props.d.clasp}>
        <Polygon
          points="228,152 238,152 242,160 238,168 228,168"
          fill="url(#gLid)"
          stroke={metal.deep}
          strokeWidth={1}
        />
      </Clasp>
    </>
  );
}

function Inner(_: DesignProps) {
  return (
    <>
      <Polygon points={OUTER} fill="url(#gInner)" stroke={metal.deep} strokeWidth={1.5} />
      <Polygon
        points="108,62 192,62 220,90 220,230 192,258 108,258 80,230 80,90"
        fill="none"
        stroke={metal.hi}
        strokeWidth={1}
      />
    </>
  );
}

export const GoldDeco: LocketDesign = {
  id: 'deco',
  title: 'Gold III · Deco sunburst',
  period: 'Art Deco, c. 1925–1935',
  cx: 150,
  cy: 160,
  hingeX: 70,
  outline: polyPath([
    [102, 52],
    [198, 52],
    [230, 84],
    [230, 236],
    [198, 268],
    [102, 268],
    [70, 236],
    [70, 84],
  ]),
  sparkles: [
    [246, 96],
    [252, 210],
    [200, 286],
    [68, 62],
    [214, 36],
  ],
  // one soft tap as each ray lights (13 in all)
  holdHaptics: ORDER.map((_, rank) => ({ at: rank * 0.06 + 0.05, kind: 'soft' as const })),
  Defs,
  Back,
  Front,
  Inner,
};
