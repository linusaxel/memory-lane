import assert from 'node:assert/strict';
import { test } from 'node:test';

import { shortfall, walletOf } from './wallet.ts';

const purse = { subscribed: false, free_unlocks: 0, steps: 0, steps_per_unlock: 1000 };

test('free ones come first, whatever the balance', () => {
  const w = walletOf({ ...purse, free_unlocks: 2, steps: 4210 });
  assert.equal(w.figure, 2);
  assert.equal(w.unit, 'free today');
  assert.equal(w.short, 0);
});

test('none free: the balance, and how many it opens', () => {
  const w = walletOf({ ...purse, steps: 4210 });
  assert.equal(w.figure, 4210);
  assert.equal(w.note, 'Opens 4');
  assert.equal(w.short, 0);
});

test('exactly the price is enough', () => {
  assert.equal(walletOf({ ...purse, steps: 1000 }).short, 0);
});

test('short: what is left to walk, and how far along', () => {
  const w = walletOf({ ...purse, steps: 400 });
  assert.equal(w.figure, 600);
  assert.equal(w.unit, 'to go');
  assert.equal(w.short, 600);
  assert.equal(w.progress, 0.4);
});

test('a subscriber is never short where they stand', () => {
  const w = walletOf({ ...purse, subscribed: true, steps: 0 });
  assert.equal(w.short, 0);
  assert.equal(w.unit, 'steps');
});

test('the shortfall in minutes rounds up, and never says 0 min', () => {
  assert.equal(shortfall(620), '620 steps to go · about 7 min walking');
  assert.equal(shortfall(5), '5 steps to go · about 1 min walking');
});
