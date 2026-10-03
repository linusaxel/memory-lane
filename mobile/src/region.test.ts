import assert from 'node:assert/strict';
import { test } from 'node:test';

import { around, metersBetween, pathMeters, simplifyPath } from './region.ts';

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

test('a hop between sidewalks is smoothed, a street corner is kept', () => {
  // 200m north up one sidewalk, 15m east across the avenue, 200m north up the
  // other, then 200m east round a corner.
  const north = 200 / 111320;
  const east = (m: number) => m / (111320 * Math.cos((40.75 * Math.PI) / 180));
  const at = (dn: number, de: number) => ({ lat: 40.75 + dn, lng: -73.98 + de });
  const path = [
    at(0, 0),
    at(north, 0),
    at(north, east(15)),
    at(2 * north, east(15)),
    at(2 * north, east(215)),
  ];
  const drawn = simplifyPath(path, 12);
  assert.deepEqual(drawn, [path[0], path[3], path[4]]);
});

test('around keeps you in the middle and the stop inside the frame', () => {
  const you = { lat: 40.748, lng: -73.985 };
  const r = around(you, [{ lat: 40.758, lng: -73.98 }], 0.002);
  assert.equal(r.latitude, you.lat);
  assert.equal(r.longitude, you.lng);
  // The stop sits well inside half the frame, clear of the overlays at the edges.
  assert.ok(0.01 / (r.latitudeDelta / 2) < 0.6);
  assert.ok(0.005 / (r.longitudeDelta / 2) < 0.6);
  assert.equal(around(you, [you], 0.002).latitudeDelta, 0.002);
});
