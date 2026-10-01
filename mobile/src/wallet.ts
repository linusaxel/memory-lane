/** What the steps pill says, and whether standing on a pin can open it
 *  (docs/10, "Pick one to start, then where you stand"). A .ts so the
 *  gate's `node --test` can import it. */

import type { Profile } from './api.ts';

/** A brisk walk; only used to turn a shortfall into minutes. */
export const STEPS_PER_MINUTE = 100;

type Purse = Pick<Profile, 'subscribed' | 'welcome_unlocks' | 'steps' | 'steps_per_unlock'>;

export type Wallet = {
  /** The pill's big line, and the number in it that rolls. */
  figure: number;
  unit: string;
  /** The pill's small line; empty for none. */
  note: string;
  /** Steps still to walk before one opens; 0 when one can. */
  short: number;
  /** How full the next unlock is, 0-1, while short. */
  progress: number;
  /** What a hold where you stand takes off `figure`. */
  price: number;
  spoken: string;
};

export function walletOf(p: Purse): Wallet {
  const steps = p.steps.toLocaleString();
  // Standing there, steps go before the welcome one, so it shows only while
  // the steps cannot pay.
  if (p.welcome_unlocks > 0 && !p.subscribed && p.steps < p.steps_per_unlock) {
    return {
      figure: p.welcome_unlocks,
      unit: 'to start',
      note: `${steps} steps`,
      short: 0,
      progress: 1,
      price: 1,
      spoken: `${p.welcome_unlocks} to start, ${steps} steps.`,
    };
  }
  if (p.subscribed || p.steps >= p.steps_per_unlock) {
    // The balance is enough on its own: no "Opens 4" under it (the founder).
    const note = p.subscribed ? 'Unlimited where you stand' : '';
    return {
      figure: p.steps,
      unit: 'steps',
      note,
      short: 0,
      progress: 1,
      price: p.subscribed ? 0 : p.steps_per_unlock,
      spoken: note ? `${steps} steps. ${note}.` : `${steps} steps.`,
    };
  }
  const short = p.steps_per_unlock - p.steps;
  return {
    figure: short,
    unit: 'to go',
    note: `${steps} steps`,
    short,
    progress: p.steps / p.steps_per_unlock,
    price: 0,
    spoken: `${short.toLocaleString()} steps until the next one opens. You have ${steps}.`,
  };
}

/** The figure `t` (0-1) of the way through a hold: down in tenths with the
 *  ring, so a price of steps ticks and a free one drops only as it fills. */
export function countDown(figure: number, price: number, t: number): number {
  return figure - Math.floor((price * Math.floor(t * 10)) / 10);
}

/** "620 steps to go · about 7 min walking" */
export function shortfall(short: number): string {
  const minutes = Math.max(1, Math.ceil(short / STEPS_PER_MINUTE));
  return `${short.toLocaleString()} steps to go · about ${minutes} min walking`;
}
