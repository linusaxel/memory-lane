import assert from 'node:assert/strict';
import { test } from 'node:test';

import { CLASSES, STAGES, classOf, stageNow, stageOf, toNext } from './collector.ts';

test('a stage opens at its count and the next waits', () => {
  assert.equal(stageOf(0), 0);
  assert.equal(stageOf(2), 0);
  assert.equal(stageOf(3), 1);
  assert.equal(stageOf(5000), 7);
  assert.equal(toNext(3), 5);
  assert.equal(toNext(250), null);
});

test('a rank never goes down', () => {
  assert.equal(stageNow(3, 2), 3);
  assert.equal(stageNow(undefined, 8), 2);
  assert.equal(stageNow(1, 15), 3);
});

test('no pick is the Wayfinder', () => {
  assert.equal(classOf(undefined).id, 'wayfinder');
  assert.equal(classOf('nonsense').id, 'wayfinder');
  assert.equal(classOf('pilgrim').id, 'pilgrim');
});

test('every class has a rank for every stage', () => {
  for (const c of CLASSES) assert.equal(c.ranks.length, STAGES.length, c.id);
});
