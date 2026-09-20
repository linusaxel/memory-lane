/** Which memories are under the current viewport.
 *
 * All of it: the viewport, the debounce, the out-of-order guard and the
 * same-question guard, which only make sense together and were four refs and
 * three pieces of state in App.tsx.
 */

import { useCallback, useEffect, useRef, useState } from 'react';

import { fetchNearby, type LocatedMemory } from './api.ts';
import { isSameQuery, regionToRadiusKm, type Region } from './region.ts';
import type { Status } from './types.ts';

const DEBOUNCE_MS = 400;

export function useNearby(initialRegion: Region) {
  const [region, setRegion] = useState<Region>(initialRegion);
  const [memories, setMemories] = useState<LocatedMemory[]>([]);
  const [status, setStatus] = useState<Status>('loading');

  const mounted = useRef(true);
  const debounce = useRef<ReturnType<typeof setTimeout> | null>(null);
  const latestRequest = useRef(0);
  // The last viewport that actually came back with data. Only successes are
  // recorded, so "Try again" after a failure is never mistaken for a repeat.
  const lastFetched = useRef<Region | null>(null);

  useEffect(() => {
    mounted.current = true;
    return () => {
      mounted.current = false;
      if (debounce.current) clearTimeout(debounce.current);
    };
  }, []);

  const load = useCallback(async (r: Region) => {
    // Asking the same question twice. animateToRegion fires
    // onRegionChangeComplete when it lands, and a programmatic move looks
    // exactly like a pan from there - so recentring fetched once eagerly and
    // again a second later. The guard lives here because every caller routes
    // through load, including "Try again".
    if (isSameQuery(lastFetched.current, r)) return;

    // Responses can land out of order: a slow request for the region you just
    // left resolves after a fast one for the region you are looking at and
    // overwrites it, including stamping 'failed' over a newer success.
    const request = ++latestRequest.current;
    const isStale = () => !mounted.current || request !== latestRequest.current;

    setStatus('loading');
    try {
      const found = await fetchNearby(r.latitude, r.longitude, regionToRadiusKm(r));
      if (isStale()) return;
      lastFetched.current = r;
      setMemories(found);
      setStatus('ready');
    } catch {
      if (isStale()) return;
      // Keep the last good pins. They are still true of the place, and a map
      // that empties itself on a dropped request looks like the area went blank
      // rather than the network.
      setStatus('failed');
    }
  }, []);

  /** Ask again for a viewport we have already fetched - after filing a memory,
   *  when the pins changed but the question did not. */
  const reload = useCallback(
    (r: Region) => {
      lastFetched.current = null;
      load(r);
    },
    [load],
  );

  const onRegionChangeComplete = useCallback(
    (r: Region) => {
      setRegion(r);
      if (debounce.current) clearTimeout(debounce.current);
      debounce.current = setTimeout(() => load(r), DEBOUNCE_MS);
    },
    [load],
  );

  return { region, setRegion, memories, status, load, reload, onRegionChangeComplete };
}
