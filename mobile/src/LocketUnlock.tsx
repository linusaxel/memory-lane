/**
 * The hold that opens a memory, drawn as the memory's own locket (lockets.ts).
 *
 * Hold → the locket does its own thing (the compass hunts, the rays light,
 * the garnet turns over: lockets/designs) → we ask the server → the lid
 * swings open on its hinge, sparkles pop, the inside glows → the camera dives
 * in. The state machine and the shared choreography are lockets/lockMotion.ts;
 * each design draws its case, its lid and its own hold.
 *
 * The rules (mobile/UI.md, "The unlock control"):
 *  - The hold never claims an unlock: it ends in a "checking" beat and opens
 *    only if `requestUnlock` resolves true. A refusal springs back.
 *  - Haptics: Light on press, the design's detents, Medium at commit, Success
 *    on open, and never on an early release.
 *  - A plain accessibility activation (VoiceOver's double-tap) opens it without
 *    holding.
 *  - The hold is one way to drive it; `ref` is the other: SlideToUnlock scrubs
 *    the same progress with a thumb (docs/10, "Slide to unlock").
 *  - Reduce Motion: no tilt, sway, sparkles or zoom; it cross-fades instead.
 *
 * The parent must not clip this view: the dive scales it past its bounds.
 */
import {
  useCallback,
  useEffect,
  useImperativeHandle,
  useRef,
  type ReactNode,
  type Ref,
} from 'react';
import {
  Pressable,
  StyleSheet,
  View,
  useColorScheme,
  useWindowDimensions,
  type AccessibilityActionEvent,
  type ViewStyle,
} from 'react-native';
import Animated, {
  Easing,
  runOnJS,
  useAnimatedProps,
  useAnimatedStyle,
  useDerivedValue,
  useReducedMotion,
  useSharedValue,
  withTiming,
  type SharedValue,
} from 'react-native-reanimated';
import Svg, { Defs, Path } from 'react-native-svg';

import { locketOf, type LocketId } from './lockets.ts';
import { useLockMotion } from './lockets/lockMotion.ts';
import { eio, mMul, mRotate, mScale, mTranslate, seg } from './lockets/math.ts';
import {
  AG,
  EngraveOpacity,
  GoldGradients,
  matrixProps,
  OutlineClip,
  Shine,
  SPARKLE,
} from './lockets/parts.tsx';
import { PHASE, type Derived, type LocketDesign, type Motion } from './lockets/types.ts';
import { color, metal, radius } from './theme.ts';

// Every layer is a 400×400 view whose Svg shows the 300×300 design box with
// 50 / 60 of bleed, so chains and sparkles outside the box are never clipped.
const OX = 50;
const OY = 60;
const BOX = 400;
const VIEWBOX = `${-OX} ${-OY} ${BOX} ${BOX}`;
const PERSPECTIVE = 900;

const OPEN_MS = 2300;
// The zoom runs over o 0.5 → 0.9 of the open; IrisGrow waits it out.
const DIVE_MS = 0.4 * OPEN_MS;
const SETTLE_MS = 380;

type Props = {
  locket: LocketId;
  /** Engraved inside the case. */
  placeName: string;
  coordinates?: string;
  /** The server re-measures. Resolve true to open, false to refuse. */
  requestUnlock: () => Promise<boolean>;
  /** Fired as the camera starts diving in: bring the memory up. */
  onDiveStart?: () => void;
  /** Fired when the dive has finished. */
  onOpened?: () => void;
  /** Rendered size in points (the design is 300). */
  size?: number;
  style?: ViewStyle;
  ref?: Ref<LocketDrive>;
  /** The hold, when the parent shares it (SlideToUnlock's thumb rides it). */
  progress?: SharedValue<number>;
  /** Plays the opening backwards instead of waiting for a hold: the lid shuts
   *  on a memory just filed (docs/10, "Writing is a calm page"). Called once
   *  it is shut. */
  onSealed?: () => void;
};

/** The locket driven from outside, by SlideToUnlock. */
export type LocketDrive = {
  /** Puts the hold at `p`; reaching the end commits, as a full hold does. */
  scrub: (p: number) => void;
  /** Lets go: back to closed, unless it already committed. */
  release: () => void;
  /** Opens without a gesture: VoiceOver's double-tap. */
  open: () => void;
};

export default function LocketUnlock({
  locket,
  placeName,
  coordinates,
  requestUnlock,
  onDiveStart,
  onOpened,
  size = 300,
  style,
  ref,
  progress,
  onSealed,
}: Props) {
  const design = locketOf(locket).design;
  const { cx, cy, hingeX } = design;
  const hingeY = design.hingeY ?? cy;
  const k = size / 300;
  const root = useRef<View>(null);
  const window = useWindowDimensions();
  const zoomMax = useSharedValue(14);

  // The dive ends with the inside covering the whole screen, whatever the
  // locket's shape: its half-width reaches the farthest corner. IrisGrow takes
  // over from there (docs/10, "One handover for every locket").
  const measureZoom = useCallback(() => {
    root.current?.measureInWindow((x, y) => {
      const px = x + cx * k;
      const py = y + cy * k;
      const far = Math.hypot(Math.max(px, window.width - px), Math.max(py, window.height - py));
      const inside = 0.9 * (cx - hingeX) * k;
      zoomMax.value = Math.max(14, (1.1 * far) / inside);
    });
  }, [cx, cy, hingeX, k, window, zoomMax]);

  const { m, d, pressIn, release, scrub, open } = useLockMotion(design, {
    requestUnlock,
    onCommit: measureZoom,
    onDiveStart,
    onOpened,
    onSealed,
    progress,
    zoomMax,
  });
  useImperativeHandle(ref, () => ({ scrub, release, open }), [scrub, release, open]);

  const onAccessibilityAction = useCallback(
    (e: AccessibilityActionEvent) => {
      if (e.nativeEvent.actionName === 'activate') open();
    },
    [open],
  );

  const dive = useAnimatedStyle(() => ({
    opacity: d.lockOp.value,
    transform: [{ scale: d.zoom.value }],
  }));
  const rig = useAnimatedStyle(() => ({
    transform: [
      { perspective: PERSPECTIVE },
      { rotateZ: `${d.sway.value}deg` },
      { rotateY: `${d.tilt.value}deg` },
      { translateY: cy },
      { scale: d.scale.value },
      { translateY: -cy },
    ],
  }));
  const lidFront = useAnimatedStyle(() => ({
    transform: [{ perspective: PERSPECTIVE }, { rotateY: `${-d.ang.value}deg` }],
  }));
  const lidInner = useAnimatedStyle(() => ({
    transform: [
      { perspective: PERSPECTIVE },
      { rotateY: `${-d.ang.value}deg` },
      { rotateY: '180deg' },
      { translateX: -2 * (cx - hingeX) },
    ],
  }));

  const place = { name: placeName, coords: coordinates ?? '' };
  const props = { m, d, place };
  const { Back, Front, Inner, Overlay } = design;
  const edge = design.edge ?? [metal.dark, metal.deep, metal.rim];
  const hinge = { transformOrigin: [hingeX + OX, hingeY + OY, 0] };

  return (
    <View ref={root} collapsable={false} style={[{ width: size, height: size }, style]}>
      <EngraveOpacity.Provider value={d.engrave}>
        <View style={[styles.box, { transform: [{ scale: k }], transformOrigin: [0, 0, 0] }]}>
          <Animated.View
            pointerEvents="none"
            style={[styles.layer, { transformOrigin: [150 + OX, cy + OY, 0] }, dive]}
          >
            <Animated.View style={[styles.fill, { transformOrigin: [150 + OX, OY, 0] }, rig]}>
              <Layer design={design} z={-12} d={d}>
                <Back {...props} />
              </Layer>
              {edge.map((stroke, i) => (
                <Layer key={i} design={design} z={-9 + 3 * i} d={d}>
                  <Path d={design.outline} fill="none" stroke={stroke} strokeWidth={3} />
                </Layer>
              ))}
              <Plane>
                <Animated.View style={[styles.fill, styles.face, hinge, lidFront]}>
                  <LayerSvg design={design}>
                    <Front {...props} />
                    <Shine clipId="lkOutline" cx={cx} cy={cy} x={d.shineX} op={d.shineOp} />
                  </LayerSvg>
                </Animated.View>
              </Plane>
              <Plane>
                <Animated.View style={[styles.fill, styles.face, hinge, lidInner]}>
                  <LayerSvg design={design}>
                    <Inner {...props} />
                  </LayerSvg>
                </Animated.View>
              </Plane>
              <Layer design={design} z={6} d={d}>
                {!d.reduceMotion &&
                  design.sparkles.map((q, i) => (
                    <Sparkle key={i} i={i} x={q[0]} y={q[1]} m={m} d={d} />
                  ))}
                {Overlay ? <Overlay {...props} /> : null}
              </Layer>
            </Animated.View>
          </Animated.View>
        </View>
      </EngraveOpacity.Provider>

      <Pressable
        disabled={!!onSealed}
        onPressIn={pressIn}
        onPressOut={release}
        accessible
        accessibilityRole="button"
        accessibilityLabel="Unlock this memory"
        accessibilityHint="Press and hold to open."
        accessibilityActions={[{ name: 'activate' }]}
        onAccessibilityAction={onAccessibilityAction}
        style={[StyleSheet.absoluteFill, { borderRadius: size / 2 }]}
      />
    </View>
  );
}

// iOS depth-sorts 3D-transformed siblings: the lid sorted behind the case and
// half of it vanished as the locket turned. A plain parent flattens its child,
// so each moving layer gets one and the layers paint in the order written.
function Plane({ children }: { children: ReactNode }) {
  return (
    <View style={styles.fill} collapsable={false} pointerEvents="none">
      {children}
    </View>
  );
}

/** One Svg layer, shifted sideways by z·sin(tilt) to fake the case's thickness as it turns. */
function Layer({
  design,
  z,
  d,
  children,
}: {
  design: LocketDesign;
  z: number;
  d: Derived;
  children: ReactNode;
}) {
  const shift = useAnimatedStyle(() => ({
    transform: [{ translateX: z * Math.sin((d.tilt.value * Math.PI) / 180) }],
  }));
  return (
    <Plane>
      <Animated.View style={[styles.fill, shift]}>
        <LayerSvg design={design}>{children}</LayerSvg>
      </Animated.View>
    </Plane>
  );
}

function LayerSvg({ design, children }: { design: LocketDesign; children: ReactNode }) {
  const Extra = design.Defs;
  return (
    <Svg width={BOX} height={BOX} viewBox={VIEWBOX}>
      <Defs>
        <GoldGradients />
        <OutlineClip id="lkOutline" d={design.outline} />
        {Extra ? <Extra /> : null}
      </Defs>
      {children}
    </Svg>
  );
}

function Sparkle({ i, x, y, m, d }: { i: number; x: number; y: number; m: Motion; d: Derived }) {
  const props = useAnimatedProps(() => {
    const kk =
      m.phase.value === PHASE.open
        ? Math.sin(Math.PI * seg(d.oa.value, 0.2 + i * 0.1, 0.55 + i * 0.1))
        : 0;
    const s = Math.max(0.0001, kk * (i % 2 ? 0.8 : 1.2));
    return matrixProps(mMul(mMul(mTranslate(x, y), mRotate(45 * kk)), mScale(s, s)));
  });
  return (
    <AG animatedProps={props}>
      <Path d={SPARKLE} fill={metal.inner} />
    </AG>
  );
}

type IrisProps = {
  /** The open memory's card it lands on: full width, on the bottom edge. */
  height: number;
  /** Settled on the card's frame: the card can show. */
  onGrown: () => void;
};

/** The dive, handed over: the locket's zoom ends with its inside covering the
 *  screen, and from then this full-screen paper, over it, settles down into
 *  the card's frame. It matches no locket's shape, so every locket blends the
 *  same. In light the inside's glow fades to paper as it settles; in dark,
 *  where a cream screen would flash, the paper fades in over the dive itself,
 *  so the locket dives into plum-black and nothing is ever white.
 *  The parent removes it once the card is up. With Reduce Motion it draws
 *  nothing and hands over at once. */
export function IrisGrow({ height, onGrown }: IrisProps) {
  const reduce = useReducedMotion();
  const { height: screen } = useWindowDimensions();
  const dark = useColorScheme() === 'dark';
  const ms = useSharedValue(0);
  const total = DIVE_MS + SETTLE_MS;

  useEffect(() => {
    if (reduce) {
      onGrown();
      return;
    }
    ms.value = withTiming(total, { duration: total, easing: Easing.linear }, (fin) => {
      if (fin) runOnJS(onGrown)();
    });
    // Once, as it mounts: the callback is new every render.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const settle = useDerivedValue(() => eio(Math.max((ms.value - DIVE_MS) / SETTLE_MS, 0)));
  const frame = useAnimatedStyle(() => {
    const b = settle.value;
    return {
      opacity: dark ? Math.min(ms.value / DIVE_MS, 1) : ms.value >= DIVE_MS ? 1 : 0,
      top: (screen - height) * b,
      borderTopLeftRadius: radius.card * b,
      borderTopRightRadius: radius.card * b,
    };
  });
  const glow = useAnimatedStyle(() => ({
    opacity: 1 - settle.value,
    borderTopLeftRadius: radius.card * settle.value,
    borderTopRightRadius: radius.card * settle.value,
  }));

  if (reduce) return null;
  return (
    <Animated.View pointerEvents="none" style={[styles.iris, frame]}>
      {!dark && <Animated.View style={[styles.irisGlow, glow]} />}
    </Animated.View>
  );
}

const styles = StyleSheet.create({
  box: { position: 'absolute', left: 0, top: 0, width: 300, height: 300 },
  layer: { position: 'absolute', left: -OX, top: -OY, width: BOX, height: BOX },
  fill: { position: 'absolute', left: 0, top: 0, width: BOX, height: BOX },
  face: { backfaceVisibility: 'hidden' },
  iris: { position: 'absolute', left: 0, right: 0, bottom: 0, backgroundColor: color.paper },
  irisGlow: { ...StyleSheet.absoluteFill, backgroundColor: metal.glow },
});
