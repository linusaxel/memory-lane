import assert from 'node:assert/strict';
import { test } from 'node:test';

import {
  CLASSES,
  STAGES,
  classOf,
  rankInto,
  stageNow,
  stageOf,
  wants,
  wantsWords,
} from './collector.ts';

test('a stage opens when both counts reach it', () => {
  assert.equal(stageOf(0, 0), 0);
  assert.equal(stageOf(4, 0), 0, 'lockets alone open nothing');
  assert.equal(stageOf(4, 1), 1);
  assert.equal(stageOf(3, 9), 1, 'nor do filed memories alone');
  assert.equal(stageOf(5000, 20), 7);
  assert.deepEqual(wants(1, 4, 1), { lockets: 4, filed: 1 });
  assert.deepEqual(wants(0, 4, 0), { lockets: 0, filed: 1 });
  assert.equal(wants(7, 250, 20), null);
  assert.equal(wantsWords({ lockets: 36, filed: 1 }), '36 more lockets and 1 memory of yours');
  assert.equal(wantsWords({ lockets: 0, filed: 2 }), '2 memories of yours');
});

test('a rank never goes down', () => {
  assert.equal(stageNow(3, 2, 0), 3);
  assert.equal(stageNow(undefined, 8, 2), 2);
  assert.equal(stageNow(1, 15, 3), 3);
});

test('no pick is the Wayfinder', () => {
  assert.equal(classOf(undefined).id, 'wayfinder');
  assert.equal(classOf('nonsense').id, 'wayfinder');
  assert.equal(classOf('pilgrim').id, 'pilgrim');
});

test('every class has a rank for every stage', () => {
  for (const c of CLASSES) assert.equal(c.ranks.length, STAGES.length, c.id);
});

test('the bar to the next rank', () => {
  assert.equal(rankInto(1, 3, 1), 0);
  assert.equal(rankInto(1, 5.5, 2), 0.5);
  assert.equal(rankInto(1, 8, 1), 0, 'the scale further behind decides');
  assert.equal(rankInto(3, 2, 0), 0, 'a kept rank above the counts starts empty, never negative');
  assert.equal(rankInto(7, 300, 0), 1);
});
