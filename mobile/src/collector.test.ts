import assert from 'node:assert/strict';
import { test } from 'node:test';

import { CLASSES, STAGES, stageOf, toNext } from './collector.ts';

test('a stage opens at its count and the next waits', () => {
  assert.equal(stageOf(0), 0);
  assert.equal(stageOf(4), 0);
  assert.equal(stageOf(5), 1);
  assert.equal(stageOf(5000), 7);
  assert.equal(toNext(5), 10);
  assert.equal(toNext(1000), null);
});

test('every class has a rank for every stage', () => {
  for (const c of CLASSES) assert.equal(c.ranks.length, STAGES.length, c.id);
});
