import { useCallback, useRef } from 'react';
import {
  useDerivedValue,
  useFrameCallback,
  useReducedMotion,
  useSharedValue,
  type SharedValue,
} from 'react-native-reanimated';
import { scheduleOnRN } from 'react-native-worklets';
import { fireHaptic } from './haptics.ts';
import { clamp, eic, eio, eob, eoc, seg } from './math.ts';
import { PHASE, type Derived, type LocketDesign, type Motion } from './types.ts';

const HOLD_S = 0.9;
const CHECK_S = 0.42;
const OPEN_S = 2.3;
const SEAL_S = 1.1;
// The seal plays the open back from here, short of the dive (it starts at 0.5).
const SEAL_FROM = 0.45;
// Past this the slide's thumb is at the end of its track; a finger rarely lands on 1.
const COMMIT = 0.98;

export type LockMotionOptions = {
  /** The server re-measures. Resolve true to open; false (or a throw) springs it shut. */
  requestUnlock: () => Promise<boolean>;
  /** The hold is done and the check begins: measure the dive. */
  onCommit?: () => void;
  /** The camera starts diving in: bring the memory up. */
  onDiveStart?: () => void;
  /** The dive has finished. */
  onOpened?: () => void;
  /** Set: play the open backwards, once, as it mounts, then call this. */
  onSealed?: () => void;
  /** The hold, when the parent shares it (SlideToUnlock's thumb rides it). */
  progress?: SharedValue<number>;
  /** How far the dive zooms: enough for the inside to cover the screen. */
  zoomMax: SharedValue<number>;
};

/**
 * The shared unlock state machine, identical for every locket:
 *   idle → holding (900 ms linear) → commit (≥420 ms, server check) → open (2.3 s)
 *   holding → spring (k260 / d20, no haptic) → idle on early release.
 * A hold, a slide (`scrub`) or VoiceOver (`open`) drive the same progress.
 * Runs on the UI thread via a frame callback that is only active while something moves.
 */
export function useLockMotion(design: LocketDesign, opts: LockMotionOptions) {
  const reduceMotion = useReducedMotion();
  const own = useSharedValue(0);
  const p = opts.progress ?? own;
  // A seal starts open, short of the dive, and plays back to shut.
  const phase = useSharedValue<number>(opts.onSealed ? PHASE.open : PHASE.idle);
  const c = useSharedValue(0);
  const o = useSharedValue(opts.onSealed ? SEAL_FROM : 0);
  const t = useSharedValue(0);
  const press = useSharedValue(0);
  const vel = useSharedValue(0);
  /** p as of the last frame, so a scrub between frames still fires its detents */
  const lastP = useSharedValue(0);
  /** hold speed in p per second; 0 while a slide holds it */
  const rate = useSharedValue(1 / HOLD_S);
  const sealing = useSharedValue(!!opts.onSealed);
  /** 0 pending, 1 ok, -1 refused */
  const verified = useSharedValue(0);
  const m: Motion = { p, phase, c, o, t, press };

  const optsRef = useRef(opts);
  optsRef.current = opts;

  const holdHaptics = design.holdHaptics.map((h) => ({ at: h.at, kind: h.kind }));

  const startVerify = useCallback(() => {
    optsRef.current.onCommit?.();
    optsRef.current.requestUnlock().then(
      (ok) => {
        verified.value = ok ? 1 : -1;
      },
      () => {
        verified.value = -1;
      },
    );
  }, [verified]);

  const diveStart = useCallback(() => optsRef.current.onDiveStart?.(), []);
  const opened = useCallback(() => optsRef.current.onOpened?.(), []);
  const sealed = useCallback(() => {
    fireHaptic('rigid');
    optsRef.current.onSealed?.();
  }, []);
  const stopRef = useRef<() => void>(() => {});
  const stop = useCallback(() => stopRef.current(), []);

  const frame = useFrameCallback((info) => {
    'worklet';
    const dt = Math.min(0.05, (info.timeSincePreviousFrame ?? 16) / 1000);
    t.value += dt;
    const ph = phase.value;
    const target = ph === PHASE.holding || ph === PHASE.commit ? 1 : 0;
    press.value += (target - press.value) * Math.min(1, dt * 18);

    if (ph === PHASE.holding) {
      const prev = lastP.value;
      const next = Math.min(1, Math.max(0, p.value) + dt * rate.value);
      p.value = next;
      lastP.value = next;
      for (let i = 0; i < holdHaptics.length; i++) {
        const h = holdHaptics[i];
        if (prev < h.at && next >= h.at) scheduleOnRN(fireHaptic, h.kind);
      }
      if (next >= 1) {
        phase.value = PHASE.commit;
        c.value = 0;
        verified.value = 0;
        scheduleOnRN(fireHaptic, 'medium');
        scheduleOnRN(startVerify);
      }
    } else if (ph === PHASE.spring) {
      vel.value += (-260 * p.value - 20 * vel.value) * dt;
      p.value += vel.value * dt;
      lastP.value = p.value;
      if (Math.abs(p.value) < 0.002 && Math.abs(vel.value) < 0.02) {
        p.value = 0;
        lastP.value = 0;
        vel.value = 0;
        phase.value = PHASE.idle;
      }
    } else if (ph === PHASE.commit) {
      c.value = Math.min(1, c.value + dt / CHECK_S);
      if (c.value >= 1 && verified.value === 1) {
        phase.value = PHASE.open;
        o.value = 0;
        scheduleOnRN(fireHaptic, 'success');
      } else if (c.value >= 1 && verified.value === -1) {
        phase.value = PHASE.spring;
        vel.value = 0;
        scheduleOnRN(fireHaptic, 'warning');
      }
    } else if (ph === PHASE.open && sealing.value) {
      if (c.value >= 1) return;
      c.value = Math.min(1, c.value + dt / SEAL_S);
      o.value = SEAL_FROM * (1 - eio(c.value));
      if (c.value >= 1) scheduleOnRN(sealed);
    } else if (ph === PHASE.open) {
      const prev = o.value;
      o.value = Math.min(1, prev + dt / OPEN_S);
      if (prev < 0.5 && o.value >= 0.5) scheduleOnRN(diveStart);
      if (prev < 1 && o.value >= 1) scheduleOnRN(opened);
    }

    const resting = phase.value === PHASE.idle && press.value < 0.01;
    const finished = phase.value === PHASE.open && (sealing.value ? c.value >= 1 : o.value >= 1);
    if (resting || finished) scheduleOnRN(stop);
  }, !!opts.onSealed);

  stopRef.current = () => frame.setActive(false);

  const begin = useCallback(
    (seconds: number) => {
      if (phase.value >= PHASE.commit) return;
      if (phase.value !== PHASE.holding) fireHaptic('light');
      vel.value = 0;
      p.value = clamp(p.value, 0, 1);
      lastP.value = p.value;
      rate.value = 1 / seconds;
      phase.value = PHASE.holding;
      frame.setActive(true);
    },
    [frame, lastP, p, phase, rate, vel],
  );

  const pressIn = useCallback(() => begin(HOLD_S), [begin]);

  const release = useCallback(() => {
    // early release: spring back, deliberately no haptic
    if (phase.value === PHASE.holding) phase.value = PHASE.spring;
  }, [phase]);

  /** Puts the hold at `to`; reaching the end commits, as a full hold does. */
  const scrub = useCallback(
    (to: number) => {
      if (phase.value >= PHASE.commit) return;
      begin(HOLD_S);
      rate.value = 0;
      p.value = to >= COMMIT ? 1 : clamp(to, 0, 1);
    },
    [begin, p, phase, rate],
  );

  /** Opens without a gesture: VoiceOver's double-tap. */
  const open = useCallback(() => begin(0.3), [begin]);

  const d = useDerived(m, design, reduceMotion, opts.zoomMax);
  return { m, d, pressIn, release, scrub, open };
}

/** The shared choreography: tilt in the hand, light sweep, clasp, lid crack → swing, sway, glow, dive. */
function useDerived(
  m: Motion,
  design: LocketDesign,
  reduceMotion: boolean,
  zoomMax: SharedValue<number>,
): Derived {
  const tune = design.tune ?? {};
  const tiltMax = tune.tilt ?? -10;
  const tiltFn = tune.tiltFn;
  const scaleFn = tune.scaleFn;
  const crackStart = tune.crack?.[0] ?? 0.82;
  const crackDeg = tune.crack?.[1] ?? 8;
  const claspA = tune.clasp?.[0] ?? 0.75;
  const claspB = tune.clasp?.[1] ?? 0.95;
  const tremble = !!tune.tremble;
  const noShine = !!tune.noShine;

  const pp = useDerivedValue(() => {
    const ph = m.phase.value;
    return ph === PHASE.commit || ph === PHASE.open ? 1 : clamp(m.p.value, 0, 1);
  });
  const oa = useDerivedValue(() => (m.phase.value === PHASE.open ? seg(m.o.value, 0, 0.45) : 0));
  // The dive: o 0.5 → 0.9 of the open. LocketUnlock's IrisGrow waits it out.
  const zt = useDerivedValue(() =>
    !reduceMotion && m.phase.value === PHASE.open ? seg(m.o.value, 0.5, 0.9) : 0,
  );

  const tilt = useDerivedValue(() => {
    if (reduceMotion) return 0;
    const ph = m.phase.value;
    const done = ph === PHASE.commit || ph === PHASE.open;
    if (tiltFn) return tiltFn(m.p.value, pp.value, done);
    if (ph === PHASE.open) return tiltMax * (1 - eoc(seg(oa.value, 0, 0.6)));
    return tiltMax * eio(pp.value);
  });

  const sway = useDerivedValue(() => {
    if (reduceMotion || m.phase.value !== PHASE.open) return 0;
    const o = m.o.value;
    return 5 * Math.sin(o * 14) * Math.pow(1 - o, 2);
  });

  const scale = useDerivedValue(() => {
    const base = 1 - 0.025 * m.press.value;
    return scaleFn ? base * scaleFn(m.p.value, pp.value) : base;
  });

  const ang = useDerivedValue(() => {
    const ph = m.phase.value;
    if (ph === PHASE.open) return crackDeg + (132 - crackDeg) * eob(oa.value, 1.5);
    if (ph === PHASE.commit) return crackDeg + Math.sin(m.t.value * 90) * 0.8;
    let a = crackDeg * eic(seg(pp.value, crackStart, 1));
    if (tremble && ph === PHASE.holding)
      a += Math.sin(m.t.value * 70) * 0.5 * seg(m.p.value, 0.65, 1);
    return a;
  });

  const clasp = useDerivedValue(() => 7 * eob(seg(pp.value, claspA, claspB), 1.6));

  const shineX = useDerivedValue(() =>
    m.phase.value === PHASE.open ? -60 + 260 * seg(oa.value, 0, 0.5) : -60 + 230 * eio(pp.value),
  );
  const shineOp = useDerivedValue<number>(() =>
    noShine || reduceMotion || m.phase.value === PHASE.idle ? 0 : 0.42,
  );
  const glowOp = useDerivedValue(() =>
    m.phase.value === PHASE.open
      ? eoc(seg(oa.value, 0.15, 0.7))
      : m.phase.value === PHASE.commit
        ? 0.12
        : 0,
  );

  const zoom = useDerivedValue(() => 1 + (zoomMax.value - 1) * eic(zt.value));
  // No fade on the dive: the inside covers the screen until IrisGrow, over it, takes over.
  const lockOp = useDerivedValue(() =>
    reduceMotion && m.phase.value === PHASE.open ? 1 - seg(m.o.value, 0.5, 0.85) : 1,
  );
  const engrave = useDerivedValue(() => 1 - seg(zt.value, 0, 0.3));

  return {
    pp,
    oa,
    tilt,
    sway,
    scale,
    ang,
    clasp,
    shineX,
    shineOp,
    glowOp,
    zoom,
    lockOp,
    engrave,
    reduceMotion,
  };
}
