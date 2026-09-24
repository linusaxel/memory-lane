/** Map maths: the viewport shape, and metres between points. */

export type Region = {
  latitude: number;
  longitude: number;
  latitudeDelta: number;
  longitudeDelta: number;
};

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

/** The path with every point dropped that sits within `tolerance` metres of
 *  the line between its neighbours (Douglas-Peucker). For drawing only: OSM
 *  maps Manhattan's sidewalks as their own ways, so a street route hops from
 *  one to the other at every crosswalk, and drawn as-is each hop is a notch. */
export function simplifyPath<T extends { lat: number; lng: number }>(
  points: T[],
  tolerance: number,
): T[] {
  if (points.length < 3) return points;
  const k = Math.cos((points[0].lat * Math.PI) / 180);
  const xy = points.map((p) => [p.lng * 111320 * k, p.lat * 111320]);
  const keep = new Array<boolean>(points.length).fill(false);
  keep[0] = keep[points.length - 1] = true;
  const stack: [number, number][] = [[0, points.length - 1]];
  while (stack.length) {
    const [a, b] = stack.pop()!;
    const [ax, ay] = xy[a];
    const dx = xy[b][0] - ax;
    const dy = xy[b][1] - ay;
    const len2 = dx * dx + dy * dy;
    let far = -1;
    let farthest = tolerance;
    for (let i = a + 1; i < b; i++) {
      const along = len2 ? ((xy[i][0] - ax) * dx + (xy[i][1] - ay) * dy) / len2 : 0;
      const t = Math.max(0, Math.min(1, along));
      const off = Math.hypot(xy[i][0] - ax - t * dx, xy[i][1] - ay - t * dy);
      if (off > farthest) {
        far = i;
        farthest = off;
      }
    }
    if (far < 0) continue;
    keep[far] = true;
    stack.push([a, far], [far, b]);
  }
  return points.filter((_, i) => keep[i]);
}
