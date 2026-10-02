/** What the keys pill says, and whether standing on a pin can open it
 *  (docs/10, "Keys open a lock, and today's walk is free"). A .ts so the
 *  gate's `node --test` can import it. */

import type { Profile } from './api.ts';

type Purse = Pick<Profile, 'subscribed' | 'welcome_unlocks' | 'keys'>;

export type Wallet = {
  /** The pill's number, and the one that rolls. */
  figure: number;
  /** The figure counts the welcome one, not keys. */
  starting: boolean;
  /** What the pill says under the figure; empty for none. */
  note: string;
  /** Standing on a pin off today's walk opens it. A stop of today's walk
   *  always does. */
  open: boolean;
  /** What a hold where you stand takes off `figure`, off the walk. */
  price: number;
  spoken: string;
};

/** "1 to start", "1 key", "3 keys". */
export function lineOf(w: Pick<Wallet, 'starting'>, figure: number): string {
  if (w.starting) return `${figure} to start`;
  return `${figure} ${figure === 1 ? 'key' : 'keys'}`;
}

// Standing there, a key goes before the welcome one, so it shows only while
// there are no keys.
function starting(p: Purse): boolean {
  return p.welcome_unlocks > 0 && !p.subscribed && p.keys === 0;
}

export function walletOf(p: Purse): Wallet {
  if (starting(p)) {
    const line = lineOf({ starting: true }, p.welcome_unlocks);
    return { figure: p.welcome_unlocks, starting: true, note: '', open: true, price: 1, spoken: `${line}.` };
  }
  const keys = { figure: p.keys, starting: false };
  const line = lineOf(keys, p.keys);
  if (p.subscribed) {
    const note = 'Unlimited where you stand';
    return { ...keys, note, open: true, price: 0, spoken: `${line}. ${note}.` };
  }
  if (p.keys > 0) return { ...keys, note: '', open: true, price: 1, spoken: `${line}.` };
  const note = "Free on today's walk";
  return { ...keys, note, open: false, price: 0, spoken: `No keys. ${note}.` };
}

/** The figure at the end of a hold: down by the price only as the ring
 *  completes, never part way. */
export function countDown(figure: number, price: number, t: number): number {
  return t >= 1 ? figure - price : figure;
}
