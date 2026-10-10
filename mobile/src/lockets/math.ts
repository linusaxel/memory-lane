// Easing + SVG matrix helpers. Every function is a worklet so it runs on the UI thread.
// These are the exact curves used on the canvas, so timings match the designs one to one.

export function clamp(x: number, a: number, b: number): number {
  'worklet';
  return Math.max(a, Math.min(b, x));
}

/** Progress of x through [a, b], clamped to 0–1. */
export function seg(x: number, a: number, b: number): number {
  'worklet';
  return clamp((x - a) / (b - a), 0, 1);
}

/** ease-out cubic */
export function eoc(x: number): number {
  'worklet';
  return 1 - Math.pow(1 - x, 3);
}

/** ease-in cubic */
export function eic(x: number): number {
  'worklet';
  return x * x * x;
}

/** ease-in-out cubic */
export function eio(x: number): number {
  'worklet';
  return x < 0.5 ? 4 * x * x * x : 1 - Math.pow(-2 * x + 2, 3) / 2;
}

/** ease-out back with overshoot s */
export function eob(x: number, s: number): number {
  'worklet';
  const k = s + 1;
  return 1 + k * Math.pow(x - 1, 3) + s * Math.pow(x - 1, 2);
}

/** Half-sine bump: 0 outside [0, w], 1 at w/2. */
export function bump(d: number, w: number): number {
  'worklet';
  return d < 0 || d > w ? 0 : Math.sin((Math.PI * d) / w);
}

// --- 2D affine matrices for react-native-svg -------------------------------------------
// Animated SVG transforms must be sent as the native `matrix` prop ([a, b, c, d, e, f]);
// the `transform` string is only parsed on the JS side and is not updated by animatedProps.

export type M6 = [number, number, number, number, number, number];

export const IDENTITY: M6 = [1, 0, 0, 1, 0, 0];

export function mMul(m1: M6, m2: M6): M6 {
  'worklet';
  return [
    m1[0] * m2[0] + m1[2] * m2[1],
    m1[1] * m2[0] + m1[3] * m2[1],
    m1[0] * m2[2] + m1[2] * m2[3],
    m1[1] * m2[2] + m1[3] * m2[3],
    m1[0] * m2[4] + m1[2] * m2[5] + m1[4],
    m1[1] * m2[4] + m1[3] * m2[5] + m1[5],
  ];
}

export function mTranslate(x: number, y: number): M6 {
  'worklet';
  return [1, 0, 0, 1, x, y];
}

export function mRotate(deg: number, cx = 0, cy = 0): M6 {
  'worklet';
  const r = (deg * Math.PI) / 180;
  const c = Math.cos(r);
  const s = Math.sin(r);
  return [c, s, -s, c, cx - c * cx + s * cy, cy - s * cx - c * cy];
}

export function mScale(sx: number, sy: number, cx = 0, cy = 0): M6 {
  'worklet';
  return [sx, 0, 0, sy, cx - sx * cx, cy - sy * cy];
}

// --- static path builders (JS thread, used once) -----------------------------------------

export const ellipsePath = (cx: number, cy: number, rx: number, ry: number) =>
  `M${cx - rx} ${cy}A${rx} ${ry} 0 1 0 ${cx + rx} ${cy}A${rx} ${ry} 0 1 0 ${cx - rx} ${cy}Z`;

export const circlePath = (cx: number, cy: number, r: number) => ellipsePath(cx, cy, r, r);

export const polyPath = (pts: ReadonlyArray<readonly [number, number]>) =>
  'M' + pts.map((p) => `${p[0]} ${p[1]}`).join('L') + 'Z';

export const roundRectPath = (x: number, y: number, w: number, h: number, r: number) =>
  `M${x + r} ${y}H${x + w - r}A${r} ${r} 0 0 1 ${x + w} ${y + r}V${y + h - r}A${r} ${r} 0 0 1 ${x + w - r} ${y + h}` +
  `H${x + r}A${r} ${r} 0 0 1 ${x} ${y + h - r}V${y + r}A${r} ${r} 0 0 1 ${x + r} ${y}Z`;

/** Static SVG transform string that scales about (cx, cy) – for inset copies of a case outline. */
export const inset = (cx: number, cy: number, k: number) =>
  `translate(${cx} ${cy}) scale(${k}) translate(${-cx} ${-cy})`;
