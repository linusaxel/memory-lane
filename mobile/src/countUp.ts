/** The values a number passes through as it rolls from what the journal last
 *  showed to what it is now (UI.md, the journal header). At most `maxTicks`,
 *  each one up, the last exactly `to`. Nothing when it did not grow: a number
 *  that fell, a memory hidden, just shows. */
export function roll(from: number, to: number, maxTicks = 8): number[] {
  if (to <= from) return [];
  const n = Math.min(to - from, maxTicks);
  return Array.from({ length: n }, (_, i) => Math.round(from + ((to - from) * (i + 1)) / n));
}
