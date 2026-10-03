/** Owns the map ref and everything about moving the camera.
 *
 * Three refs that always had to move together, and one rule that was applied in
 * two of the three places it was needed: `animateToRegion` before `onMapReady`
 * is accepted and then silently discarded. Going through `flyTo` makes that
 * impossible to forget - see docs/10-decisions.md#the-app.
 *
 * It also sits between the map and `onRegionChangeComplete`, because that
 * callback cannot be trusted on its own.
 *
 * **A long `animateToRegion` never reports.** A short one does: fly 40m and the
 * map settles and announces the region it settled on, which is what fetches.
 * Fly to another continent and nothing is ever announced. Measured, not
 * guessed - `[CAM]` traces of the same build show the landing reported at 40m
 * and never at 6,000km.
 *
 * Two flows died on that. Opening the app anywhere far from FALLBACK_REGION
 * fetched Manhattan once and stopped, so somebody in Copenhagen read
 * Manhattan's memory count over their own city and F19's card never appeared;
 * and F19's own "Show me New York", which is a long jump by definition, moved
 * the camera and left the pins behind.
 *
 * So a commanded flight is watched. If the map announces the landing, that
 * wins - it knows the region it actually fitted to the screen, and we do not.
 * If it says nothing by the time the flight is over, we say it instead. And
 * while a flight is in the air, a report about somewhere else is the map
 * talking about where it used to be, which is dropped rather than fetched.
 *
 * This is the whole of the exception to "never fetch alongside
 * animateToRegion" (mobile/UI.md rule 10). The rule's reason - that eager
 * fetching asks twice for one press, once for a viewport that never exists -
 * still holds for every move the map does report, and those still fetch once,
 * from the map's own region.
 */

import { useCallback, useEffect, useRef, useState } from 'react';
import type MapView from 'react-native-maps';

import { metersBetween, type Region } from './region.ts';

const FLIGHT_MS = 600;

/** Added to a flight's duration before we give up waiting for the map. Long
 *  enough not to race a landing that was going to be announced anyway. */
const GRACE_MS = 700;

/** How far off a report can be and still count as the landing. Generous,
 *  because the map fits the deltas to the screen and settles near the region
 *  rather than on it - and far below any distance worth flying. */
const ARRIVED_M = 500;

export function useMapCamera(onRegionSettled: (region: Region) => void) {
  const mapRef = useRef<MapView>(null);
  // Tracked, not inferred from mapRef.current: the ref is set the moment
  // MapView renders, which is before the native map will accept a camera move.
  const ready = useRef(false);
  // The same, for effects that must wait for it (a fit is dropped before it).
  const [mapReady, setMapReady] = useState(false);
  const pending = useRef<Region | null>(null);
  // Where the camera was last told to go, while it is still on its way.
  const flying = useRef<Region | null>(null);
  const giveUp = useRef<ReturnType<typeof setTimeout> | null>(null);

  const land = useCallback(
    (region: Region) => {
      if (giveUp.current) clearTimeout(giveUp.current);
      giveUp.current = null;
      flying.current = null;
      onRegionSettled(region);
    },
    [onRegionSettled],
  );

  /** Start watching a flight we just commanded. */
  const watch = useCallback(
    (region: Region, duration: number) => {
      if (giveUp.current) clearTimeout(giveUp.current);
      flying.current = region;
      giveUp.current = setTimeout(() => land(region), duration + GRACE_MS);
    },
    [land],
  );

  useEffect(
    () => () => {
      if (giveUp.current) clearTimeout(giveUp.current);
    },
    [],
  );

  /** Move the camera, or queue it until the map can take it. */
  const flyTo = useCallback(
    (region: Region, duration = FLIGHT_MS) => {
      if (!ready.current) {
        // Nothing is moving yet, so there is nothing to wait for. onMapReady
        // starts the watch when it replays this.
        pending.current = region;
        return;
      }
      mapRef.current?.animateToRegion(region, duration);
      watch(region, duration);
    },
    [watch],
  );

  const onMapReady = useCallback(() => {
    ready.current = true;
    setMapReady(true);
    const queued = pending.current;
    if (!queued) return;
    pending.current = null;
    mapRef.current?.animateToRegion(queued, FLIGHT_MS);
    watch(queued, FLIGHT_MS);
  }, [watch]);

  const onRegionChangeComplete = useCallback(
    (reported: Region) => {
      const destination = flying.current;
      if (
        destination &&
        metersBetween(
          destination.latitude,
          destination.longitude,
          reported.latitude,
          reported.longitude,
        ) >= ARRIVED_M
      ) {
        // The map reporting somewhere we have already left - the region it was
        // born at, announced after we flew away from it. Fetching for it would
        // put the wrong pins on the screen and, being the later request, win.
        return;
      }
      land(reported);
    },
    [land],
  );

  /** Whether a commanded flight has yet to land. */
  const inFlight = useCallback(() => flying.current !== null, []);

  return { mapRef, mapReady, flyTo, inFlight, onMapReady, onRegionChangeComplete };
}
