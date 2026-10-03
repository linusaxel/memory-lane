/** The preview's walk, drawn the way Apple Maps draws a route: a blue line
 *  with a darker edge, under the street names (patches/react-native-maps*
 *  moves polylines to MKOverlayLevelAboveRoads). Only the preview has one -
 *  while walking, the next pin hops instead (docs/09-visual-design.md §3a).
 *
 *  Still, because on iOS any Polyline prop change removes and re-adds the
 *  overlay (AIRMapPolyline.m, `update`). theme.ts `solid`, because a Polyline
 *  takes a real colour.
 *
 *  `draw` traces a new walk from you like a loading bar filling, and
 *  `onReach` says how many `stops` its tip has passed, so each pin lands as
 *  the line gets to it (UI.md, "A new walk draws itself"). The patch's
 *  `strokeEnd` moves without rebuilding the overlay.
 */

import { useEffect, useMemo, useRef, useState } from 'react';
import { Easing } from 'react-native';
import { Polyline } from 'react-native-maps';

import type { Coordinates } from './api.ts';
import { metersBetween, simplifyPath } from './region.ts';
import { solid } from './theme.ts';
import { useReduceMotion } from './useBreath.ts';

// One flow, well under 1.5 s. Speeding up a little toward the end: progress
// that accelerates feels fastest, and a slow tail slowest (Harrison et al.,
// "Rethinking the Progress Bar", UIST 2007).
const DRAW_MS = 1200;
const ease = Easing.bezier(0.3, 0.1, 0.7, 0.6);
// A pin lands a beat before the tip, so the two arrive together.
const LEAD_MS = 50;

type Props = {
  path: Coordinates[];
  dark: boolean;
  /** Trace it in from the start. */
  draw?: boolean;
  /** The walk's stops in order, for onReach. */
  stops?: Coordinates[];
  onReach?: (count: number) => void;
  /** A new walk is on its way: this one fades back. */
  dim?: boolean;
};

export default function RouteLine({ path, dark, draw, stops = [], onReach, dim }: Props) {
  const reduceMotion = useReduceMotion();
  const { line, lineCasing } = solid(dark);
  // Memoised: a fresh array makes react-native-maps rebuild the overlay.
  const { coordinates, along } = useMemo(() => {
    // 12m: wider than the hop between two sidewalks, narrower than a block.
    const points = simplifyPath(path, 12);
    const along = [0];
    for (let i = 1; i < points.length; i++) {
      const [a, b] = [points[i - 1], points[i]];
      along.push(along[i - 1] + metersBetween(a.lat, a.lng, b.lat, b.lng));
    }
    return {
      coordinates: points.map((at) => ({ latitude: at.lat, longitude: at.lng })),
      along,
    };
  }, [path]);
  const total = along[along.length - 1] || 1;

  // How far along the line each stop is, as a fraction: where it sits nearest
  // the line, searched on from the stop before, so a loop that passes stop 1
  // again on the way home still reaches it first.
  const stopAt = useMemo(() => {
    let from = 0;
    return stops.map((stop) => {
      // Flat metres around the stop: a few km, so the curve does not matter.
      const k = Math.cos((stop.lat * Math.PI) / 180);
      const xy = coordinates.map((at) => [
        (at.longitude - stop.lng) * 111320 * k,
        (at.latitude - stop.lat) * 111320,
      ]);
      const hits = xy.slice(1).map(([bx, by], i) => {
        const [ax, ay] = xy[i];
        const [dx, dy] = [bx - ax, by - ay];
        const f = Math.max(0, Math.min(1, -(ax * dx + ay * dy) / (dx * dx + dy * dy || 1)));
        return { i, f, off: i < from ? Infinity : Math.hypot(ax + dx * f, ay + dy * f) };
      });
      const nearest = Math.min(...hits.map((hit) => hit.off));
      // The first pass about as near as the nearest, not a later one.
      const hit = hits.find((h) => h.off <= nearest + 15);
      if (!hit) return 0;
      from = hit.i;
      return (along[hit.i] + (along[hit.i + 1] - along[hit.i]) * hit.f) / total;
    });
  }, [stops, coordinates, along, total]);

  const reachRef = useRef(onReach);
  reachRef.current = onReach;
  const [drawn, setDrawn] = useState(draw ? 0 : 1);
  useEffect(() => {
    if (!draw || reduceMotion) {
      setDrawn(1);
      reachRef.current?.(stopAt.length);
      return;
    }
    const start = Date.now();
    let told = -1;
    let frame = requestAnimationFrame(function tick() {
      const t = Math.min(1, (Date.now() - start) / DRAW_MS);
      setDrawn(ease(t));
      const ahead = ease(Math.min(1, t + LEAD_MS / DRAW_MS));
      const count = stopAt.filter((at) => at <= ahead).length;
      if (count !== told) reachRef.current?.((told = count));
      if (t < 1) frame = requestAnimationFrame(tick);
    });
    return () => cancelAnimationFrame(frame);
  }, [stopAt, draw, reduceMotion]);

  // Nothing at 0: a round cap would sit there as a dot.
  if (coordinates.length < 2 || drawn === 0) return null;
  // #RRGGBB + 66: the same colour at 40%.
  const fade = (hex: string) => (dim ? `${hex}66` : hex);
  return (
    <>
      <Polyline
        coordinates={coordinates}
        strokeEnd={drawn}
        strokeWidth={9}
        strokeColor={fade(lineCasing)}
        lineCap="round"
        lineJoin="round"
      />
      <Polyline
        coordinates={coordinates}
        strokeEnd={drawn}
        strokeWidth={6}
        strokeColor={fade(line)}
        lineCap="round"
        lineJoin="round"
      />
    </>
  );
}
