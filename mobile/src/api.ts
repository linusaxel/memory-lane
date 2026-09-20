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

  const res = await fetch(`${BASE}/v1/memories/nearby?${params}`, { signal });
  if (!res.ok) throw new Error(`API ${res.status}`);

  const body = (await res.json()) as { memories?: Memory[] };
  // `meta.total` is unreliable on this endpoint (its count query ignores the
  // active filters), so it is deliberately ignored.
  //
  // The null-coordinate filter is the trust boundary: places.coordinates is
  // nullable in the schema and a null-coordinate marker crashes react-native-maps.
  return (body.memories ?? []).filter(hasCoordinates);
}
