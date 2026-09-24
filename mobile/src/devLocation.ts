/** A position the app is told, instead of one it asks for.
 *
 * Only under `__DEV__` — Metro strips the branch from a release bundle, so this
 * cannot reach a shipped app.
 *
 * It weakens nothing even if it did. The position is already self-reported:
 * `docs/10-decisions.md#the-position-is-self-reported` says the gate stops curl
 * and not a determined spoofer. This makes lying convenient locally; it does not
 * make it possible.
 *
 * What it buys is that `xcrun simctl location booted set` stops being a step you
 * have to remember after every boot — and it works on a physical device, where
 * simctl cannot help at all. Pair it with `python -m pipeline.seed_dev`, which
 * plants memories at exactly this coordinate.
 */

import type { Coordinates } from './api.ts';

/** `EXPO_PUBLIC_DEV_LOCATION=55.67886,12.57586`. Baked in when Metro starts, so
 *  changing it needs a dev-server restart. */
export function devLocation(): Coordinates | null {
  if (!__DEV__) return null;

  const raw = process.env.EXPO_PUBLIC_DEV_LOCATION;
  if (!raw) return null;

  const [lat, lng] = raw.split(',').map((part: string) => Number(part.trim()));
  if (!Number.isFinite(lat) || !Number.isFinite(lng)) {
    console.warn(`EXPO_PUBLIC_DEV_LOCATION is not "lat,lng": ${raw}`);
    return null;
  }
  return { lat, lng };
}
