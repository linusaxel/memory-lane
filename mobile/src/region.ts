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
