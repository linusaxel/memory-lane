import assert from 'node:assert/strict';
import { test } from 'node:test';

import { distance, duration, sealOpensAt, walkDate, when } from './format.ts';

test('metres below a kilometre, kilometres above', () => {
  assert.equal(distance(420), '420 m');
  assert.equal(distance(999), '999 m');
  assert.equal(distance(1400), '1.4 km');
});

test('one decimal below 10 km and none above', () => {
  // The rule ReachBanner stated and MemorySheet did not follow: a memory opened
  // from the collection used to render "6181.0 km away".
  assert.equal(distance(9900), '9.9 km');
  assert.equal(distance(6_189_000), '6,189 km');
});

test('a suffix is appended, not baked in', () => {
  assert.equal(distance(420, { suffix: 'away' }), '420 m away');
});

test('durations are m:ss until there is an hour', () => {
  assert.equal(duration(41), '0:41');
  assert.equal(duration(125), '2:05');
  assert.equal(duration(3661, { hours: true }), '1:01:01');
  // Without hours, minutes keep counting past sixty - a recording, not a video.
  assert.equal(duration(3661), '61:01');
});

test('a negative duration clamps rather than rendering a minus', () => {
  assert.equal(duration(-3), '0:00');
});

test('a missing timestamp is null, not Invalid Date', () => {
  // Real bug: unlocks stored before timestamps existed rendered "Invalid Date"
  // in the collection. They were still earned.
  assert.equal(when(undefined), null);
  assert.equal(when(Number.NaN), null);
});

test('recent unlocks read as words, older ones as a date', () => {
  const now = Date.UTC(2026, 8, 20, 12);
  const days = (n: number) => now - n * 86_400_000;
  assert.equal(when(days(0), now), 'today');
  assert.equal(when(days(1), now), 'yesterday');
  assert.equal(when(days(5), now), '5 days ago');
  assert.notEqual(when(days(400), now), '400 days ago');
});

test('a clock skewed into the future still says today', () => {
  const now = Date.UTC(2026, 8, 20, 12);
  assert.equal(when(now + 60_000, now), 'today');
});

const NOW = new Date('2026-09-21T12:00:00Z');

test('a seal needs a year still to come', () => {
  assert.equal(sealOpensAt('2041', NOW), '2041-01-01');
  assert.equal(sealOpensAt('2027', NOW), '2027-01-01');
});

test('a year that has already begun is not a seal', () => {
  // The server treats a date that has come as no date at all, so letting one
  // through here would post a readable memory to somebody who asked to seal it.
  assert.equal(sealOpensAt('2026', NOW), null);
  assert.equal(sealOpensAt('1994', NOW), null);
});

test('half a year is not a year', () => {
  // The state the bug lived in: "Nobody until" chosen, year left empty.
  assert.equal(sealOpensAt('', NOW), null);
  assert.equal(sealOpensAt('20', NOW), null);
  assert.equal(sealOpensAt('20x1', NOW), null);
  assert.equal(sealOpensAt('  ', NOW), null);
});

test('a year is read around its spaces', () => {
  assert.equal(sealOpensAt(' 2041 ', NOW), '2041-01-01');
});

test("a walk's date is the day it was walked, in any timezone", () => {
  assert.equal(walkDate('2026-09-22', 'en-US'), 'Tue, Sep 22');
});
