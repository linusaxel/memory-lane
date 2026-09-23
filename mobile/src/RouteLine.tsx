/** Today's route, drawn as a flow: dots that march from the start through
 *  stop 1 to the last stop and home, round and round. Ink, never seal - it is
 *  a suggestion, not an unlock state.
 *
 *  Its own component so the tick re-renders one Polyline and not the screen.
 *  The phase is the only prop that changes per tick. A fresh coordinates array
 *  makes react-native-maps rebuild the overlay, which restarts the flow, so
 *  the coordinates are memoised and the colour is fixed - it used to ebb, and
 *  that alone repainted the line twenty times a second.
 *
 *  The phase animates on iOS only (react-native-maps has no lineDashPhase on
 *  Android); there, and under Reduce Motion, it is the same line, still.
 *
 *  One colour, not `strokeColors`: that prop swaps in react-native-maps' own
 *  gradient renderer, which does not scale the dash pattern with zoom, so the
 *  dots fuse into a solid bar.
 */

import { useEffect, useMemo, useState } from 'react';
import { AccessibilityInfo } from 'react-native';
import { Polyline } from 'react-native-maps';

import type { Coordinates } from './api.ts';

const DOT = 1;
const GAP = 11;
const PERIOD = DOT + GAP;
/** Points per second the dots travel. Walking pace on screen, not a spinner. */
const SPEED = 14;
const TICK_MS = 50;

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

  const coordinates = useMemo(
    () => path.map((at) => ({ latitude: at.lat, longitude: at.lng })),
    [path],
  );

  // A falling phase moves the pattern away from the first coordinate, which is
  // the start: the dots flow toward stop 1 and on round the loop.
  const phase = PERIOD - ((t / 1000) * SPEED) % PERIOD;

  return (
    <Polyline
      coordinates={coordinates}
      strokeWidth={4}
      strokeColor={dark ? 'rgba(189,181,168,0.7)' : 'rgba(74,68,61,0.7)'}
      lineCap="round"
      lineDashPattern={[DOT, GAP]}
      lineDashPhase={phase}
    />
  );
}
