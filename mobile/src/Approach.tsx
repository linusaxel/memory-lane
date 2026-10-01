/** How close you are, as the ring you are going to hold - see "The walk in is
 *  the same ring" under "The unlock control" in UI.md. */

import { useEffect, useRef } from 'react';
import { Animated, StyleSheet, View } from 'react-native';

import Glyph from './Glyph.tsx';
import { approachOf } from './reach.ts';
import { color } from './theme.ts';

const RING = 84;

type Props = {
  /** How far away the memory is, or null when there is no position at all. */
  meters: number | null;
  /** The server's unlock radius, which is where the ring reads full. */
  radius: number;
  /** In place of how close: how full, 0-1, as the steps towards an unlock. */
  progress?: number;
  size?: number;
};

export default function Approach({ meters, radius, progress, size = RING }: Props) {
  const filled = progress ?? approachOf(meters, radius);
  const fill = useRef(new Animated.Value(filled)).current;

  useEffect(() => {
    // Springs rather than jumps: a position arrives every 5m, and a disc that
    // snaps between two sizes reads as a glitch where a rise reads as ground
    // covered.
    Animated.spring(fill, {
      toValue: filled,
      speed: 6,
      bounciness: 4,
      useNativeDriver: true,
    }).start();
  }, [filled, fill]);

  return (
    <View style={[styles.ring, { width: size, height: size, borderRadius: size / 2 }]}>
      <View style={[styles.band, { borderRadius: size / 2 }]} />
      {/* Paper shrinking over the band is what makes the rim appear. Scaling
          a cover rather than growing a ring, because a border width cannot go
          on the native driver and a transform can. */}
      <Animated.View
        style={[
          styles.cover,
          { borderRadius: size / 2, transform: [{ scale: fill.interpolate(CLOSE) }] },
        ]}
      />
      <Glyph name="lock.fill" size={Math.round((size * 2) / 7)} color={color.faded} />
    </View>
  );
}

/** 1 hides the band completely; 0.72 leaves a rim about a seventh of the
 *  radius. Never quite 0 progress to nothing - at the far edge there should
 *  still be a hairline, so the ring reads as an instrument rather than as an
 *  outline somebody forgot to fill. */
const CLOSE = { inputRange: [0, 1], outputRange: [0.985, 0.72] };

const styles = StyleSheet.create({
  ring: {
    borderWidth: 3,
    borderColor: color.rule,
    backgroundColor: color.paper,
    alignItems: 'center',
    justifyContent: 'center',
    overflow: 'hidden',
  },
  band: {
    position: 'absolute',
    top: 0,
    left: 0,
    right: 0,
    bottom: 0,
    backgroundColor: color.faded,
  },
  cover: {
    position: 'absolute',
    top: 0,
    left: 0,
    right: 0,
    bottom: 0,
    backgroundColor: color.paper,
  },
});
