import assert from 'node:assert/strict';
import { test } from 'node:test';

import { count, distance, duration, walkDate, when } from './format.ts';

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

test("a walk's date is the day it was walked, in any timezone", () => {
  assert.equal(walkDate('2026-09-22', 'en-US'), 'Tue, Sep 22');
});

test('small counts in words, large ones in digits', () => {
  assert.equal(count(3), 'three');
  assert.equal(count(12), '12');
});
