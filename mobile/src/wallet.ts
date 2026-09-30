/** What the steps pill says, and whether standing on a pin can open it
 *  (docs/10, "Three free a day, then steps where you stand"). A .ts so the
 *  gate's `node --test` can import it. */

import type { Profile } from './api.ts';

/** A brisk walk; only used to turn a shortfall into minutes. */
export const STEPS_PER_MINUTE = 100;

type Purse = Pick<Profile, 'subscribed' | 'free_unlocks' | 'steps' | 'steps_per_unlock'>;

export type Wallet = {
  /** The pill's big line, and the number in it that rolls. */
  figure: number;
  unit: string;
  /** The pill's small line. */
  note: string;
  /** Steps still to walk before one opens; 0 when one can. */
  short: number;
  /** How full the next unlock is, 0-1, while short. */
  progress: number;
  spoken: string;
};

export function walletOf(p: Purse): Wallet {
  const steps = p.steps.toLocaleString();
  if (p.free_unlocks > 0) {
    return {
      figure: p.free_unlocks,
      unit: 'free today',
      note: `${steps} steps`,
      short: 0,
      progress: 1,
      spoken: `${p.free_unlocks} free today, ${steps} steps.`,
    };
  }
  if (p.subscribed || p.steps >= p.steps_per_unlock) {
    const opens = Math.floor(p.steps / p.steps_per_unlock);
    const note = p.subscribed ? 'Unlimited where you stand' : `Opens ${opens}`;
    return {
      figure: p.steps,
      unit: 'steps',
      note,
      short: 0,
      progress: 1,
      spoken: `${steps} steps. ${note}.`,
    };
  }
  const short = p.steps_per_unlock - p.steps;
  return {
    figure: short,
    unit: 'to go',
    note: `${steps} steps`,
    short,
    progress: p.steps / p.steps_per_unlock,
    spoken: `${short.toLocaleString()} steps until the next one opens. You have ${steps}.`,
  };
}

/** "620 steps to go · about 7 min walking" */
export function shortfall(short: number): string {
  const minutes = Math.max(1, Math.ceil(short / STEPS_PER_MINUTE));
  return `${short.toLocaleString()} steps to go · about ${minutes} min walking`;
}
