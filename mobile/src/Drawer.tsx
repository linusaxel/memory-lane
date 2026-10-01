/** The journal's way in: a panel that slides over the map from the left,
 *  opened by the Journal pill or a swipe off the left edge. The map stays in
 *  view at the right, dimmed, so the panel reads as a layer over the world
 *  rather than another page (docs/10-decisions.md, "The journal is a drawer; settings are
 *  the map's").
 *
 *  React Native's own Animated and PanResponder, not a drawer library: those
 *  need gesture-handler and reanimated, which is a native rebuild for one
 *  panel. ponytail: JS-thread spring, move to reanimated if it drops frames. */

import { useEffect, useRef, useState, type ReactNode } from 'react';
import {
  AccessibilityInfo,
  Animated,
  PanResponder,
  Pressable,
  StyleSheet,
  useWindowDimensions,
  View,
} from 'react-native';
import * as Haptics from 'expo-haptics';

import { color } from './theme.ts';

/** Wide enough to claim a deliberate swipe, narrow enough that the map keeps
 *  its pans; it ends where the Journal pill begins. */
const EDGE = 18;
/** The map left showing at the right of the panel. */
const PEEK = 44;

type Props = {
  open: boolean;
  onOpen: () => void;
  onClose: () => void;
  children: ReactNode;
};

export default function Drawer({ open, onOpen, onClose, children }: Props) {
  const { width: screen } = useWindowDimensions();
  const width = Math.min(screen - PEEK, 380);
  // 0 shut, 1 open. Everything (panel, scrim) is read off this one value.
  const progress = useRef(new Animated.Value(0)).current;
  const reduceMotion = useRef(false);
  // Still drawn while it springs shut, then out of the way of the map's touches.
  const [shown, setShown] = useState(open);
  // Where it is going, so `open` arriving after a drag already decided it
  // does not restart the spring and lose the fling.
  const target = useRef<0 | 1>(open ? 1 : 0);
  // The responders are made once; they read the props through this.
  const live = useRef({ open, onOpen, onClose, width });
  live.current = { open, onOpen, onClose, width };

  useEffect(() => {
    AccessibilityInfo.isReduceMotionEnabled().then((on) => (reduceMotion.current = on));
  }, []);

  const settle = (to: 0 | 1, velocity = 0) => {
    target.current = to;
    if (to === 1) setShown(true);
    const done = ({ finished }: { finished: boolean }) => {
      if (!finished) return;
      if (to === 1) Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Light).catch(() => {});
      else setShown(false);
    };
    if (reduceMotion.current) {
      Animated.timing(progress, { toValue: to, duration: 0, useNativeDriver: true }).start(done);
      return;
    }
    // A little overshoot on the way in, none on the way out: it lands, it
    // does not bounce off the edge of the screen.
    Animated.spring(progress, {
      toValue: to,
      velocity,
      useNativeDriver: true,
      ...(to === 1 ? { tension: 70, friction: 9 } : { tension: 90, friction: 12, overshootClamping: true }),
    }).start(done);
  };

  useEffect(() => {
    if (target.current !== (open ? 1 : 0)) settle(open ? 1 : 0);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open]);

  // Opening and closing are one drag: from the edge strip it starts at 0,
  // on the panel at 1. Release past halfway, or flung, and it goes.
  const drag = (from: 0 | 1) =>
    PanResponder.create({
      onMoveShouldSetPanResponder: (_, g) =>
        Math.abs(g.dx) > 10 && Math.abs(g.dx) > Math.abs(g.dy) * 1.5 && (from === 0 ? g.dx > 0 : g.dx < 0),
      onMoveShouldSetPanResponderCapture: (_, g) =>
        from === 1 && g.dx < -10 && Math.abs(g.dx) > Math.abs(g.dy) * 1.5,
      onPanResponderGrant: () => {
        progress.stopAnimation();
        setShown(true);
        // Tell App now, not on release: what hides under the journal (the
        // walk preview's slider) has to go before the panel is over it.
        if (from === 0) {
          target.current = 1;
          live.current.onOpen();
        }
      },
      onPanResponderMove: (_, g) => {
        progress.setValue(Math.max(0, Math.min(1, from + g.dx / live.current.width)));
      },
      onPanResponderRelease: (_, g) => {
        const at = Math.max(0, Math.min(1, from + g.dx / live.current.width));
        const flung = Math.abs(g.vx) > 0.5;
        if (flung ? g.vx > 0 : at > 0.5) {
          settle(1, g.vx);
        } else {
          settle(0, g.vx);
          live.current.onClose();
        }
      },
      onPanResponderTerminate: () => settle(target.current),
    });
  const edge = useRef(drag(0)).current;
  const panel = useRef(drag(1)).current;

  const translateX = progress.interpolate({ inputRange: [0, 1], outputRange: [-width, 0] });
  const scrim = progress.interpolate({ inputRange: [0, 1], outputRange: [0, 1], extrapolate: 'clamp' });

  return (
    <>
      {!shown && <View style={styles.edge} {...edge.panHandlers} />}
      {/* Shut, display:none rather than unmounted, as the journal cover was:
          it keeps its lists, and leaves the map's touches and the
          accessibility tree alone (UI.md rule 9). */}
      <View style={[StyleSheet.absoluteFill, !shown && styles.hidden]}>
        <Animated.View style={[styles.scrim, { opacity: scrim }]}>
          {/* Not announced: the panel's × is the accessible way out. */}
          <Pressable style={StyleSheet.absoluteFill} onPress={onClose} accessible={false} />
        </Animated.View>
        <Animated.View
          style={[styles.panel, { width, transform: [{ translateX }] }]}
          accessibilityViewIsModal={open}
          {...panel.panHandlers}
        >
          {children}
        </Animated.View>
      </View>
    </>
  );
}

const styles = StyleSheet.create({
  hidden: { display: 'none' },
  edge: { position: 'absolute', top: 0, bottom: 0, left: 0, width: EDGE },
  scrim: { position: 'absolute', top: 0, right: 0, bottom: 0, left: 0, backgroundColor: color.scrim },
  panel: {
    position: 'absolute',
    top: 0,
    bottom: 0,
    left: 0,
    backgroundColor: color.paper,
    // Its own edge against the dimmed map, not a rule: it is lifted, not drawn.
    shadowColor: color.shadow,
    shadowOffset: { width: 6, height: 0 },
    shadowRadius: 24,
    shadowOpacity: 0.18,
  },
});
