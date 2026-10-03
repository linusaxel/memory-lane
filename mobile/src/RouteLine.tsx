/** The preview's walk, drawn the way Apple Maps draws a route: a blue line
 *  with a darker edge, under the street names (patches/react-native-maps*
 *  moves polylines to MKOverlayLevelAboveRoads). Only the preview has one -
 *  while walking, the next pin hops instead (docs/09-visual-design.md §3a).
 *
 *  Still, because on iOS any Polyline prop change removes and re-adds the
 *  overlay (AIRMapPolyline.m, `update`). theme.ts `solid`, because a Polyline
 *  takes a real colour.
 *
 *  `draw` grows a new walk from you along its length (UI.md, Motion). A stroke
 *  can't animate natively, so each step is a longer slice: STEPS rebuilds of
 *  the fill only, and the edge lands once the line is whole.
 */

import { useEffect, useMemo, useState } from 'react';
import { Polyline } from 'react-native-maps';

import type { Coordinates } from './api.ts';
import { metersBetween, simplifyPath } from './region.ts';
import { solid } from './theme.ts';
import { useReduceMotion } from './useBreath.ts';

const DRAW_MS = 600;
// ponytail: one overlay rebuild per step; fewer steps if a phone drops frames.
const STEPS = 24;

type Props = {
  path: Coordinates[];
  dark: boolean;
  /** Grow it in from the start, then call onDrawn. */
  draw?: boolean;
  onDrawn?: () => void;
  /** A new walk is on its way: this one fades back. */
  dim?: boolean;
};

export default function RouteLine({ path, dark, draw, onDrawn, dim }: Props) {
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

  const [step, setStep] = useState(draw ? 0 : STEPS);
  useEffect(() => {
    if (!draw || reduceMotion) {
      setStep(STEPS);
      if (draw) onDrawn?.();
      return;
    }
    setStep(0);
    const start = Date.now();
    let frame = requestAnimationFrame(function tick() {
      const t = Math.min(1, (Date.now() - start) / DRAW_MS);
      // Ease out: quick from you, settling as it reaches the far end.
      setStep(Math.round((1 - (1 - t) ** 3) * STEPS));
      if (t < 1) frame = requestAnimationFrame(tick);
      else onDrawn?.();
    });
    return () => cancelAnimationFrame(frame);
    // A new walk is a new path; onDrawn changing is not a reason to redraw.
  }, [coordinates, draw, reduceMotion]);

  const shown = useMemo(() => {
    if (step >= STEPS) return coordinates;
    const reach = (step / STEPS) * along[along.length - 1];
    const i = along.findIndex((meters) => meters > reach);
    if (i < 1) return coordinates;
    const [a, b] = [coordinates[i - 1], coordinates[i]];
    const k = (reach - along[i - 1]) / (along[i] - along[i - 1] || 1);
    return [
      ...coordinates.slice(0, i),
      {
        latitude: a.latitude + (b.latitude - a.latitude) * k,
        longitude: a.longitude + (b.longitude - a.longitude) * k,
      },
    ];
  }, [coordinates, along, step]);

  // #RRGGBB + 66: the same colour at 40%.
  const fade = (hex: string) => (dim ? `${hex}66` : hex);
  // Keyed on whole: both remount together, so the edge is added under the
  // fill rather than on top of it.
  const whole = step >= STEPS;
  return (
    <>
      {whole && (
        <Polyline
          key="edge"
          coordinates={shown}
          strokeWidth={9}
          strokeColor={fade(lineCasing)}
          lineCap="round"
          lineJoin="round"
        />
      )}
      {shown.length > 1 && (
        <Polyline
          key={`fill-${whole}`}
          coordinates={shown}
          strokeWidth={6}
          strokeColor={fade(line)}
          lineCap="round"
          lineJoin="round"
        />
      )}
    </>
  );
}
