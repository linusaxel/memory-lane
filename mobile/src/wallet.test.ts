import assert from 'node:assert/strict';
import { test } from 'node:test';

import { countDown, shortfall, walletOf } from './wallet.ts';

const purse = { subscribed: false, welcome_unlocks: 0, steps: 0, steps_per_unlock: 1000 };

test('the welcome one shows while the steps cannot pay', () => {
  const w = walletOf({ ...purse, welcome_unlocks: 1, steps: 400 });
  assert.equal(w.figure, 1);
  assert.equal(w.unit, 'to start');
  assert.equal(w.short, 0);
});

test('steps that can pay go before the welcome one', () => {
  const w = walletOf({ ...purse, welcome_unlocks: 1, steps: 4210 });
  assert.equal(w.unit, 'steps');
  assert.equal(w.price, 1000);
});

test('none free: the balance alone', () => {
  const w = walletOf({ ...purse, steps: 4210 });
  assert.equal(w.figure, 4210);
  assert.equal(w.note, '');
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

test('a hold pays the price in tenths, and a free one only at the end', () => {
  assert.equal(countDown(4210, 1000, 0.35), 3910);
  assert.equal(countDown(4210, 1000, 1), 3210);
  assert.equal(countDown(3, 1, 0.95), 3);
  assert.equal(countDown(3, 1, 1), 2);
});
