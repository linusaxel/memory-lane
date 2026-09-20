import assert from 'node:assert/strict';
import { test } from 'node:test';

import { inUnlockOrder, type Unlocked } from './unlocked.ts';

function entry(id: number, unlockedAt?: number) {
  return { id, unlocked_at: unlockedAt } as unknown as Unlocked[number];
}

test('the newest unlock comes first', () => {
  const stored: Unlocked = {
    1: entry(1, 1000),
    2: entry(2, 3000),
    3: entry(3, 2000),
  };

  assert.deepEqual(
    inUnlockOrder(stored).map((m) => m.id),
    [2, 3, 1],
  );
});

test('an unlock stored before timestamps existed still appears', () => {
  // Real case: memories unlocked by an earlier build have no unlocked_at, and
  // arithmetic on undefined used to render them as "Invalid Date". They were
  // still earned - they sort last rather than vanishing.
  const stored: Unlocked = { 1: entry(1), 2: entry(2, 5000) };

  assert.deepEqual(
    inUnlockOrder(stored).map((m) => m.id),
    [2, 1],
  );
});
