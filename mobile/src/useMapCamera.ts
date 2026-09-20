/** Owns the map ref and everything about moving the camera.
 *
 * Three refs that always had to move together, and one rule that was applied in
 * two of the three places it was needed: `animateToRegion` before `onMapReady`
 * is accepted and then silently discarded. Going through `flyTo` makes that
 * impossible to forget - see docs/10-decisions.md#the-app.
 */

import { useCallback, useRef } from 'react';
import type MapView from 'react-native-maps';

import type { Region } from './region.ts';

export function useMapCamera() {
  const mapRef = useRef<MapView>(null);
  // Tracked, not inferred from mapRef.current: the ref is set the moment
  // MapView renders, which is before the native map will accept a camera move.
  const ready = useRef(false);
  const pending = useRef<Region | null>(null);

  /** Move the camera, or queue it until the map can take it. */
  const flyTo = useCallback((region: Region, duration = 600) => {
    if (ready.current) mapRef.current?.animateToRegion(region, duration);
    else pending.current = region;
  }, []);

  const onMapReady = useCallback(() => {
    ready.current = true;
    const queued = pending.current;
    if (!queued) return;
    pending.current = null;
    mapRef.current?.animateToRegion(queued, 600);
  }, []);

  return { mapRef, flyTo, onMapReady };
}
