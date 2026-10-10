import React, { createContext, useContext } from 'react';
import Animated, { useAnimatedProps, type SharedValue } from 'react-native-reanimated';
import {
  Circle,
  ClipPath,
  Ellipse,
  G,
  Line,
  LinearGradient,
  Path,
  RadialGradient,
  Rect,
  Stop,
  Text as SvgText,
} from 'react-native-svg';
import { mRotate, mTranslate, type M6 } from './math.ts';
import { font, metal } from '../theme.ts';
import type { PlaceInfo } from './types.ts';

// Animated SVG primitives. Animate native props only: opacity, d, cx/cy/r, x/y, x2/y2,
// strokeWidth, strokeDashoffset and matrix (for transforms – see math.ts).
export const AG = Animated.createAnimatedComponent(G);
export const APath = Animated.createAnimatedComponent(Path);
export const ACircle = Animated.createAnimatedComponent(Circle);
export const AEllipse = Animated.createAnimatedComponent(Ellipse);
export const ARect = Animated.createAnimatedComponent(Rect);
export const ALine = Animated.createAnimatedComponent(Line);

/** animatedProps carrying a native matrix. Cast is needed because `matrix` isn't in the public prop types. */
export const matrixProps = (m: M6) => {
  'worklet';
  return { matrix: m } as unknown as Record<string, never>;
};

/** The five gold gradients every locket uses. Render inside <Defs>. */
export function GoldGradients() {
  return (
    <>
      <LinearGradient id="gLid" x1="0" y1="0" x2="1" y2="1">
        <Stop offset="0" stopColor={metal.hi} />
        <Stop offset="0.3" stopColor={metal.light} />
        <Stop offset="0.65" stopColor={metal.mid} />
        <Stop offset="1" stopColor={metal.deep} />
      </LinearGradient>
      <LinearGradient id="gBack" x1="1" y1="0" x2="0" y2="1">
        <Stop offset="0" stopColor={metal.mid} />
        <Stop offset="1" stopColor={metal.dark} />
      </LinearGradient>
      <LinearGradient id="gInner" x1="0" y1="0" x2="1" y2="1">
        <Stop offset="0" stopColor={metal.hi} />
        <Stop offset="0.5" stopColor={metal.inner} />
        <Stop offset="1" stopColor={metal.rim} />
      </LinearGradient>
      <RadialGradient id="gGlow" cx="50%" cy="50%" r="50%">
        <Stop offset="0" stopColor={metal.glow} stopOpacity={1} />
        <Stop offset="1" stopColor={metal.glow} stopOpacity={0} />
      </RadialGradient>
    </>
  );
}

/** Outline clip used by the light sweep. Rendered by the shell into the lid layer. */
export function OutlineClip({ id, d }: { id: string; d: string }) {
  return (
    <ClipPath id={id}>
      <Path d={d} />
    </ClipPath>
  );
}

/** Chain links running down to a bail ring at (150, ringY). `top` is the first link's y. */
export function Chain({
  top,
  count,
  ringY,
  ringR = 9,
  knobY,
}: {
  top: number;
  count: number;
  ringY?: number;
  ringR?: number;
  knobY?: number;
}) {
  const links = [];
  for (let i = 0; i < count; i++) {
    const y = top + i * 12;
    links.push(
      i % 2 ? (
        <Ellipse key={i} cx={150} cy={y} rx={3} ry={6} stroke={metal.deep} />
      ) : (
        <Ellipse key={i} cx={150} cy={y} rx={4} ry={7} />
      ),
    );
  }
  return (
    <>
      <G fill="none" stroke={metal.rim} strokeWidth={2.5}>
        {links}
      </G>
      {ringY != null && (
        <Circle cx={150} cy={ringY} r={ringR} fill="none" stroke="url(#gLid)" strokeWidth={4} />
      )}
      {knobY != null && (
        <Circle cx={150} cy={knobY} r={5} fill="url(#gLid)" stroke={metal.deep} strokeWidth={1} />
      )}
    </>
  );
}

/** Two hinge knuckles on the left edge of the lid. */
export function Hinges({
  x,
  y1,
  y2,
  color = metal.deep,
}: {
  x: number;
  y1: number;
  y2: number;
  color?: string;
}) {
  return (
    <>
      <Rect x={x} y={y1} width={8} height={12} rx={2} fill={color} />
      <Rect x={x} y={y2} width={8} height={12} rx={2} fill={color} />
    </>
  );
}

/** Wraps a clasp drawing; slides it right by d.clasp px as the hold finishes. */
export function Clasp({
  clasp,
  children,
}: {
  clasp: SharedValue<number>;
  children: React.ReactNode;
}) {
  const props = useAnimatedProps(() => matrixProps(mTranslate(clasp.value, 0)));
  return <AG animatedProps={props}>{children}</AG>;
}

/** The light sweep across the lid, clipped to the case outline. */
export function Shine({
  clipId,
  cx,
  cy,
  x,
  op,
}: {
  clipId: string;
  cx: number;
  cy: number;
  x: SharedValue<number>;
  op: SharedValue<number>;
}) {
  const props = useAnimatedProps(() => ({ x: x.value, opacity: op.value }));
  return (
    <G clipPath={`url(#${clipId})`}>
      <G transform={`rotate(20 ${cx} ${cy})`}>
        <ARect animatedProps={props} y={cy - 130} width={34} height={260} fill={metal.glow} />
      </G>
    </G>
  );
}

/** The warm glow inside the case as the lid opens. */
export function Glow({
  cx,
  cy,
  rx,
  ry,
  op,
  fill = 'url(#gGlow)',
}: {
  cx: number;
  cy: number;
  rx: number;
  ry: number;
  op: SharedValue<number>;
  fill?: string;
}) {
  const props = useAnimatedProps(() => ({ opacity: op.value }));
  return <AEllipse animatedProps={props} cx={cx} cy={cy} rx={rx} ry={ry} fill={fill} />;
}

/** The engraving's opacity: it leaves as the dive starts, or the name sweeps
 *  the screen huge. Provided by LocketUnlock. */
export const EngraveOpacity = createContext<SharedValue<number> | null>(null);

/** The place name and coordinates engraved inside the case. */
export function PlaceText({
  place,
  x = 150,
  y,
  gap = 20,
  color = metal.ink,
  faded = metal.faded,
  rule,
}: {
  place: PlaceInfo;
  x?: number;
  y: number;
  gap?: number;
  color?: string;
  faded?: string;
  rule?: string;
}) {
  const engrave = useContext(EngraveOpacity);
  const props = useAnimatedProps(() => ({ opacity: engrave ? engrave.value : 1 }));
  // A long name engraves smaller rather than running off the case.
  const nameSize = Math.min(20, 240 / Math.max(place.name.length, 1));
  return (
    <AG animatedProps={props}>
      <SvgText
        x={x}
        y={y}
        textAnchor="middle"
        fontFamily={font.title.fontFamily}
        fontSize={nameSize}
        fill={color}
      >
        {place.name}
      </SvgText>
      {rule ? <Path d={rule} stroke={metal.rim} strokeWidth={1} fill="none" /> : null}
      <SvgText
        x={x}
        y={y + gap}
        textAnchor="middle"
        fontFamily={font.uiBold.fontFamily}
        fontWeight="600"
        fontSize={8}
        letterSpacing={1.2}
        fill={faded}
      >
        {place.coords}
      </SvgText>
    </AG>
  );
}

/** A small four-point gold sparkle at the origin. */
export const SPARKLE = 'M0 -9 L2 -2 L9 0 L2 2 L0 9 L-2 2 L-9 0 L-2 -2 Z';

/** Static helper for rotating a repeated element. */
export const rot = (deg: number, cx: number, cy: number) => `rotate(${deg} ${cx} ${cy})`;

export { mRotate, Line };
