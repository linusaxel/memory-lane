/** Which memories are under Explore's viewport.
 *
 * The region is the one useMapCamera reports, so a commanded flight fetches
 * once, where it lands (UI.md rule 10). Panning reports continuously: the
 * effect's cleanup is the debounce, and aborting the request it started is
 * what keeps a slow answer for the region you left from overwriting this one.
 */

import { useEffect, useRef, useState } from 'react';

import { fetchNearby, type LocatedMemory } from './api.ts';
import { isSameQuery, regionToRadiusKm, type Region } from './region.ts';

const DEBOUNCE_MS = 400;

export function useNearby(region: Region, active: boolean): LocatedMemory[] {
  const [memories, setMemories] = useState<LocatedMemory[]>([]);
  // Only successes are recorded, so a failed viewport is asked again.
  const lastFetched = useRef<Region | null>(null);

  useEffect(() => {
    if (!active || isSameQuery(lastFetched.current, region)) return;
    const abort = new AbortController();
    const timer = setTimeout(() => {
      fetchNearby(region.latitude, region.longitude, regionToRadiusKm(region), abort.signal)
        .then((found) => {
          if (abort.signal.aborted) return;
          lastFetched.current = region;
          setMemories(found);
        })
        // Keep the last good pins: a map that empties on a dropped request
        // looks like the area went blank rather than the network.
        .catch(() => {});
    }, DEBOUNCE_MS);
    return () => {
      clearTimeout(timer);
      abort.abort();
    };
  }, [region, active]);

  return memories;
}
