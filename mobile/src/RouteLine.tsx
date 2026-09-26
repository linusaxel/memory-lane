/** The preview's walk, drawn the way Apple Maps draws a route: a blue line
 *  with a darker edge, under the street names (patches/react-native-maps*
 *  moves polylines to MKOverlayLevelAboveRoads). Only the preview has one -
 *  while walking, the next pin hops instead (docs/09-visual-design.md §3a).
 *
 *  Still, because on iOS any Polyline prop change removes and re-adds the
 *  overlay (AIRMapPolyline.m, `update`). theme.ts `solid`, because a Polyline
 *  takes a real colour.
 */

import { useMemo } from 'react';
import { Polyline } from 'react-native-maps';

import type { Coordinates } from './api.ts';
import { simplifyPath } from './region.ts';
import { solid } from './theme.ts';

type Props = { path: Coordinates[]; dark: boolean };

export default function RouteLine({ path, dark }: Props) {
  // Memoised: a fresh array makes react-native-maps rebuild the overlay.
  const { route, routeCasing } = solid(dark);
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
        strokeColor={routeCasing}
        lineCap="round"
        lineJoin="round"
      />
      <Polyline
        coordinates={coordinates}
        strokeWidth={6}
        strokeColor={route}
        lineCap="round"
        lineJoin="round"
      />
    </>
  );
}
