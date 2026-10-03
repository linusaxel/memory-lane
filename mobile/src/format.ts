/** How numbers are written on screen.
 *
 * In a .ts and not a .tsx on purpose: the gate runs `node --test` over
 * `mobile/src/*.test.ts`, and node cannot import a .tsx. Every formatter that
 * lived inside a component was therefore untestable, which is how two of them
 * drifted apart and a third shipped an "Invalid Date".
 */

import type { ContentRef } from './api.ts';

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

/** A walk's day, "Tue, Sep 22". Parsed as a local date: `new Date('2026-09-22')`
 *  is UTC midnight, which is the 21st anywhere west of Greenwich. */
export function walkDate(routeDate: string, locale?: string): string {
  const [y, m, d] = routeDate.split('-').map(Number);
  return new Date(y, m - 1, d).toLocaleDateString(locale, {
    weekday: 'short',
    month: 'short',
    day: 'numeric',
  });
}

const WORDS = ['no', 'one', 'two', 'three', 'four', 'five', 'six', 'seven', 'eight', 'nine', 'ten'];

/** A small count in words, as prose writes it: "today's three free". */
export function count(n: number): string {
  return WORDS[n] ?? n.toLocaleString();
}

const MONTHS = [
  'January',
  'February',
  'March',
  'April',
  'May',
  'June',
  'July',
  'August',
  'September',
  'October',
  'November',
  'December',
];

/** When it happened, as much as the source said: the year to set large, and
 *  the day or month beside it. A decade is "1930s". Read from the ISO string,
 *  not a Date, which would be the day before anywhere west of Greenwich. */
export function happened(
  at: string | null | undefined,
  precision: string | null | undefined,
): { year: string; within: string | null } | null {
  if (!at) return null;
  const [y, m, d] = at.split('-').map(Number);
  if (!Number.isFinite(y)) return null;
  if (precision === 'decade') return { year: `${Math.floor(y / 10) * 10}s`, within: null };
  const month = MONTHS[m - 1];
  if (precision === 'day' && month) return { year: String(y), within: `${d} ${month}` };
  if (precision === 'month' && month) return { year: String(y), within: month };
  return { year: String(y), within: null };
}

/** What the button out to the source says: where it goes, never "Open the
 *  source" (docs/09 part 10). `spoken` is for VoiceOver, where "Watch from
 *  12:04" out of context is a time of day. */
export function sourceAction(content: ContentRef): { text: string; spoken: string } {
  const at = content.timestamp_start;
  const host = content.url.replace(/^https?:\/\/(www\.)?/, '').split('/')[0];
  const text =
    content.kind === 'video'
      ? at != null
        ? `Watch from ${duration(at, { hours: true })}`
        : /youtube\.com|youtu\.be/.test(host)
          ? 'Watch on YouTube'
          : 'Watch the video'
      : content.kind === 'book'
        ? 'Read it in the book'
        : content.kind === 'newspaper'
          ? content.published_year
            ? `Read the ${content.published_year} article`
            : 'Read the article'
          : content.kind === 'archive'
            ? `Read it at ${content.source?.name ?? host}`
            : 'Read the original';
  return { text, spoken: at != null && content.kind === 'video' ? `${text} into the video` : text };
}
