/** Map viewport -> the radius_km the API will accept. */

export type Region = {
  latitude: number;
  longitude: number;
  latitudeDelta: number;
  longitudeDelta: number;
};

/** The API rejects radius_km outside this range with a 422. */
export const MIN_RADIUS_KM = 0.1;
export const MAX_RADIUS_KM = 100;

const KM_PER_DEGREE = 111;

/**
 * The API is radius-only (ST_DWithin), so a rectangular viewport is covered by
 * its circumscribing circle.
 *
 * ponytail: over-fetches the corners, and clamps at the API maximum, so a
 * zoomed-right-out map shows the nearest 100km rather than everything on
 * screen. Add a bbox endpoint if that ever looks sparse.
 */
export function regionToRadiusKm(region: Region): number {
  const latKm = region.latitudeDelta * KM_PER_DEGREE;
  // Longitude degrees shrink toward the poles.
  const lngKm =
    region.longitudeDelta * KM_PER_DEGREE * Math.cos((region.latitude * Math.PI) / 180);

  const diagonalKm = Math.hypot(latKm, lngKm);
  const radiusKm = diagonalKm / 2;

  if (!Number.isFinite(radiusKm)) return MIN_RADIUS_KM;
  return Math.min(MAX_RADIUS_KM, Math.max(MIN_RADIUS_KM, radiusKm));
}

/** Great-circle metres between two points. The unlock gate is server-side; this
 *  is only how the map decides which pin looks reachable. */
export function metersBetween(aLat: number, aLng: number, bLat: number, bLng: number): number {
  const toRad = (deg: number) => (deg * Math.PI) / 180;
  const lat1 = toRad(aLat);
  const lat2 = toRad(bLat);
  const dLat = lat2 - lat1;
  const dLng = toRad(bLng - aLng);
  const h =
    Math.sin(dLat / 2) ** 2 + Math.cos(lat1) * Math.cos(lat2) * Math.sin(dLng / 2) ** 2;
  return 2 * 6371000 * Math.asin(Math.sqrt(h));
}

/** Straight-line metres along a path, point to point. What is left of today's
 *  route: a walking distance where the path follows a street leg, not where it
 *  is straight. */
export function pathMeters(points: { lat: number; lng: number }[]): number {
  let total = 0;
  for (let i = 1; i < points.length; i++) {
    total += metersBetween(points[i - 1].lat, points[i - 1].lng, points[i].lat, points[i].lng);
  }
  return total;
}

/** Would these two viewports ask the API the same question?
 *
 * `animateToRegion` fires `onRegionChangeComplete` when it lands, and a
 * programmatic move is indistinguishable there from a pan - so recentring used
 * to fetch twice: once eagerly, once again ~1s later when the camera settled.
 *
 * Comparing the regions field-by-field does not work: the map adjusts the
 * deltas to the screen's aspect ratio, so the region it reports is never quite
 * the one it was given. What matters is whether the *query* would differ, which
 * is the centre and the radius.
 */
export function isSameQuery(a: Region | null, b: Region): boolean {
  if (!a) return false;

  // 25m is well inside the 0.1km minimum radius: a pan this small cannot change
  // what comes back, so skipping it loses nothing.
  const moved = metersBetween(a.latitude, a.longitude, b.latitude, b.longitude);
  const before = regionToRadiusKm(a);
  const after = regionToRadiusKm(b);

  return moved < 25 && Math.abs(before - after) / after < 0.05;
}
