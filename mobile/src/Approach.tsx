/** How close you are, as the ring you are going to hold.
 *
 * The out-of-reach sheet used to be a grey padlock over a number. The number
 * changes as you walk - `watchPositionAsync` reports every 25m - but a number
 * changing is not felt, and walking is the one thing this product asks of
 * anybody. So the same circle the unlock control uses fills as you close on
 * it, and when it is full it *is* that control: cross the radius and the
 * composition swaps, the ring you were filling is the ring you now hold.
 *
 * It is deliberately not seal. Seal means openable and nothing else in the
 * app wears it (UI.md, Tokens), so an approach that borrowed it would be
 * promising something it cannot deliver from here.
 *
 * And it thickens a rim rather than filling the middle, which is not a
 * decorative choice. The middle belongs to the hold: the unlock ring's disc
 * rises from the centre. If the approach filled the centre too, then arriving
 * - the best moment in the product - would swap a full circle for an almost
 * empty one and read as the ring draining just as you got there. A rim
 * closing inward leaves the centre empty for the thing that comes next, and
 * it echoes the strain ring the hold uses in its own last quarter.
 *
 * Empty at three radii, because that is already the app's idea of nearly -
 * `WARM_MULTIPLIER` in reach.ts, the distance at which a pin turns from
 * too-far to worth-walking. Past it there is nothing to show and the figure
 * underneath says it better.
 */

import { useEffect, useRef } from 'react';
import { Animated, StyleSheet, View } from 'react-native';

import Padlock from './Padlock.tsx';
import { approachOf } from './reach.ts';
import { color } from './theme.ts';

const RING = 84;

type Props = {
  /** How far away the memory is, or null when there is no position at all. */
  meters: number | null;
  /** The server's unlock radius, which is where the ring reads full. */
  radius: number;
};

export default function Approach({ meters, radius }: Props) {
  const filled = approachOf(meters, radius);
  const fill = useRef(new Animated.Value(filled)).current;

  useEffect(() => {
    // Springs rather than jumps: a position arrives every 25m, and a disc that
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
    <View style={styles.ring}>
      <View style={styles.band} />
      {/* Paper shrinking over the band is what makes the rim appear. Scaling
          a cover rather than growing a ring, because a border width cannot go
          on the native driver and a transform can. */}
      <Animated.View
        style={[styles.cover, { transform: [{ scale: fill.interpolate(CLOSE) }] }]}
      />
      <Padlock size={27} color={color.faded} />
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
    width: RING,
    height: RING,
    borderRadius: RING / 2,
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
    borderRadius: RING / 2,
    backgroundColor: color.faded,
  },
  cover: {
    position: 'absolute',
    top: 0,
    left: 0,
    right: 0,
    bottom: 0,
    borderRadius: RING / 2,
    backgroundColor: color.paper,
  },
});
