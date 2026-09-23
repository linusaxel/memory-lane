import assert from 'node:assert/strict';
import { test } from 'node:test';

import { metersBetween, pathMeters } from './region.ts';

test('a point is no distance from itself', () => {
  assert.equal(metersBetween(55.6759, 12.5655, 55.6759, 12.5655), 0);
});

test('a tenth of a degree of latitude is about eleven kilometres', () => {
  // The unlock radius is 150m, so a wrong constant or a degrees/radians slip
  // has to be visible at this scale or the gate opens from the next street.
  const away = metersBetween(55.6759, 12.5655, 55.7759, 12.5655);
  assert.ok(Math.abs(away - 11119) < 20, `expected ~11119m, got ${away}`);
});

test('longitude shrinks with latitude', () => {
  const atEquator = metersBetween(0, 0, 0, 1);
  const upNorth = metersBetween(60, 0, 60, 1);
  assert.ok(upNorth < atEquator / 1.9, 'a degree of longitude halves by 60N');
});

test('a path is the sum of its legs, and a single point walks nowhere', () => {
  const a = { lat: 40.746, lng: -73.9857 };
  const b = { lat: 40.747, lng: -73.9857 };
  const c = { lat: 40.748, lng: -73.9857 };
  const leg = metersBetween(a.lat, a.lng, b.lat, b.lng);
  assert.ok(Math.abs(pathMeters([a, b, c]) - 2 * leg) < 0.5);
  assert.equal(pathMeters([a]), 0);
});
