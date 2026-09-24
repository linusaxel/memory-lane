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

/** A region centred on `center`, wide enough to show every point in `points`
 *  clear of the overlays at the edges. Walk pins the camera on the person, so
 *  "show me the next stop" zooms out around them rather than refitting. */
export function around(
  center: { lat: number; lng: number },
  points: { lat: number; lng: number }[],
  minDelta: number,
): Region {
  let lat = 0;
  let lng = 0;
  for (const p of points) {
    lat = Math.max(lat, Math.abs(p.lat - center.lat));
    lng = Math.max(lng, Math.abs(p.lng - center.lng));
  }
  // 2 for either side of the centre, and 1.8 for the pill, the tab bar and
  // "+ Add", which a pin must not land under: at 1.4 a stop to the north-east
  // sat under the button.
  return {
    latitude: center.lat,
    longitude: center.lng,
    latitudeDelta: Math.max(lat * 3.6, minDelta),
    longitudeDelta: Math.max(lng * 3.6, minDelta),
  };
}

export type Inset = { top: number; right: number; bottom: number; left: number };

/** Where on a `width` x `height` north-up map showing `region` the arrow to
 *  `target` sits, and which way it points in degrees clockwise from up; null
 *  while `target` is inside the map less `inset`. The arrow is where the line
 *  from the centre to the target leaves that box.
 *
 *  ponytail: degrees are treated as linear across the screen, which Mercator
 *  is not; at street scale the error is under a pixel. */
export function edgeArrow(
  region: Region,
  target: { lat: number; lng: number },
  width: number,
  height: number,
  inset: Inset,
): { x: number; y: number; angle: number } | null {
  const dx = ((target.lng - region.longitude) / region.longitudeDelta) * width;
  const dy = (-(target.lat - region.latitude) / region.latitudeDelta) * height;
  const cx = width / 2;
  const cy = height / 2;
  const right = width - inset.right - cx;
  const left = inset.left - cx;
  const down = height - inset.bottom - cy;
  const up = inset.top - cy;
  if (dx >= left && dx <= right && dy >= up && dy <= down) return null;
  const s = Math.min(
    dx > 0 ? right / dx : dx < 0 ? left / dx : Infinity,
    dy > 0 ? down / dy : dy < 0 ? up / dy : Infinity,
  );
  return { x: cx + dx * s, y: cy + dy * s, angle: (Math.atan2(dx, -dy) * 180) / Math.PI };
}
