/** The preview's walk, drawn the way Apple Maps draws a route: a blue line
 *  with a darker edge, under the street names (patches/react-native-maps*
 *  moves polylines to MKOverlayLevelAboveRoads). Only the preview has one -
 *  while walking, the next pin hops instead (docs/09-visual-design.md §3a).
 *
 *  Still, because on iOS any Polyline prop change removes and re-adds the
 *  overlay (AIRMapPolyline.m, `update`). Hex, not theme tokens, because a
 *  Polyline takes a real colour: the fill is theme.ts `route`.
 */

import { useMemo } from 'react';
import { Polyline } from 'react-native-maps';

import type { Coordinates } from './api.ts';
import { simplifyPath } from './region.ts';

type Props = { path: Coordinates[]; dark: boolean };

export default function RouteLine({ path, dark }: Props) {
  // Memoised: a fresh array makes react-native-maps rebuild the overlay.
  const coordinates = useMemo(
    () =>
      // 12m: wider than the hop between two sidewalks, narrower than a block.
      simplifyPath(path, 12).map((at) => ({ latitude: at.lat, longitude: at.lng })),
    [path],
  );

  return (
    <>
      <Polyline
        coordinates={coordinates}
        strokeWidth={9}
        strokeColor={dark ? '#1B4F99' : '#0E3F8C'}
        lineCap="round"
        lineJoin="round"
      />
      <Polyline
        coordinates={coordinates}
        strokeWidth={6}
        strokeColor={dark ? '#5AA2FF' : '#1A64D6'}
        lineCap="round"
        lineJoin="round"
      />
    </>
  );
}
