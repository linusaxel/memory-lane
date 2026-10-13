import React from 'react';
import { useAnimatedProps, useDerivedValue, type SharedValue } from 'react-native-reanimated';
import { mMul, mRotate, mScale, mTranslate, type M6 } from './math.ts';
import { ACircle, AEllipse, AG, APath, ARect } from './parts.tsx';
import type { Motion } from './types.ts';

// Bridge for the lockets generated straight from canvas boards (Gold XI–XVI).
// Each design keeps the board's own maths in a `vals(S)` worklet that returns the same values the board
// put into its {{holes}}: numbers, path strings and SVG transform strings. <Dyn> applies them as
// animated props; transform strings are parsed into the native `matrix` on the UI thread.

export type DynState = {
  p: number;
  phase: 'idle' | 'holding' | 'spring' | 'commit' | 'open';
  c: number;
  o: number;
  t: number;
  press: number;
};

export type Vals = Record<string, string | number>;

const NAMES = ['idle', 'holding', 'spring', 'commit', 'open'] as const;

/** Runs the design's `vals` worklet every frame. */
export function useVals(m: Motion, fn: (S: DynState) => Vals): SharedValue<Vals> {
  return useDerivedValue(() =>
    fn({
      p: m.p.value,
      phase: NAMES[m.phase.value] ?? 'idle',
      c: m.c.value,
      o: m.o.value,
      t: m.t.value,
      press: m.press.value,
    }),
  );
}

/** "translate(a b) rotate(d cx cy) scale(sx sy) matrix(...)" -> M6. No regex, so it is safe in worklets. */
export function parseTransform(s: string): M6 {
  'worklet';
  let m: M6 = [1, 0, 0, 1, 0, 0];
  let i = 0;
  while (i < s.length) {
    const open = s.indexOf('(', i);
    if (open < 0) break;
    const close = s.indexOf(')', open);
    const name = s.slice(i, open).trim();
    const raw = s
      .slice(open + 1, close)
      .split(',')
      .join(' ')
      .split(' ');
    const n: number[] = [];
    for (let k = 0; k < raw.length; k++) if (raw[k] !== '') n.push(Number(raw[k]));
    if (name === 'translate') m = mMul(m, mTranslate(n[0], n.length > 1 ? n[1] : 0));
    else if (name === 'rotate')
      m = mMul(m, n.length > 2 ? mRotate(n[0], n[1], n[2]) : mRotate(n[0]));
    else if (name === 'scale') m = mMul(m, mScale(n[0], n.length > 1 ? n[1] : n[0]));
    else if (name === 'matrix') m = mMul(m, [n[0], n[1], n[2], n[3], n[4], n[5]]);
    i = close + 1;
  }
  return m;
}

const COMP = { g: AG, path: APath, circle: ACircle, ellipse: AEllipse, rect: ARect } as const;

/** animated prop -> vals key, or [key, multiplier] */
type AnimMap = Record<string, string | readonly [string, number]>;

type DynProps = {
  v: SharedValue<Vals>;
  el: keyof typeof COMP;
  /** animated props */
  a?: AnimMap;
  /** vals key holding an SVG transform string (only used with el="g") */
  t?: string;
  children?: React.ReactNode;
  [prop: string]: unknown;
};

export function Dyn({ v, el, a, t, children, ...rest }: DynProps) {
  const props = useAnimatedProps(() => {
    const out: Record<string, unknown> = {};
    const vals = v.value;
    if (a) {
      for (const k in a) {
        const spec = a[k];
        const key = typeof spec === 'string' ? spec : spec[0];
        const mul = typeof spec === 'string' ? 1 : spec[1];
        const raw = vals[key];
        out[k] = k === 'd' ? String(raw) : Number(raw) * mul;
      }
    }
    if (t) out.matrix = parseTransform(String(vals[t]));
    return out as Record<string, never>;
  });
  const C = COMP[el] as unknown as React.ComponentType<Record<string, unknown>>;
  return (
    <C animatedProps={props} {...rest}>
      {children}
    </C>
  );
}
