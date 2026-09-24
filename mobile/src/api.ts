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
  /** Already resolved by the server - a document, or a video at the right
   *  second. Open it as-is; never rebuild a YouTube URL by hand. */
  url: string;
  /** Seconds into the recording, and null when the source is not one. It is
   *  the label on the link, not the link. */
  timestamp_start: number | null;
  /** Null for the handful of videos whose channel the config never names. */
  source: Source | null;
};

/** Who filed a memory, when a person did rather than a transcript. */
export type Author = {
  id: string;
  /** Never empty: the server renders an unnamed submitter "Anonymous". */
  name: string;
};

/** A photo or a recording hanging off a memory. */
export type MediaItem = {
  id: number;
  kind: 'photo' | 'audio';
  /** Server-relative. Join it to API_BASE before handing it to <Image>. */
  url: string;
  duration_seconds: number | null;
};

/** Fixed by a CHECK constraint in db/migrations/002_layers.sql. */
export type Layer = 'historical' | 'friend' | 'stranger';

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
  /** What kind of memory this is, and so what shape its pin takes. `historical`
   *  is everything the pipeline extracted, `stranger` everything filed from a
   *  phone. `friend` has no writer yet. See F4 in docs/08-ux-flows.md. */
  layer: Layer;
  /**
   * The server decided this, not the app. Hiding a summary the API already
   * sent would be theatre - see F7 in docs/08-ux-flows.md.
   */
  locked: boolean;
  unlock_radius_meters: number | null;
  /** Null for everything extracted from a video. */
  author: Author | null;
  /** Empty while locked. media_count is not - a locked card is allowed to say
   *  there is a photograph waiting, which is the pull rather than the leak. */
  media: MediaItem[];
  media_count: number;
  /** Set on a locked memory too, like media_count and anniversary - a count
   *  is a passive signal, not the content the gate protects. */
  heart_count: number;
  /** Something happened here on today's date. Set on locked memories too — it
   *  is a reason to walk over and gives away nothing the pin did not. The
   *  server sorts these to the top, which is the whole of "resurfacing": there
   *  are no notifications in this product. */
  anniversary: boolean;
  /** ISO date, or null when the source did not say. The server has never sent
   *  the precision that goes with it - see api/models.py's Memory - so the
   *  edit form can only recover a year, not whether it was exact to the day. */
  happened_at: string | null;
  /** ISO date, and set only while the memory is still sealed. A time lock is a
   *  different refusal from the proximity one: standing here does not open it,
   *  so the sheet must not offer the unlock. Null once the date has passed. */
  opens_at: string | null;
  /** Set once enough people report it. Only ever true from /v1/me/memories -
   *  every other endpoint drops a hidden memory instead of flagging it. */
  hidden: boolean;
};

/** Media urls come back server-relative so the host can change without a
 *  release. Nothing else in the app needs to know where uploads live. */
export function mediaUrl(item: MediaItem): string {
  return `${BASE}${item.url}`;
}

/** A memory whose place has real coordinates - safe to drop on a map. */
export type LocatedMemory = Memory & { place: Memory['place'] & { coordinates: Coordinates } };

function hasCoordinates(m: Memory): m is LocatedMemory {
  const c = m.place?.coordinates;
  return !!c && Number.isFinite(c.lat) && Number.isFinite(c.lng);
}

/** fetch has no default timeout, and a hung request renders as "0 memories
 *  here" forever - indistinguishable from an empty area. */
export const REQUEST_TIMEOUT_MS = 8000;

async function post<T>(path: string, body: unknown, signal?: AbortSignal): Promise<T> {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS);
  const forwardAbort = () => controller.abort();
  signal?.addEventListener('abort', forwardAbort);

  try {
    const res = await fetch(`${BASE}${path}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
      signal: controller.signal,
    });
    if (!res.ok) throw new Error(`API ${res.status}`);
    return (await res.json()) as T;
  } finally {
    clearTimeout(timer);
    signal?.removeEventListener('abort', forwardAbort);
  }
}

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

/** What Explore draws: every memory under the viewport, always locked where
 *  gated. No position goes with this, so nothing unlocks from here. */
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
  const body = await get<{ memories?: Memory[] }>('/v1/memories/nearby', params, signal);
  // A null-coordinate marker crashes react-native-maps (UI.md rule 5).
  return (body.memories ?? []).filter(hasCoordinates);
}

/** Open one memory, and record that it opened. The server re-checks the
 *  distance and can still say no, so a result that comes back still locked is a
 *  refusal - not a success. */
export async function unlockMemory(
  id: number,
  at: Coordinates,
  device: string,
): Promise<LocatedMemory | null> {
  const memory = await post<Memory>(`/v1/memories/${id}/unlock`, {
    device,
    lat: at.lat,
    lng: at.lng,
  });
  return !memory.locked && hasCoordinates(memory) ? memory : null;
}

/** Say this one mattered. One-way: there is no way to un-heart, and hearting
 *  twice from the same device is a harmless no-op that leaves the count
 *  unchanged. No position - unlike unlock, hearting isn't gated by proximity. */
export async function heartMemory(id: number, device: string): Promise<number> {
  const res = await post<{ heart_count: number }>(`/v1/memories/${id}/heart`, { device });
  return res.heart_count;
}

/** Everything this device - and anything signed in alongside it - has earned.
 *  The local copy is the offline cache; this is what survives it being
 *  cleared, and what follows you to a new phone. */
export async function fetchUnlocked(
  device: string,
  signal?: AbortSignal,
): Promise<LocatedMemory[]> {
  const body = await get<{ memories?: Memory[] }>(
    '/v1/unlocks',
    new URLSearchParams({ device }),
    signal,
  );
  return (body.memories ?? []).filter(hasCoordinates);
}

/** One page of what this account has filed, newest first - including a sealed
 *  one (shown shut, seal included) and a reported one (shown, flagged
 *  `hidden`). The one screen that manages your own memories cannot let either
 *  vanish from it silently.
 *
 *  `total` is the server's count of everything filed, not just this page -
 *  the caller compares it against how many rows it has loaded to know
 *  whether there's a next page to ask for. */
export type MinePage = { memories: LocatedMemory[]; total: number };

export const MINE_PAGE_SIZE = 100;

export async function fetchMine(
  device: string,
  offset = 0,
  signal?: AbortSignal,
): Promise<MinePage> {
  const body = await get<{ memories?: Memory[]; meta?: { total?: number } }>(
    '/v1/me/memories',
    new URLSearchParams({ device, limit: String(MINE_PAGE_SIZE), offset: String(offset) }),
    signal,
  );
  return {
    memories: (body.memories ?? []).filter(hasCoordinates),
    total: body.meta?.total ?? 0,
  };
}

/** Today's walk: up to five not-yet-earned stops, in walking order. */
export type TodaysRoute = {
  memories: LocatedMemory[];
  /** ISO date. Compared against the local calendar day to decide whether a
   *  cached copy (mobile/src/route.ts) is still today's. */
  route_date: string;
  /** The route's true size - can be short of the usual handful in a sparse
   *  area, same honesty as every other list's meta.total. */
  size: number;
  /** Ends back where the day's walk started. The server never stores that
   *  start, so the app remembers it (mobile/src/route.ts). */
  loop: boolean;
  /** legs[i] is the street shape from stop i to stop i + 1, or null with no
   *  routing server. Never to or from the start, which is not stored. */
  legs: Coordinates[][] | null;
  /** Street shapes from the start to stop 1 and from the last stop home.
   *  Preview only: the server stores no start, so the phone keeps these. */
  out_leg: Coordinates[] | null;
  home_leg: Coordinates[] | null;
};

type RouteBody = {
  memories?: Memory[];
  meta?: {
    route_date?: string;
    size?: number;
    loop?: boolean;
    legs?: Coordinates[][] | null;
    out_leg?: Coordinates[] | null;
    home_leg?: Coordinates[] | null;
  };
};

function toRoute(body: RouteBody): TodaysRoute {
  return {
    memories: (body.memories ?? []).filter(hasCoordinates),
    route_date: body.meta?.route_date ?? '',
    size: body.meta?.size ?? 0,
    loop: body.meta?.loop ?? false,
    legs: body.meta?.legs ?? null,
    out_leg: body.meta?.out_leg ?? null,
    home_leg: body.meta?.home_leg ?? null,
  };
}

/** The walk this device accepted today, or null when it has not accepted one.
 *  One per device per day: there is no replanning until tomorrow. */
export async function fetchTodaysRoute(
  device: string,
  signal?: AbortSignal,
): Promise<TodaysRoute | null> {
  try {
    return toRoute(await get<RouteBody>('/v1/routes/today', new URLSearchParams({ device }), signal));
  } catch (e) {
    if (e instanceof Error && e.message === 'API 404') return null;
    throw e;
  }
}

/** The walk a `budgetMeters` loop from `at` would be. Stores nothing. */
export async function previewRoute(
  device: string,
  at: Coordinates,
  budgetMeters: number,
  signal?: AbortSignal,
): Promise<TodaysRoute> {
  const params = new URLSearchParams({
    device,
    lat: String(at.lat),
    lng: String(at.lng),
    budget_meters: String(budgetMeters),
  });
  return toRoute(await get<RouteBody>('/v1/routes/preview', params, signal));
}

/** Accept the previewed walk for today. Same inputs, same stops: the server
 *  recomputes rather than trusting ids from the client. */
export async function acceptRoute(
  device: string,
  at: Coordinates,
  budgetMeters: number,
): Promise<TodaysRoute> {
  return toRoute(
    await post<RouteBody>('/v1/routes/today', {
      device,
      lat: at.lat,
      lng: at.lng,
      budget_meters: budgetMeters,
    }),
  );
}

// --- writing -----------------------------------------------------------------

/** What this device is, to the extent it is anybody. */
export type Profile = {
  user_id: string | null;
  display_name: string | null;
  submitted: number;
  unlocked: number;
  /** Consecutive days, ending today or yesterday, with at least one unlock. */
  streak: number;
  /** Which sign-ins are attached, oldest first. Empty means this is still just
   *  a device: everything works, but a new phone would start empty. */
  providers: ('google' | 'apple')[];
};

export type Draft = {
  place_name: string;
  summary: string;
  tags: string[];
  /** ISO date, or null when the person did not say when. */
  happened_at: string | null;
  happened_precision: 'day' | 'year' | null;
  /** ISO date. Nobody reads it before then, the author included. */
  opens_at: string | null;
  media_ids: number[];
  display_name: string | null;
};

/**
 * The chips a submission may carry. Mirrored from `api/write.py`, and
 * `tests/test_api_submit.py` fails if the two stop matching - they had already
 * drifted once, which is how `sport` came to match nothing.
 */
export const SUBMISSION_TAGS = [
  'food',
  'drink',
  'music',
  'art',
  'history',
  'nature',
  'sport',
  'nightlife',
  'work',
  'family',
  'strange',
] as const;

export async function fetchProfile(device: string, signal?: AbortSignal): Promise<Profile> {
  return get<Profile>('/v1/me', new URLSearchParams({ device }), signal);
}

export async function saveDisplayName(device: string, displayName: string): Promise<Profile> {
  const res = await fetch(`${BASE}/v1/me`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ device, display_name: displayName }),
  });
  if (!res.ok) throw new Error(`API ${res.status}`);
  return (await res.json()) as Profile;
}

/**
 * Send one photo or recording ahead of the memory it belongs to, so a 4 MB
 * photo uploads while the person is still typing.
 *
 * Deliberately not behind REQUEST_TIMEOUT_MS: an upload over a phone connection
 * legitimately takes longer than a query, and aborting it at 8s would make the
 * feature unusable on the move.
 */
export async function uploadMedia(
  device: string,
  uri: string,
  mime: string,
  durationSeconds?: number,
): Promise<MediaItem> {
  const form = new FormData();
  form.append('device', device);
  // The server generates the stored name; this one only decides the multipart
  // part's filename, which nothing downstream trusts.
  form.append('file', { uri, name: uri.split('/').pop() ?? 'upload', type: mime } as never);
  if (durationSeconds != null) form.append('duration_seconds', String(Math.round(durationSeconds)));

  const res = await fetch(`${BASE}/v1/media`, { method: 'POST', body: form });
  if (!res.ok) throw new Error(`API ${res.status}`);
  return (await res.json()) as MediaItem;
}

/** File a memory of where you are standing. One coordinate, because it is both
 *  where the person is and where the memory goes. Comes back unlocked, with the
 *  unlock already recorded. */
export async function submitMemory(
  device: string,
  at: Coordinates,
  draft: Draft,
): Promise<LocatedMemory> {
  const memory = await post<Memory>('/v1/memories', { device, ...at, ...draft });
  if (!hasCoordinates(memory)) throw new Error('Submitted memory came back without a place');
  return memory;
}

/** Everything a submission carries except where it was filed and who it is
 *  signed with - the position never moves, and the name is `PUT /v1/me`'s job. */
export type EditDraft = Omit<Draft, 'display_name'>;

/** Change what you filed. Refused with a `sealed` error while the memory is
 *  still sealed - F23 says nobody may read one early to edit it, the author
 *  included, and the server enforces that rather than trusting the app to
 *  simply not ask. */
export async function updateMemory(
  device: string,
  id: number,
  draft: EditDraft,
): Promise<LocatedMemory> {
  const res = await fetch(`${BASE}/v1/memories/${id}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ device, ...draft }),
  });
  if (res.status === 423) throw new Error('sealed');
  if (!res.ok) throw new Error(`API ${res.status}`);
  const memory = (await res.json()) as Memory;
  if (!hasCoordinates(memory)) throw new Error('Edited memory came back without a place');
  return memory;
}

/** Take down something you filed. A real delete - the row, its media files and
 *  its self-minted place are gone, not just hidden the way a report is. */
export async function deleteMemory(device: string, id: number): Promise<void> {
  const res = await fetch(`${BASE}/v1/memories/${id}?${new URLSearchParams({ device })}`, {
    method: 'DELETE',
  });
  if (!res.ok) throw new Error(`API ${res.status}`);
}

// --- signing in ---------------------------------------------------------------

/**
 * Hand a provider's ID token to the server and find out who that makes us. No
 * session token comes back - see docs/10-decisions.md#identity.
 *
 * `displayName` is for Apple, which gives the name to the client on the very
 * first authorization and never again.
 */
export async function signIn(
  provider: 'google' | 'apple',
  device: string,
  idToken: string,
  displayName?: string | null,
): Promise<Profile> {
  return post<Profile>(`/v1/auth/${provider}`, {
    device,
    id_token: idToken,
    display_name: displayName ?? null,
  });
}

/** Unlink this device. Nothing is deleted, and there is no token to revoke. */
export async function signOut(device: string): Promise<Profile> {
  return post<Profile>('/v1/auth/signout', { device });
}
