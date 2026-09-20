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
