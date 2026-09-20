/** Memory Lane API client. One fetch, no wrapper library. */

const BASE = process.env.EXPO_PUBLIC_API_URL ?? 'http://localhost:8080';

export type Coordinates = { lat: number; lng: number };

export type Memory = {
  id: number;
  summary: string;
  place: {
    id: number;
    name: string;
    coordinates: Coordinates | null;
    precision_meters: number;
  };
  distance_meters: number | null;
  content: {
    id: number;
    title: string | null;
    url: string;
    timestamp_start: number;
    /** Already a deep link to the right second - open it as-is. */
    timestamp_url: string;
  };
  tags: string[];
  /** Only 'high' and 'medium' ever reach the database; 'low' is filtered at extraction. */
  confidence: string;
};

/** A memory whose place has real coordinates - safe to drop on a map. */
export type LocatedMemory = Memory & { place: Memory['place'] & { coordinates: Coordinates } };

function hasCoordinates(m: Memory): m is LocatedMemory {
  const c = m.place?.coordinates;
  return !!c && Number.isFinite(c.lat) && Number.isFinite(c.lng);
}

/**
 * A hung request is worse than a failed one: it renders as "0 memories here"
 * forever, so an unreachable server is indistinguishable from an empty area.
 * fetch has no default timeout, so this is the only thing that ends the wait.
 */
export const REQUEST_TIMEOUT_MS = 8000;

export async function fetchNearby(
  lat: number,
  lng: number,
  radiusKm: number,
  signal?: AbortSignal,
): Promise<LocatedMemory[]> {
  const params = new URLSearchParams({
    lat: String(lat),
    lng: String(lng),
    radius_km: String(radiusKm),
    limit: '100',
  });

  // AbortSignal.timeout and AbortSignal.any are not reliably present on Hermes,
  // so the timer is wired by hand and the caller's signal is forwarded onto it.
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS);
  const forwardAbort = () => controller.abort();
  signal?.addEventListener('abort', forwardAbort);

  try {
    const res = await fetch(`${BASE}/v1/memories/nearby?${params}`, {
      signal: controller.signal,
    });
    if (!res.ok) throw new Error(`API ${res.status}`);

    const body = (await res.json()) as { memories?: Memory[] };
    // The null-coordinate filter is the trust boundary: places.coordinates is
    // nullable in the schema and a null-coordinate marker crashes
    // react-native-maps.
    return (body.memories ?? []).filter(hasCoordinates);
  } finally {
    clearTimeout(timer);
    signal?.removeEventListener('abort', forwardAbort);
  }
}
