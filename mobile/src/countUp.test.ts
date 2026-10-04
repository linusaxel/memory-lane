import assert from 'node:assert/strict';
import { test } from 'node:test';

import { roll } from './countUp.ts';

test('nothing rolls when nothing grew', () => {
  assert.deepEqual(roll(5, 5), []);
  assert.deepEqual(roll(5, 3), []);
});

test('a small gain ticks once a step', () => {
  assert.deepEqual(roll(3, 6), [4, 5, 6]);
});

test('a big gain is capped, climbs every tick and lands on the value', () => {
  const ticks = roll(4210, 6000);
  assert.equal(ticks.length, 8);
  assert.equal(ticks.at(-1), 6000);
  ticks.forEach((v, i) => assert.ok(v > (i ? ticks[i - 1] : 4210)));
});
