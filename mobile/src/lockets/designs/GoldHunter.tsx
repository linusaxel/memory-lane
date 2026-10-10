import React from 'react';
import { useAnimatedProps } from 'react-native-reanimated';
import { Circle, G, Path, Rect, Text as SvgText } from 'react-native-svg';
import { circlePath, eob, mRotate, mTranslate, seg } from '../math.ts';
import { AG, Chain, Glow, Hinges, PlaceText, matrixProps } from '../parts.tsx';
import { font, metal } from '../../theme.ts';
import type { DesignProps, LocketDesign } from '../types.ts';

// Gold II · Hunter compass — round hunter-case watch.
// Hold: the compass rose swings, hunts and settles pointing at the memory (damped spring);
// then the crown presses home.

function Back({ d, place }: DesignProps) {
  const crown = useAnimatedProps(() =>
    matrixProps(mTranslate(0, 6 * eob(seg(d.pp.value, 0.7, 0.95), 1.8))),
  );
  return (
    <>
      <Chain top={-30} count={5} ringY={30} />
      <Circle cx={150} cy={170} r={100} fill="url(#gBack)" />
      <Circle cx={150} cy={170} r={90} fill={metal.glow} stroke={metal.deep} strokeWidth={1.5} />
      <Circle
        cx={150}
        cy={170}
        r={80}
        fill="none"
        stroke={metal.ink}
        strokeWidth={6}
        strokeDasharray="0.8 7.58"
        opacity={0.6}
      />
      <Circle cx={150} cy={170} r={70} fill="none" stroke={metal.inner} strokeWidth={1} />
      <Glow cx={150} cy={170} rx={80} ry={80} op={d.glowOp} />
      <PlaceText place={place} y={166} />
      <Path d="M150 112 L154 124 L150 121 L146 124 Z" fill={metal.red} />
      <AG animatedProps={crown}>
        <Rect x={144} y={56} width={12} height={16} fill="url(#gBack)" />
        <Rect
          x={135}
          y={40}
          width={30}
          height={18}
          rx={4}
          fill="url(#gLid)"
          stroke={metal.deep}
          strokeWidth={1.2}
        />
        <Path
          d="M141 42 V56 M146 42 V56 M151 42 V56 M156 42 V56 M161 42 V56"
          stroke={metal.deep}
          strokeWidth={1}
        />
      </AG>
    </>
  );
}

function Front({ d }: DesignProps) {
  const rose = useAnimatedProps(() => {
    const x = seg(d.pp.value, 0, 0.85);
    const a = x > 0 ? 38 * (1 - Math.exp(-4 * x) * Math.cos(11 * x)) : 0;
    return matrixProps(mRotate(a, 150, 170));
  });
  return (
    <>
      <Circle cx={150} cy={170} r={100} fill="url(#gLid)" stroke={metal.deep} strokeWidth={1.5} />
      <Circle cx={150} cy={170} r={92} fill="none" stroke={metal.hi} strokeWidth={1.5} />
      <Circle cx={150} cy={170} r={88} fill="none" stroke={metal.deep} strokeWidth={0.8} />
      <Circle cx={150} cy={170} r={70} fill="none" stroke={metal.deep} strokeWidth={0.8} />
      <Circle
        cx={150}
        cy={170}
        r={66}
        fill="none"
        stroke={metal.deep}
        strokeWidth={3}
        strokeDasharray="0.6 6.31"
        opacity={0.7}
      />
      <AG animatedProps={rose}>
        <Path
          d="M150 108 L157 163 L150 170 L143 163 Z M150 232 L143 177 L150 170 L157 177 Z M88 170 L143 163 L150 170 L143 177 Z M212 170 L157 177 L150 170 L157 163 Z"
          fill={metal.hi}
          stroke={metal.deep}
          strokeWidth={1}
        />
        <Path
          d="M150 108 L150 170 L157 163 Z M150 232 L150 170 L143 177 Z M88 170 L150 170 L143 163 Z M212 170 L150 170 L157 177 Z"
          fill={metal.rim}
        />
        {[45, 135, 225, 315].map((r) => (
          <Path
            key={r}
            d="M150 130 L154 166 L150 170 L146 166 Z"
            fill="none"
            stroke={metal.deep}
            strokeWidth={0.8}
            transform={`rotate(${r} 150 170)`}
          />
        ))}
        <Circle cx={150} cy={170} r={5} fill="url(#gLid)" stroke={metal.deep} strokeWidth={1} />
        <SvgText
          x={150}
          y={100}
          textAnchor="middle"
          fontFamily={font.title.fontFamily}
          fontSize={11}
          fill={metal.north}
        >
          N
        </SvgText>
      </AG>
      <Hinges x={46} y1={150} y2={178} />
    </>
  );
}

function Inner(_: DesignProps) {
  return (
    <G>
      <Circle cx={150} cy={170} r={100} fill="url(#gInner)" stroke={metal.deep} strokeWidth={1.5} />
      <Circle cx={150} cy={170} r={90} fill="none" stroke={metal.hi} strokeWidth={1} />
      <Circle cx={150} cy={170} r={80} fill="none" stroke={metal.rim} strokeWidth={0.8} />
    </G>
  );
}

export const GoldHunter: LocketDesign = {
  id: 'hunter',
  title: 'Gold II · Hunter compass',
  period: 'Victorian hunter-case watch, c. 1880–1900',
  cx: 150,
  cy: 170,
  hingeX: 50,
  outline: circlePath(150, 170, 100),
  sparkles: [
    [256, 120],
    [258, 220],
    [204, 290],
    [70, 92],
    [226, 64],
  ],
  holdHaptics: [
    { at: 0.12, kind: 'soft' },
    { at: 0.3, kind: 'soft' },
    { at: 0.5, kind: 'selection' },
    { at: 0.88, kind: 'rigid' },
  ],
  Back,
  Front,
  Inner,
};
