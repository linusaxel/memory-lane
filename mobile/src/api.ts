/** Memory Lane API client. One fetch, no wrapper library. */

export const API_BASE = process.env.EXPO_PUBLIC_API_URL ?? 'http://localhost:8080';
const BASE = API_BASE;

export type Coordinates = { lat: number; lng: number };

/** Who published the video this memory came out of. */
export type Source = {
  name: string;
  url: string | null;
  icon_url: string | null;
};

export type ContentRef = {
  id: number;
  title: string | null;
  url: string;
  timestamp_start: number;
  /** Already a deep link to the right second - open it as-is. */
  timestamp_url: string;
  /** Null for the handful of videos whose channel the config never names. */
  source: Source | null;
};

export type Memory = {
  id: number;
  /** Empty string while locked. The server never sends it until you are there. */
  summary: string;
  place: {
    id: number;
    name: string;
    coordinates: Coordinates | null;
    precision_meters: number;
  };
  distance_meters: number | null;
  /** Null while locked: the source is part of what standing there buys. */
  content: ContentRef | null;
  tags: string[];
  /** Only 'high' and 'medium' ever reach the database; 'low' is filtered at extraction. */
  confidence: string;
  /**
   * The server decided this, not the app. Hiding a summary the API already
   * sent would be theatre - see F7 in docs/08-ux-flows.md.
   */
  locked: boolean;
  unlock_radius_meters: number | null;
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

async function get<T>(path: string, params: URLSearchParams, signal?: AbortSignal): Promise<T> {
  // AbortSignal.timeout and AbortSignal.any are not reliably present on Hermes,
  // so the timer is wired by hand and the caller's signal is forwarded onto it.
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS);
  const forwardAbort = () => controller.abort();
  signal?.addEventListener('abort', forwardAbort);

  try {
    const res = await fetch(`${BASE}${path}?${params}`, { signal: controller.signal });
    if (!res.ok) throw new Error(`API ${res.status}`);
    return (await res.json()) as T;
  } finally {
    clearTimeout(timer);
    signal?.removeEventListener('abort', forwardAbort);
  }
}

export async function fetchNearby(
  lat: number,
  lng: number,
  radiusKm: number,
  signal?: AbortSignal,
): Promise<LocatedMemory[]> {
  // No position goes with this: the map never unlocks anything, however close
  // you are standing. Only unlockMemory does, and only when asked.
  const params = new URLSearchParams({
    lat: String(lat),
    lng: String(lng),
    radius_km: String(radiusKm),
    limit: '100',
  });

  const body = await get<{ memories?: Memory[] }>('/v1/memories/nearby', params, signal);
  // The null-coordinate filter is the trust boundary: places.coordinates is
  // nullable in the schema and a null-coordinate marker crashes
  // react-native-maps.
  return (body.memories ?? []).filter(hasCoordinates);
}

/**
 * Ask the server to open one memory. It re-checks the distance itself and can
 * still say no - GPS moves between the press and the request - so a result that
 * comes back still locked is a refusal, not a success.
 */
export async function unlockMemory(id: number, at: Coordinates): Promise<LocatedMemory | null> {
  const memory = await get<Memory>(
    `/v1/memories/${id}`,
    new URLSearchParams({ at_lat: String(at.lat), at_lng: String(at.lng) }),
  );
  return !memory.locked && hasCoordinates(memory) ? memory : null;
}

/** Where the corpus actually is, for a map that has nothing on it. */
export type Hotspot = {
  label: string;
  lat: number;
  lng: number;
  memories: number;
};

/**
 * Asked once, lazily, and only when the map turns up empty. "No memories here
 * yet" is true and useless outside New York; this is what turns it into
 * somewhere to go.
 */
export async function fetchHotspots(signal?: AbortSignal): Promise<Hotspot[]> {
  const body = await get<{ hotspots?: Hotspot[] }>(
    '/v1/stats',
    new URLSearchParams({ hotspots: '3' }),
    signal,
  );
  return body.hotspots ?? [];
}
