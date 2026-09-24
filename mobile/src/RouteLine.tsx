/** Today's route: an ink line over a paper casing, from the start through
 *  every stop and home. Still - the numbered pins already say the order.
 *
 *  It used to march dots along the line by ticking `lineDashPhase`. On iOS,
 *  react-native-maps answers any prop change on a Polyline by removing the
 *  overlay and adding it back (AIRMapPolyline.m, `update`), so every tick
 *  re-rendered it from scratch: the line restarted and stuttered. Nothing on
 *  a Polyline can move smoothly; docs/09-visual-design.md has the options that
 *  could, and why neither was taken.
 *
 *  Ink, never seal: seal means openable and nothing else (mobile/UI.md). Hex
 *  and not theme tokens because a Polyline takes a real colour, not a
 *  platform-resolved one - these are theme.ts `ink` and `paper`.
 */

import { useMemo } from 'react';
import { Polyline } from 'react-native-maps';

import type { Coordinates } from './api.ts';

type Props = { path: Coordinates[]; dark: boolean };

export default function RouteLine({ path, dark }: Props) {
  // Memoised: a fresh array makes react-native-maps rebuild the overlay.
  const coordinates = useMemo(
    () => path.map((at) => ({ latitude: at.lat, longitude: at.lng })),
    [path],
  );

  return (
    <>
      <Polyline
        coordinates={coordinates}
        strokeWidth={8}
        strokeColor={dark ? '#161412' : '#F7F4EE'}
        lineCap="round"
        lineJoin="round"
      />
      <Polyline
        coordinates={coordinates}
        strokeWidth={4}
        strokeColor={dark ? '#F2EDE4' : '#1C1917'}
        lineCap="round"
        lineJoin="round"
      />
    </>
  );
}
