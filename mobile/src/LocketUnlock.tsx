/**
 * The hold that opens a memory, drawn as the memory's own locket (lockets.ts).
 *
 * Hold → a gold key slides into the keyhole and turns → the ornament swings and
 * settles → the bail presses home → we ask the server → the lid swings open on
 * its hinge, sparkles pop, the inside glows → the camera dives into the locket.
 * The motion is the same for every locket; only the art differs (ART below).
 *
 * The rules (mobile/UI.md, "The unlock control"):
 *  - The hold never claims an unlock: it ends in a "checking" beat and opens
 *    only if `requestUnlock` resolves true. A refusal springs back.
 *  - Haptics: Light on press, Rigid detents, Medium at commit, Success on open,
 *    and never on an early release.
 *  - A plain accessibility activation (VoiceOver's double-tap) opens it without
 *    holding.
 *  - Reduce Motion: no tilt, sway, sparkles or zoom; it cross-fades instead.
 *
 * The parent must not clip this view: the dive scales it past its bounds.
 */
import { memo, useCallback, type ReactNode } from 'react';
import {
  Pressable,
  StyleSheet,
  View,
  useColorScheme,
  type AccessibilityActionEvent,
  type ViewStyle,
} from 'react-native';
import Animated, {
  cancelAnimation,
  Easing,
  runOnJS,
  useAnimatedProps,
  useAnimatedReaction,
  useAnimatedStyle,
  useDerivedValue,
  useFrameCallback,
  useReducedMotion,
  useSharedValue,
  withSpring,
  withTiming,
  type SharedValue,
} from 'react-native-reanimated';
import Svg, {
  Circle,
  ClipPath,
  Defs,
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
import * as Haptics from 'expo-haptics';

import {
  about,
  clamp,
  easeInCubic as eic,
  easeInOutCubic as eio,
  easeOutBack as eob,
  easeOutCubic as eoc,
  seg,
  type Tf,
} from './lockMotion.ts';
import { locketOf, type LocketId } from './lockets.ts';
import { font, metal, solid } from './theme.ts';

const AnimatedCircle = Animated.createAnimatedComponent(Circle);

// ─── constants ────────────────────────────────────────────────────────────────
const BOX = 300; // design box; everything below is in these units
const C = 150; // centre of the box
const CY = 170; // centre of the locket
const RING_LEN = 879.6; // 2π × 140

const HOLD_MS = 900;
const CHECK_MIN_MS = 420;
const OPEN_MS = 2300;

// phases as numbers so worklets can read them cheaply
const IDLE = 0;
const HOLDING = 1;
const RELEASING = 2;
const CHECKING = 3;
const OPEN = 4;

type HapticKind = 'light' | 'soft' | 'rigid' | 'medium';

// Detents during the hold: the key seats, turns, gives. Never on the way back.
const TICKS: Array<[number, HapticKind]> = [
  [0.28, 'rigid'],
  [0.72, 'rigid'],
  [0.85, 'soft'],
  [0.92, 'rigid'],
];

type Props = {
  locket: LocketId;
  /** Engraved inside the case. */
  placeName: string;
  coordinates?: string;
  /** The server re-measures. Resolve true to open, false to refuse. */
  requestUnlock: () => Promise<boolean>;
  /** Fired as the camera starts diving in: bring the memory up from here. */
  onDiveStart?: () => void;
  /** Fired when the dive has finished. */
  onOpened?: () => void;
  /** Rendered size in points (the design is 300). */
  size?: number;
  style?: ViewStyle;
};

type Motion = {
  pp: number;
  oa: number;
  rose: number;
  crown: number;
  tilt: number;
  sway: number;
  ang: number;
  shine: number;
  s: number;
  ins: number;
  turn: number;
  ka: number;
  keyOp: number;
  zoom: number;
  lockOp: number;
  glow: number;
  o: number;
};

// The rig: the whole locket hangs from its bail at (150, 0) and turns in your hand.
const rigTf = (m: Motion, cx: number, cy: number): Tf => {
  'worklet';
  return about(C, 0, cx, cy, [
    { rotateZ: `${m.sway}deg` },
    { rotateX: `${-12 * m.ka}deg` },
    { rotateY: `${30 * m.ka + m.tilt}deg` },
    { scale: m.s },
  ]);
};

// The lid swings around its hinge on the left edge.
const lidTf = (m: Motion, hingeX: number, cx: number, cy: number): Tf => {
  'worklet';
  return about(hingeX, CY, cx, cy, [{ rotateY: `${-m.ang}deg` }]);
};

export default function LocketUnlock({
  locket,
  placeName,
  coordinates,
  requestUnlock,
  onDiveStart,
  onOpened,
  size = BOX,
  style,
}: Props) {
  const reduce = useReducedMotion();
  const ring = solid(useColorScheme() === 'dark');
  const art = ART[locketOf(locket).id];
  const { hingeX, keyY, swing } = art;
  const width = 2 * (C - hingeX);

  const progress = useSharedValue(0); // the hold, 0 → 1 (springs below 0 on release)
  const openP = useSharedValue(0); // the opening + dive, 0 → 1
  const phase = useSharedValue(IDLE);
  const pressed = useSharedValue(0);
  const clock = useSharedValue(0); // seconds, only ticks while something is moving

  const frame = useFrameCallback((info) => {
    clock.value = info.timeSinceFirstFrame / 1000;
  }, false);

  const haptic = useCallback((kind: HapticKind) => {
    const map = {
      light: Haptics.ImpactFeedbackStyle.Light,
      soft: Haptics.ImpactFeedbackStyle.Soft,
      rigid: Haptics.ImpactFeedbackStyle.Rigid,
      medium: Haptics.ImpactFeedbackStyle.Medium,
    } as const;
    Haptics.impactAsync(map[kind]).catch(() => {});
  }, []);

  useAnimatedReaction(
    () => progress.value,
    (cur, prev) => {
      if (phase.value !== HOLDING || prev == null) return;
      for (let i = 0; i < TICKS.length; i++) {
        const th = TICKS[i][0];
        if (prev < th && cur >= th) runOnJS(haptic)(TICKS[i][1]);
      }
    },
  );

  // Start the dive callback once, as the zoom begins.
  useAnimatedReaction(
    () => openP.value >= 0.5,
    (now, before) => {
      if (now && !before && phase.value === OPEN && onDiveStart) runOnJS(onDiveStart)();
    },
    [onDiveStart],
  );

  const finishOpen = useCallback(() => {
    frame.setActive(false);
    onOpened?.();
  }, [frame, onOpened]);

  const stopClock = useCallback(() => frame.setActive(false), [frame]);

  const springBack = useCallback(() => {
    phase.value = RELEASING;
    pressed.value = withTiming(0, { duration: 160 });
    progress.value = withSpring(0, { stiffness: 260, damping: 20, mass: 1 }, (fin) => {
      if (fin && phase.value === RELEASING) {
        phase.value = IDLE;
        runOnJS(stopClock)();
      }
    });
  }, [phase, pressed, progress, stopClock]);

  const onHoldComplete = useCallback(async () => {
    phase.value = CHECKING;
    haptic('medium');
    const [ok] = await Promise.all([
      requestUnlock().catch(() => false),
      new Promise((r) => setTimeout(r, CHECK_MIN_MS)),
    ]);
    if (phase.value !== CHECKING) return;
    if (!ok) {
      Haptics.notificationAsync(Haptics.NotificationFeedbackType.Warning).catch(() => {});
      springBack();
      return;
    }
    phase.value = OPEN;
    Haptics.notificationAsync(Haptics.NotificationFeedbackType.Success).catch(() => {});
    pressed.value = withTiming(0, { duration: 200 });
    openP.value = withTiming(1, { duration: OPEN_MS, easing: Easing.linear }, (fin) => {
      if (fin) runOnJS(finishOpen)();
    });
  }, [finishOpen, haptic, openP, phase, pressed, requestUnlock, springBack]);

  const begin = useCallback(
    (durationMs?: number) => {
      if (phase.value >= CHECKING) return;
      phase.value = HOLDING;
      frame.setActive(true);
      haptic('light');
      pressed.value = withTiming(1, { duration: 120 });
      const from = clamp(progress.value, 0, 1);
      progress.value = from;
      progress.value = withTiming(
        1,
        { duration: durationMs ?? HOLD_MS * (1 - from), easing: Easing.linear },
        (fin) => {
          if (fin) runOnJS(onHoldComplete)();
        },
      );
    },
    [frame, haptic, onHoldComplete, phase, pressed, progress],
  );

  const end = useCallback(() => {
    if (phase.value !== HOLDING) return;
    cancelAnimation(progress);
    springBack(); // no haptic: letting go is not a failure to reward
  }, [phase, progress, springBack]);

  const onAccessibilityAction = useCallback(
    (e: AccessibilityActionEvent) => {
      if (e.nativeEvent.actionName === 'activate') begin(300);
    },
    [begin],
  );

  // ─── one place that turns state into every moving number ─────────────────
  const motion = useDerivedValue<Motion>(() => {
    const p = progress.value;
    const o = openP.value;
    const t = clock.value;
    const ph = phase.value;
    const open = ph === OPEN;
    const done = ph >= CHECKING;
    const pp = done ? 1 : clamp(p, 0, 1);
    const oa = open ? seg(o, 0, 0.45) : 0;

    // the ornament swings, hunts and settles on the memory (damped spring)
    const x = seg(pp, 0, 0.85);
    const rose = x > 0 ? swing * (1 - Math.exp(-4 * x) * Math.cos(11 * x)) : 0;
    const crown = 6 * eob(seg(pp, 0.7, 0.95), 1.8);
    const tilt = reduce ? 0 : open ? -10 * (1 - eoc(seg(oa, 0, 0.6))) : -10 * eio(pp);
    const sway = reduce || !open ? 0 : 5 * Math.sin(o * 14) * Math.pow(1 - o, 2);

    let ang = 8 * eic(seg(pp, 0.85, 1));
    if (ph === CHECKING) ang = 8 + Math.sin(t * 90) * 0.8;
    if (open) ang = 8 + 124 * eob(oa, 1.5);

    // key: slides in along its own axis, grinds to 25°, then gives and snaps to 90°
    const ins = 70 * (1 - eoc(seg(pp, 0, 0.28)));
    const tt = seg(pp, 0.32, 0.8);
    let turn = tt < 0.6 ? 25 * (tt / 0.6) : 25 + 65 * eob(seg(tt, 0.6, 1), 1.6);
    if (ph === HOLDING && pp > 0.32 && pp < 0.6) turn += Math.sin(t * 85) * 1.2;
    // the locket turns toward you to take the key, then faces you again
    const ka = open || reduce ? 0 : eio(seg(pp, 0, 0.22)) * (1 - eio(seg(pp, 0.82, 1)));
    // and leaves with the lid before it passes 90°: past that it would point into the case
    const keyOp = done ? (open ? 1 - seg(oa, 0.05, 0.18) : 1) : seg(p, 0, 0.16);

    const zt = open && !reduce ? seg(o, 0.5, 0.9) : 0;
    return {
      pp,
      oa,
      rose,
      crown,
      tilt,
      sway,
      ang,
      shine: open ? -60 + 260 * seg(oa, 0, 0.5) : -60 + 230 * eio(pp),
      s: 1 - 0.025 * pressed.value,
      ins,
      turn,
      ka,
      keyOp,
      zoom: 1 + 13 * eic(zt),
      lockOp: reduce ? (open ? 1 - seg(o, 0.5, 0.85) : 1) : 1 - seg(zt, 0.55, 0.95),
      glow: open ? eoc(seg(oa, 0.15, 0.7)) : 0,
      o: open ? o : 0,
    };
  }, [reduce, swing]);

  // ─── styles for each layer ───────────────────────────────────────────────
  const P = { perspective: 900 };

  const diveStyle = useAnimatedStyle(() => {
    const m = motion.value;
    return {
      opacity: m.lockOp,
      transform: about(C, CY, C, C, [{ scale: m.zoom }]) as never,
    };
  });
  const caseStyle = useAnimatedStyle(() => ({
    transform: [P, ...rigTf(motion.value, C, C)] as never,
  }));
  const crownStyle = useAnimatedStyle(() => ({
    transform: [P, ...rigTf(motion.value, C, C), { translateY: motion.value.crown }] as never,
  }));
  const glowStyle = useAnimatedStyle(() => ({ opacity: motion.value.glow }));
  const lidBackStyle = useAnimatedStyle(() => {
    const m = motion.value;
    return {
      transform: [
        P,
        ...rigTf(m, C, C),
        ...lidTf(m, hingeX, C, C),
        ...about(hingeX, CY, C, C, [{ rotateY: '180deg' }, { translateX: -width }]),
      ] as never,
    };
  });
  const lidFrontStyle = useAnimatedStyle(() => {
    const m = motion.value;
    return { transform: [P, ...rigTf(m, C, C), ...lidTf(m, hingeX, C, C)] as never };
  });
  const roseStyle = useAnimatedStyle(() => {
    const m = motion.value;
    return {
      transform: [
        P,
        ...rigTf(m, C, C),
        ...lidTf(m, hingeX, C, C),
        ...about(C, CY, C, C, [{ rotateZ: `${m.rose}deg` }]),
      ] as never,
    };
  });
  const shineStyle = useAnimatedStyle(() => ({
    opacity: phase.value === IDLE ? 0 : 0.45,
    transform: [{ translateX: motion.value.shine - 50 }, { rotateZ: '20deg' }],
  }));
  const keyShadowStyle = useAnimatedStyle(() => {
    const m = motion.value;
    return { opacity: 0.22 * m.keyOp * (1 - m.ins / 70) };
  });

  // Centred on C like every other layer, so its perspective matches the lid's.
  const keyStyle = useAnimatedStyle(() => {
    const m = motion.value;
    return {
      opacity: m.keyOp,
      transform: [
        P,
        ...rigTf(m, C, C),
        ...lidTf(m, hingeX, C, C),
        ...about(C, keyY, C, C, [{ rotateZ: `${m.turn}deg` }, { rotateY: '-90deg' }]),
      ] as never,
    };
  });
  const keySlideStyle = useAnimatedStyle(() => ({ transform: [{ translateX: motion.value.ins }] }));

  const sparkleLayerStyle = useAnimatedStyle(() => ({
    transform: [P, ...rigTf(motion.value, C, C)] as never,
  }));

  const ringProps = useAnimatedProps(() => ({
    strokeDashoffset: RING_LEN * (1 - motion.value.pp),
  }));

  const scale = size / BOX;

  return (
    <View style={[{ width: size, height: size }, style]}>
      <Pressable
        onPressIn={() => begin()}
        onPressOut={end}
        accessible
        accessibilityRole="button"
        accessibilityLabel="Unlock this memory"
        accessibilityHint="Press and hold to open."
        accessibilityActions={[{ name: 'activate' }]}
        onAccessibilityAction={onAccessibilityAction}
        style={{
          width: BOX,
          height: BOX,
          transform: [
            { translateX: (size - BOX) / 2 },
            { translateY: (size - BOX) / 2 },
            { scale },
          ],
        }}
      >
        <Animated.View style={[StyleSheet.absoluteFill, diveStyle]} pointerEvents="none">
          {/* progress ring: stays flat while the locket moves inside it */}
          <Svg width={BOX} height={BOX} style={StyleSheet.absoluteFill}>
            <Circle cx={C} cy={CY} r={140} stroke={ring.rule} strokeWidth={1.5} fill="none" />
            <AnimatedCircle
              cx={C}
              cy={CY}
              r={140}
              stroke={ring.seal}
              strokeWidth={2.5}
              strokeLinecap="round"
              fill="none"
              strokeDasharray={`${RING_LEN}`}
              animatedProps={ringProps}
              transform={`rotate(-90 ${C} ${CY})`}
            />
          </Svg>

          {/* case: chain stub, bail, the inside with the place */}
          <Animated.View style={[StyleSheet.absoluteFill, caseStyle]}>
            <CaseArt shape={art.shape} placeName={placeName} coordinates={coordinates} />
            <Animated.View style={[StyleSheet.absoluteFill, glowStyle]}>
              <Svg width={BOX} height={BOX}>
                <Defs>
                  <RadialGradient id="glow">
                    <Stop offset="0" stopColor={metal.glow} stopOpacity={1} />
                    <Stop offset="1" stopColor={metal.glow} stopOpacity={0} />
                  </RadialGradient>
                </Defs>
                <Circle cx={C} cy={CY} r={80} fill="url(#glow)" />
              </Svg>
            </Animated.View>
          </Animated.View>
          <Animated.View style={[StyleSheet.absoluteFill, crownStyle]}>
            <BailArt crown={art.crown} top={art.top} />
          </Animated.View>

          {/* lid: inside face, outside face, ornament, then keyhole + shine on top */}
          <Animated.View
            style={[StyleSheet.absoluteFill, styles.noBack, { zIndex: 1 }, lidBackStyle]}
          >
            <LidInsideArt shape={art.shape} />
          </Animated.View>
          <Animated.View
            style={[StyleSheet.absoluteFill, styles.noBack, { zIndex: 2 }, lidFrontStyle]}
          >
            <Svg width={BOX} height={BOX}>
              <GoldDefs />
              {art.lid(placeName)}
            </Svg>
          </Animated.View>
          {art.ornament && (
            <Animated.View
              style={[StyleSheet.absoluteFill, styles.noBack, { zIndex: 3 }, roseStyle]}
            >
              <Svg width={BOX} height={BOX}>
                <GoldDefs />
                {art.ornament}
              </Svg>
            </Animated.View>
          )}
          <Animated.View
            style={[StyleSheet.absoluteFill, styles.noBack, { zIndex: 4 }, lidFrontStyle]}
          >
            <KeyholeArt y={keyY} />
            <Animated.View style={[StyleSheet.absoluteFill, keyShadowStyle]}>
              <Svg width={BOX} height={BOX}>
                <Ellipse
                  cx={C + 16}
                  cy={keyY + 16}
                  rx={18}
                  ry={4.5}
                  fill={metal.well}
                  transform={`rotate(35 ${C + 16} ${keyY + 16})`}
                />
              </Svg>
            </Animated.View>
            {!reduce && (
              <View style={[styles.shineClip, art.clip]}>
                <Animated.View style={[styles.shine, shineStyle]} />
              </View>
            )}
            <Svg width={BOX} height={BOX} style={StyleSheet.absoluteFill}>
              <Rect x={hingeX - 4} y={150} width={8} height={12} rx={2} fill={metal.deep} />
              <Rect x={hingeX - 4} y={178} width={8} height={12} rx={2} fill={metal.deep} />
            </Svg>
          </Animated.View>

          <Animated.View style={[StyleSheet.absoluteFill, { zIndex: 5 }, keyStyle]}>
            <View style={styles.keyClip}>
              <Animated.View style={[styles.keySlide, keySlideStyle]}>
                <KeyArt y={keyY} />
              </Animated.View>
            </View>
          </Animated.View>

          {!reduce && (
            <Animated.View style={[StyleSheet.absoluteFill, { zIndex: 6 }, sparkleLayerStyle]}>
              {SPARKLES.map((s, i) => (
                <Sparkle key={i} index={i} x={s[0]} y={s[1]} motion={motion} />
              ))}
            </Animated.View>
          )}
        </Animated.View>
      </Pressable>
    </View>
  );
}

// ─── sparkles that pop around the rim as the lid opens ──────────────────────────
const SPARKLES: Array<[number, number]> = [
  [256, 120],
  [258, 220],
  [204, 290],
  [70, 92],
  [226, 64],
];

function Sparkle({
  index,
  x,
  y,
  motion,
}: {
  index: number;
  x: number;
  y: number;
  motion: Readonly<SharedValue<Motion>>;
}) {
  const st = useAnimatedStyle(() => {
    const m = motion.value;
    const k = m.o > 0 ? Math.sin(Math.PI * seg(m.oa, 0.2 + index * 0.1, 0.55 + index * 0.1)) : 0;
    return {
      opacity: k > 0 ? 1 : 0,
      transform: [{ rotateZ: `${45 * k}deg` }, { scale: k * (index % 2 ? 0.8 : 1.2) }],
    };
  });
  return (
    <Animated.View
      style={[{ position: 'absolute', left: x - 10, top: y - 10, width: 20, height: 20 }, st]}
    >
      <Svg width={20} height={20} viewBox="-10 -10 20 20">
        <Path d="M0 -9 L2 -2 L9 0 L2 2 L0 9 L-2 2 L-9 0 L-2 -2 Z" fill={metal.inner} />
      </Svg>
    </Animated.View>
  );
}

// ─── the six lockets: one outline, one lid face, and what swings ─────────────
type Art = {
  /** The case and lid outline, centred on (150, 170). */
  shape: string;
  /** The left edge, where the hinge is. */
  hingeX: number;
  /** The top edge, where the bail meets it. */
  top: number;
  keyY: number;
  /** Where the shine is clipped to, roughly the lid. */
  clip: ViewStyle;
  /** Degrees the ornament swings through as the key turns. */
  swing: number;
  /** The compass's knurled crown, or a plain ring. */
  crown: boolean;
  lid: (placeName: string) => ReactNode;
  ornament?: ReactNode;
};

const ellipse = (rx: number, ry: number) =>
  `M${C} ${CY - ry} A${rx} ${ry} 0 1 1 ${C} ${CY + ry} A${rx} ${ry} 0 1 1 ${C} ${CY - ry} Z`;
const octagon = (w: number, h: number, cut: number) => {
  const [l, r, t, b] = [C - w / 2, C + w / 2, CY - h / 2, CY + h / 2];
  return `M${l + cut} ${t} H${r - cut} L${r} ${t + cut} V${b - cut} L${r - cut} ${b} H${l + cut} L${l} ${b - cut} V${t + cut} Z`;
};
const cushion = (w: number, h: number, rad: number) => {
  const [l, r, t, b] = [C - w / 2, C + w / 2, CY - h / 2, CY + h / 2];
  return `M${l + rad} ${t} H${r - rad} Q${r} ${t} ${r} ${t + rad} V${b - rad} Q${r} ${b} ${r - rad} ${b} H${l + rad} Q${l} ${b} ${l} ${b - rad} V${t + rad} Q${l} ${t} ${l + rad} ${t} Z`;
};
/** The same outline, shrunk about the centre: the rims and borders. */
const inset = (k: number) => `translate(${C} ${CY}) scale(${k}) translate(${-C} ${-CY})`;

/** Polished gold, a bright rim and an engraved line inside it. */
function GoldLid({ shape }: { shape: string }) {
  return (
    <>
      <Path d={shape} fill="url(#lid)" stroke={metal.deep} strokeWidth={1.5} />
      <Path d={shape} fill="none" stroke={metal.hi} strokeWidth={1.5} transform={inset(0.92)} />
      <Path d={shape} fill="none" stroke={metal.deep} strokeWidth={0.8} transform={inset(0.88)} />
    </>
  );
}

const ROUND = ellipse(100, 100);
const GUILLOCHE = ellipse(84, 102);
const SUNBURST = octagon(170, 208, 30);
const MONOGRAM = cushion(156, 196, 28);
const NIGHT = ellipse(80, 102);
const GARNET = ellipse(80, 104);

const ART: Record<LocketId, Art> = {
  'hunter-compass': {
    shape: ROUND,
    hingeX: 50,
    top: 70,
    keyY: 172,
    clip: { left: 50, top: 70, width: 200, height: 200, borderRadius: 100 },
    swing: 38,
    crown: true,
    lid: () => (
      <>
        <GoldLid shape={ROUND} />
        <Circle cx={C} cy={CY} r={70} fill="none" stroke={metal.deep} strokeWidth={0.8} />
        <Circle
          cx={C}
          cy={CY}
          r={66}
          fill="none"
          stroke={metal.deep}
          strokeWidth={3}
          strokeDasharray="0.6 6.31"
          opacity={0.7}
        />
      </>
    ),
    ornament: (
      <>
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
        {[45, 135, 225, 315].map((a) => (
          <Path
            key={a}
            d="M150 130 L154 166 L150 170 L146 166 Z"
            fill="none"
            stroke={metal.deep}
            strokeWidth={0.8}
            transform={`rotate(${a} 150 170)`}
          />
        ))}
        <SvgText
          x={C}
          y={100}
          textAnchor="middle"
          fontFamily={font.display.fontFamily}
          fontSize={11}
          fontWeight="700"
          fill={metal.north}
        >
          N
        </SvgText>
      </>
    ),
  },

  'guilloche-oval': {
    shape: GUILLOCHE,
    hingeX: 66,
    top: 68,
    keyY: 172,
    clip: { left: 66, top: 68, width: 168, height: 204, borderRadius: 84 },
    swing: 24,
    crown: false,
    lid: () => <GoldLid shape={GUILLOCHE} />,
    // Engine-turned: one loop turned eighteen times about the centre.
    ornament: (
      <G fill="none" stroke={metal.deep} strokeWidth={0.6} opacity={0.8}>
        {Array.from({ length: 18 }, (_, i) => (
          <Ellipse
            key={i}
            cx={C}
            cy={CY}
            rx={50}
            ry={20}
            transform={`rotate(${i * 10} ${C} ${CY})`}
          />
        ))}
        <Ellipse cx={C} cy={CY} rx={18} ry={22} fill="url(#lid)" />
      </G>
    ),
  },

  'deco-sunburst': {
    shape: SUNBURST,
    hingeX: 65,
    top: 66,
    keyY: 172,
    clip: { left: 65, top: 66, width: 170, height: 208, borderRadius: 24 },
    swing: 0,
    crown: false,
    lid: () => (
      <>
        <GoldLid shape={SUNBURST} />
        <Defs>
          <ClipPath id="rays">
            <Path d={SUNBURST} transform={inset(0.88)} />
          </ClipPath>
        </Defs>
        <G clipPath="url(#rays)" stroke={metal.deep} strokeWidth={0.9}>
          {Array.from({ length: 15 }, (_, i) => {
            const a = Math.PI + (i + 0.5) * (Math.PI / 15);
            return (
              <Line
                key={i}
                x1={C + 36 * Math.cos(a)}
                y1={238 + 36 * Math.sin(a)}
                x2={C + 240 * Math.cos(a)}
                y2={238 + 240 * Math.sin(a)}
              />
            );
          })}
          <Line x1={60} y1={248} x2={240} y2={248} />
          <Line x1={60} y1={256} x2={240} y2={256} />
        </G>
        <Path
          d={`M${C - 32} 238 A32 32 0 0 1 ${C + 32} 238 Z`}
          fill="url(#lid)"
          stroke={metal.deep}
          strokeWidth={1}
        />
        <Path
          d={`M${C - 18} 238 A18 18 0 0 1 ${C + 18} 238`}
          fill="none"
          stroke={metal.hi}
          strokeWidth={1}
        />
      </>
    ),
  },

  'monogram-cushion': {
    shape: MONOGRAM,
    hingeX: 72,
    top: 72,
    keyY: 236,
    clip: { left: 72, top: 72, width: 156, height: 196, borderRadius: 28 },
    swing: 0,
    crown: false,
    // The place's initial in the cartouche: the locket is engraved for it.
    lid: (placeName) => (
      <>
        <GoldLid shape={MONOGRAM} />
        <Path
          d={MONOGRAM}
          fill="none"
          stroke={metal.hi}
          strokeWidth={2}
          strokeDasharray="3 3"
          transform={inset(0.84)}
        />
        <Ellipse
          cx={C}
          cy={160}
          rx={32}
          ry={42}
          fill="url(#lid)"
          stroke={metal.deep}
          strokeWidth={1}
        />
        <Ellipse cx={C} cy={160} rx={27} ry={37} fill="none" stroke={metal.hi} strokeWidth={0.8} />
        <SvgText
          x={C}
          y={172}
          textAnchor="middle"
          fontFamily={font.display.fontFamily}
          fontStyle="italic"
          fontSize={34}
          fontWeight="700"
          fill={metal.engrave}
        >
          {placeName.trim().charAt(0).toUpperCase()}
        </SvgText>
        <Path
          d="M124 110 Q137 98 150 110 Q163 98 176 110"
          fill="none"
          stroke={metal.deep}
          strokeWidth={1}
        />
        {[
          [100, 100, -40],
          [200, 100, 40],
          [100, 246, 40],
          [200, 246, -40],
        ].map(([x, y, a]) => (
          <Ellipse
            key={`${x}${y}`}
            cx={x}
            cy={y}
            rx={8}
            ry={4}
            fill="none"
            stroke={metal.deep}
            strokeWidth={0.8}
            transform={`rotate(${a} ${x} ${y})`}
          />
        ))}
      </>
    ),
  },

  'gold-line-night': {
    shape: NIGHT,
    hingeX: 70,
    top: 68,
    keyY: 172,
    clip: { left: 70, top: 68, width: 160, height: 204, borderRadius: 80 },
    swing: 0,
    crown: false,
    // Enamel, the gold only in its lines.
    lid: () => (
      <>
        <Path d={NIGHT} fill={metal.night} stroke={metal.deep} strokeWidth={2} />
        <Path d={NIGHT} fill="none" stroke={metal.rim} strokeWidth={0.8} transform={inset(0.9)} />
        <G stroke={metal.rim} strokeWidth={0.8} fill="none">
          <Line x1={108} y1={CY} x2={192} y2={CY} />
          <Line x1={C} y1={116} x2={C} y2={224} />
          <Path d="M150 128 L178 170 L150 212 L122 170 Z" fill={metal.night} />
          <Path d="M150 144 L167 170 L150 196 L133 170 Z" />
        </G>
      </>
    ),
  },

  'victorian-garnet': {
    shape: GARNET,
    hingeX: 70,
    top: 66,
    keyY: 236,
    clip: { left: 70, top: 66, width: 160, height: 208, borderRadius: 80 },
    swing: 0,
    crown: false,
    lid: () => (
      <>
        <GoldLid shape={GARNET} />
        <Path
          d={GARNET}
          fill="none"
          stroke={metal.hi}
          strokeWidth={3}
          strokeDasharray="0.1 5"
          strokeLinecap="round"
          transform={inset(0.95)}
        />
        <G fill="none" stroke={metal.deep} strokeWidth={0.9}>
          {[0, 60, 120, 180, 240, 300].map((a) => (
            <Path
              key={a}
              d="M150 158 Q158 140 150 122 Q142 140 150 158 Z"
              transform={`rotate(${a} ${C} ${CY})`}
            />
          ))}
          <Path d="M150 96 Q160 106 150 116 Q140 106 150 96 Z" />
          <Path d="M110 120 q-12 4 -6 14 q8 6 12 -4" />
          <Path d="M190 120 q12 4 6 14 q-8 6 -12 -4" />
          <Path d="M110 218 q-12 -4 -6 -14 q8 -6 12 4" />
          <Path d="M190 218 q12 -4 6 -14 q-8 -6 -12 4" />
        </G>
        <Circle cx={C} cy={CY} r={13} fill="url(#lid)" stroke={metal.deep} strokeWidth={1} />
        <Circle cx={C} cy={CY} r={10} fill={metal.garnet} />
        <Circle cx={C - 3} cy={CY - 3} r={3} fill={metal.garnetHi} opacity={0.8} />
      </>
    ),
  },
};

// ─── static artwork (Svg content never re-renders; only the views move) ────────
function GoldDefs() {
  return (
    <Defs>
      <LinearGradient id="lid" x1="0" y1="0" x2="1" y2="1">
        <Stop offset="0" stopColor={metal.hi} />
        <Stop offset="0.3" stopColor={metal.light} />
        <Stop offset="0.65" stopColor={metal.mid} />
        <Stop offset="1" stopColor={metal.deep} />
      </LinearGradient>
      <LinearGradient id="back" x1="1" y1="0" x2="0" y2="1">
        <Stop offset="0" stopColor={metal.mid} />
        <Stop offset="1" stopColor={metal.dark} />
      </LinearGradient>
      <LinearGradient id="inner" x1="0" y1="0" x2="1" y2="1">
        <Stop offset="0" stopColor={metal.hi} />
        <Stop offset="0.5" stopColor={metal.inner} />
        <Stop offset="1" stopColor={metal.rim} />
      </LinearGradient>
    </Defs>
  );
}

const CaseArt = memo(function CaseArt({
  shape,
  placeName,
  coordinates,
}: {
  shape: string;
  placeName: string;
  coordinates?: string;
}) {
  // A long name engraves smaller rather than running off the dial.
  const nameSize = Math.min(20, 240 / Math.max(placeName.length, 1));
  return (
    <Svg width={BOX} height={BOX}>
      <GoldDefs />
      {/* a short stub of chain above the bail */}
      <G fill="none" strokeWidth={2.5}>
        <Ellipse cx={C} cy={6} rx={3} ry={6} stroke={metal.deep} />
        <Ellipse cx={C} cy={18} rx={4} ry={7} stroke={metal.rim} />
      </G>
      <Path d={shape} fill="url(#back)" />
      <Path
        d={shape}
        fill={metal.glow}
        stroke={metal.deep}
        strokeWidth={1.5}
        transform={inset(0.9)}
      />
      <Path d={shape} fill="none" stroke={metal.inner} strokeWidth={1} transform={inset(0.7)} />
      <SvgText
        x={C}
        y={166}
        textAnchor="middle"
        fontFamily={font.display.fontFamily}
        fontWeight="700"
        fontSize={nameSize}
        fill={metal.dark}
      >
        {placeName}
      </SvgText>
      {coordinates ? (
        <SvgText
          x={C}
          y={186}
          textAnchor="middle"
          fontFamily={font.uiBold.fontFamily}
          fontSize={8}
          fontWeight="600"
          letterSpacing={1.2}
          fill={metal.engrave}
        >
          {coordinates}
        </SvgText>
      ) : null}
      <Path d="M150 112 L154 124 L150 121 L146 124 Z" fill={metal.north} />
    </Svg>
  );
});

/** The ring the chain runs through, and on the compass its knurled crown. */
const BailArt = memo(function BailArt({ crown, top }: { crown: boolean; top: number }) {
  return (
    <Svg width={BOX} height={BOX}>
      <GoldDefs />
      <Circle cx={C} cy={30} r={9} fill="none" stroke="url(#lid)" strokeWidth={4} />
      <Rect x={146} y={38} width={8} height={top - 36} fill="url(#back)" />
      {crown && (
        <>
          <Rect x={144} y={56} width={12} height={16} fill="url(#back)" />
          <Rect
            x={135}
            y={40}
            width={30}
            height={18}
            rx={4}
            fill="url(#lid)"
            stroke={metal.deep}
            strokeWidth={1.2}
          />
          <Path
            d="M141 42 V56 M146 42 V56 M151 42 V56 M156 42 V56 M161 42 V56"
            stroke={metal.deep}
            strokeWidth={1}
          />
        </>
      )}
    </Svg>
  );
});

const LidInsideArt = memo(function LidInsideArt({ shape }: { shape: string }) {
  return (
    <Svg width={BOX} height={BOX}>
      <GoldDefs />
      <Path d={shape} fill="url(#inner)" stroke={metal.deep} strokeWidth={1.5} />
      <Path d={shape} fill="none" stroke={metal.hi} strokeWidth={1} transform={inset(0.9)} />
      <Path d={shape} fill="none" stroke={metal.rim} strokeWidth={0.8} transform={inset(0.8)} />
    </Svg>
  );
});

const KeyholeArt = memo(function KeyholeArt({ y }: { y: number }) {
  const cy = y - 2;
  return (
    <Svg width={BOX} height={BOX} style={StyleSheet.absoluteFill}>
      <GoldDefs />
      <Ellipse
        cx={C}
        cy={cy}
        rx={10}
        ry={14}
        fill="url(#lid)"
        stroke={metal.deep}
        strokeWidth={1.2}
      />
      <Ellipse
        cx={C}
        cy={cy}
        rx={10}
        ry={14}
        fill="none"
        stroke={metal.hi}
        strokeWidth={1}
        transform="translate(-0.7 -0.9)"
      />
      <Circle cx={C} cy={cy - 3.5} r={3.4} fill={metal.well} />
      <Path
        d={`M147.8 ${cy - 1} L146.4 ${cy + 8} L153.6 ${cy + 8} L152.2 ${cy - 1} Z`}
        fill={metal.well}
      />
    </Svg>
  );
});

// The key in profile, its axis on the keyhole's y. x < 0 is the blade that goes
// into the lock. Two offset copies give it thickness; the front copy carries the
// gradient and highlight.
const KEY_BLADE =
  'M-30 -3 L1 -3 L1 3 L-8 3 L-8 8 L-13 8 L-13 3 L-18 3 L-18 7 L-23 7 L-23 3 L-30 3 Z';
const KEY_SHANK = 'M1 -6 L5 -6 L5 -2.6 L25 -2.6 L25 2.6 L5 2.6 L5 6 L1 6 Z';
const KEY_BOW =
  'M51 0 A13 13 0 1 1 25 0 A13 13 0 1 1 51 0 Z M43 0 A5 5 0 1 0 33 0 A5 5 0 1 0 43 0 Z';

const KeyArt = memo(function KeyArt({ y }: { y: number }) {
  return (
    <Svg width={190} height={BOX} viewBox={`-40 0 190 ${BOX}`}>
      <GoldDefs />
      <G transform={`translate(0 ${y + 1.4})`} fill={metal.dark}>
        <Path d={KEY_BLADE} />
        <Path d={KEY_SHANK} />
        <Path d={KEY_BOW} fillRule="evenodd" />
      </G>
      <G
        transform={`translate(0 ${y})`}
        fill="url(#lid)"
        stroke={metal.engrave}
        strokeWidth={0.8}
        strokeLinejoin="round"
      >
        <Path d={KEY_BLADE} />
        <Path d={KEY_SHANK} />
        <Path d={KEY_BOW} fillRule="evenodd" />
      </G>
      <Path
        d={`M8 ${y - 1.4} H23 M30 ${y - 8} A10 10 0 0 1 44 ${y - 8}`}
        fill="none"
        stroke={metal.hi}
        strokeWidth={1}
        strokeLinecap="round"
        opacity={0.8}
      />
    </Svg>
  );
});

const styles = StyleSheet.create({
  noBack: { backfaceVisibility: 'hidden' },
  // left edge on the keyhole; overflow hidden clips the blade as it goes in
  keyClip: {
    position: 'absolute',
    left: C,
    top: 0,
    width: BOX - C,
    height: BOX,
    overflow: 'hidden',
  },
  keySlide: { position: 'absolute', left: -40, top: 0, width: 190, height: BOX },
  shineClip: { position: 'absolute', overflow: 'hidden' },
  shine: {
    position: 'absolute',
    left: 0,
    top: -50,
    width: 34,
    height: 300,
    backgroundColor: metal.glow,
  },
});
