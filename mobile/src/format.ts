/** How numbers are written on screen.
 *
 * In a .ts and not a .tsx on purpose: the gate runs `node --test` over
 * `mobile/src/*.test.ts`, and node cannot import a .tsx. Every formatter that
 * lived inside a component was therefore untestable, which is how two of them
 * drifted apart and a third shipped an "Invalid Date".
 */

/** One decimal below 10 km, none above: "1.4 km" is a decision and "6181.0 km"
 *  is a spreadsheet. */
export function distance(meters: number, { suffix = '' }: { suffix?: string } = {}): string {
  const km = meters / 1000;
  const body =
    meters < 1000
      ? `${Math.round(meters)} m`
      : `${km < 10 ? km.toFixed(1) : Math.round(km).toLocaleString()} km`;
  return suffix ? `${body} ${suffix}` : body;
}

/** m:ss, or h:mm:ss once there is an hour to show. Clamped at zero because a
 *  recorder can report a negative duration between stop and flush. */
export function duration(seconds: number, { hours = false }: { hours?: boolean } = {}): string {
  const total = Math.max(0, Math.floor(seconds));
  const h = Math.floor(total / 3600);
  const m = Math.floor((total % 3600) / 60);
  const s = String(total % 60).padStart(2, '0');
  if (!hours || h === 0) return `${hours ? m : Math.floor(total / 60)}:${s}`;
  return `${h}:${String(m).padStart(2, '0')}:${s}`;
}

/** How long ago, for the collection list.
 *
 *  Null rather than "Invalid Date" for the unlocks stored before this app
 *  recorded timestamps - they were still earned, they just cannot say when. */
export function when(at: number | undefined, now: number = Date.now()): string | null {
  if (!Number.isFinite(at)) return null;
  const days = Math.floor((now - (at as number)) / 86_400_000);
  if (days <= 0) return 'today';
  if (days === 1) return 'yesterday';
  if (days < 30) return `${days} days ago`;
  return new Date(at as number).toLocaleDateString();
}
