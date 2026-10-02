import assert from 'node:assert/strict';
import { test } from 'node:test';

import { countDown, lineOf, walletOf } from './wallet.ts';

const purse = { subscribed: false, welcome_unlocks: 0, keys: 0 };

test('the welcome one shows while there are no keys', () => {
  const w = walletOf({ ...purse, welcome_unlocks: 1 });
  assert.equal(lineOf(w, w.figure), '1 to start');
  assert.equal(w.open, true);
});

test('keys go before the welcome one', () => {
  const w = walletOf({ ...purse, welcome_unlocks: 1, keys: 3 });
  assert.equal(lineOf(w, w.figure), '3 keys');
  assert.equal(w.price, 1);
});

test('one key is singular', () => {
  assert.equal(lineOf(walletOf({ ...purse, keys: 1 }), 1), '1 key');
});

test('none left: closed off the walk, and says the walk is free', () => {
  const w = walletOf(purse);
  assert.equal(w.open, false);
  assert.equal(w.note, "Free on today's walk");
});

test('a subscriber always opens, and pays nothing', () => {
  const w = walletOf({ ...purse, subscribed: true });
  assert.equal(w.open, true);
  assert.equal(w.price, 0);
});

test('a hold takes the key only as the ring completes', () => {
  assert.equal(countDown(3, 1, 0.95), 3);
  assert.equal(countDown(3, 1, 1), 2);
  assert.equal(countDown(3, 0, 1), 3);
});
