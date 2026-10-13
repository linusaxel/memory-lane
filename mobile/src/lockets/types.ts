import type { ComponentType } from 'react';
import type { SharedValue } from 'react-native-reanimated';
import type { HoldHaptic } from './haptics.ts';

export const PHASE = { idle: 0, holding: 1, spring: 2, commit: 3, open: 4 } as const;

/** Raw state, all on the UI thread. */
export type Motion = {
  /** hold progress 0–1 (900 ms linear; springs back on early release) */
  p: SharedValue<number>;
  /** PHASE.* */
  phase: SharedValue<number>;
  /** commit beat 0–1 (420 ms "checking your spot") */
  c: SharedValue<number>;
  /** open progress 0–1 (2.3 s) */
  o: SharedValue<number>;
  /** seconds since the motion started; drives trembles and twinkles */
  t: SharedValue<number>;
  /** finger-down amount, eased 0–1 */
  press: SharedValue<number>;
};

/** Values every locket shares, derived from Motion with the design's tuning. */
export type Derived = {
  /** p, held at 1 once committed */
  pp: SharedValue<number>;
  /** first 45% of the open, 0–1 */
  oa: SharedValue<number>;
  tilt: SharedValue<number>;
  sway: SharedValue<number>;
  scale: SharedValue<number>;
  /** lid angle in degrees */
  ang: SharedValue<number>;
  /** clasp slide in px */
  clasp: SharedValue<number>;
  shineX: SharedValue<number>;
  shineOp: SharedValue<number>;
  glowOp: SharedValue<number>;
  zoom: SharedValue<number>;
  lockOp: SharedValue<number>;
  /** the place engraved inside: leaves as the dive starts */
  engrave: SharedValue<number>;
  reduceMotion: boolean;
};

export type Tune = {
  /** max hold tilt in degrees (default -10) */
  tilt?: number;
  /** worklet: replaces the tilt curve entirely (Victorian turns over) */
  tiltFn?: (p: number, pp: number, done: boolean) => number;
  /** lid strains open: [start p, degrees] (default [0.82, 8]) */
  crack?: readonly [number, number];
  /** clasp slide window in p (default [0.75, 0.95]) */
  clasp?: readonly [number, number];
  /** Oval: lid trembles in the last third of the hold */
  tremble?: boolean;
  /** worklet: extra scale multiplier (Heart beats, Monogram strike) */
  scaleFn?: (p: number, pp: number) => number;
  /** turn off the light sweep (Night) */
  noShine?: boolean;
  /** opacity of the light sweep while held (default 0.42) */
  shineOp?: number;
};

export type PlaceInfo = {
  /** e.g. "Kultorvet" — set in Fraunces italic inside the case */
  name: string;
  /** e.g. "55.68 N · 12.57 E" — set in Plex Mono under the name */
  coords: string;
};

export type DesignProps = { m: Motion; d: Derived; place: PlaceInfo };

export type LocketDesign = {
  id: string;
  title: string;
  /** period the design draws on, for your own reference */
  period: string;
  /** centre of the case in the 300×300 design box */
  cx: number;
  cy: number;
  /** x of the lid hinge (left edge of the case) */
  hingeX: number;
  /** y of the hinge axis origin if it differs from cy (Heart) */
  hingeY?: number;
  /** radius of the widest circle around (cx, cy) inside the open case, if under
   *  0.9·(cx − hingeX): the dive zooms until it covers the screen (Eye, Heart) */
  inside?: number;
  /** case outline as an SVG path; used for edge thickness, the shine clip and the inner face */
  outline: string;
  /** where the 5 sparkles pop on open ([] for none) */
  sparkles: ReadonlyArray<readonly [number, number]>;
  /** colour per sparkle (default: all gold) */
  sparkleColors?: ReadonlyArray<string>;
  /** haptics fired as hold progress crosses each `at` (on top of the shared press / commit / open haptics) */
  holdHaptics: HoldHaptic[];
  tune?: Tune;
  /** extra <Defs> content (gradients, clip paths) this design needs in every layer */
  Defs?: ComponentType;
  /** inside of the case: chain + bail, back plate, the place engraved inside, glow. Sits behind the lid. */
  Back: ComponentType<DesignProps>;
  /** colours of the three edge-thickness rings (back to front) */
  edge?: readonly [string, string, string];
  /** front of the lid, including its hold animation, hinges and clasp */
  Front: ComponentType<DesignProps>;
  /** inside of the lid, seen once it swings past 90° */
  Inner: ComponentType<DesignProps>;
  /** optional layer in front of everything (Night's rising motes) */
  Overlay?: ComponentType<DesignProps>;
};
