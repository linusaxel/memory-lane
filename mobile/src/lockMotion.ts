// Small worklet-safe helpers shared by the locket unlock animation.
// Every function runs on the UI thread (Reanimated worklets).

export type Tf = Array<Record<string, number | string>>;

export const clamp = (x: number, a: number, b: number) => {
  'worklet';
  return Math.max(a, Math.min(b, x));
};

/** 0→1 as x goes from a to b, clamped. */
export const seg = (x: number, a: number, b: number) => {
  'worklet';
  return clamp((x - a) / (b - a), 0, 1);
};

export const easeOutCubic = (x: number) => {
  'worklet';
  return 1 - Math.pow(1 - x, 3);
};

export const easeInCubic = (x: number) => {
  'worklet';
  return x * x * x;
};

export const easeInOutCubic = (x: number) => {
  'worklet';
  return x < 0.5 ? 4 * x * x * x : 1 - Math.pow(-2 * x + 2, 3) / 2;
};

/** Overshoots past 1 then settles — `s` sets how far. */
export const easeOutBack = (x: number, s = 1.70158) => {
  'worklet';
  const k = s + 1;
  return 1 + k * Math.pow(x - 1, 3) + s * Math.pow(x - 1, 2);
};

/**
 * React Native rotates and scales a view around its own centre (cx, cy).
 * `about` wraps transforms so they pivot around any point (px, py) of that view instead,
 * the same as CSS transform-origin. All coordinates are in the 300×300 design box.
 */
export const about = (px: number, py: number, cx: number, cy: number, inner: Tf): Tf => {
  'worklet';
  return [
    { translateX: px - cx },
    { translateY: py - cy },
    ...inner,
    { translateX: cx - px },
    { translateY: cy - py },
  ];
};
