/** Today's route, drawn as a flow: dots that march from you toward the next
 *  stop and on through the rest, the whole line ebbing slowly. Ink, never
 *  seal - it is a suggestion, not an unlock state.
 *
 *  Its own component so the tick re-renders one Polyline and not the screen.
 *  The phase animates on iOS only (react-native-maps has no lineDashPhase on
 *  Android); there, and under Reduce Motion, it is the same line, still.
 *
 *  One colour, not `strokeColors`: that prop swaps in react-native-maps' own
 *  gradient renderer, which does not scale the dash pattern with zoom, so the
 *  dots fuse into a solid bar.
 */

import { useEffect, useState } from 'react';
import { AccessibilityInfo } from 'react-native';
import { Polyline } from 'react-native-maps';

import type { Coordinates } from './api.ts';

const DOT = 1;
const GAP = 11;
const PERIOD = DOT + GAP;
/** Points per second the dots travel. Walking pace on screen, not a spinner. */
const SPEED = 14;
const TICK_MS = 50;
/** One slow ebb of the whole line's strength, in milliseconds. */
const EBB_MS = 2600;

type Props = { path: Coordinates[]; dark: boolean };

export default function RouteLine({ path, dark }: Props) {
  const [t, setT] = useState(0);
  const [reduceMotion, setReduceMotion] = useState(false);

  useEffect(() => {
    AccessibilityInfo.isReduceMotionEnabled().then(setReduceMotion);
    const sub = AccessibilityInfo.addEventListener('reduceMotionChanged', setReduceMotion);
    return () => sub.remove();
  }, []);

  useEffect(() => {
    if (reduceMotion) {
      setT(0);
      return;
    }
    const started = Date.now();
    const id = setInterval(() => setT(Date.now() - started), TICK_MS);
    return () => clearInterval(id);
  }, [reduceMotion]);

  // A falling phase moves the pattern away from the first coordinate, which is
  // you: the dots flow toward where you are going.
  const phase = PERIOD - ((t / 1000) * SPEED) % PERIOD;
  const ebb = 0.8 + 0.2 * Math.cos((2 * Math.PI * t) / EBB_MS);
  const rgb = dark ? '189,181,168' : '74,68,61';

  return (
    <Polyline
      coordinates={path.map((at) => ({ latitude: at.lat, longitude: at.lng }))}
      strokeWidth={4}
      strokeColor={`rgba(${rgb},${(0.75 * ebb).toFixed(3)})`}
      lineCap="round"
      lineDashPattern={[DOT, GAP]}
      lineDashPhase={phase}
    />
  );
}
