import assert from 'node:assert/strict';
import { test } from 'node:test';

import {
  MAX_RADIUS_KM,
  around,
  edgeArrow,
  MIN_RADIUS_KM,
  isSameQuery,
  metersBetween,
  pathMeters,
  regionToRadiusKm,
  simplifyPath,
} from './region.ts';

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

test('a city-sized viewport asks for a few kilometres', () => {
  const km = regionToRadiusKm({
    latitude: 40.75,
    longitude: -73.98,
    latitudeDelta: 0.05,
    longitudeDelta: 0.05,
  });
  assert.ok(km > 1 && km < 10, `expected a few km, got ${km}`);
});

test('a continent-sized viewport clamps to the API maximum', () => {
  // Without the clamp this is ~2000km and the API answers 422.
  const km = regionToRadiusKm({
    latitude: 40,
    longitude: -100,
    latitudeDelta: 40,
    longitudeDelta: 60,
  });
  assert.equal(km, MAX_RADIUS_KM);
});

test('a degenerate zero-size viewport still asks for a valid radius', () => {
  const km = regionToRadiusKm({
    latitude: 0,
    longitude: 0,
    latitudeDelta: 0,
    longitudeDelta: 0,
  });
  assert.equal(km, MIN_RADIUS_KM);
});

test('the same viewport asks the same question', () => {
  const here = { latitude: 55.6759, longitude: 12.5655, latitudeDelta: 0.01, longitudeDelta: 0.01 };
  assert.equal(isSameQuery(here, here), true);
});

test('the aspect-adjusted region the map reports back still counts as the same', () => {
  // animateToRegion never lands on exactly the region it was given - the map
  // fits the deltas to the screen. If this stops being tolerated, recentring
  // fetches twice again.
  const asked = { latitude: 55.6759, longitude: 12.5655, latitudeDelta: 0.01, longitudeDelta: 0.01 };
  const landed = { ...asked, latitude: 55.67591, longitudeDelta: 0.0102 };
  assert.equal(isSameQuery(asked, landed), true);
});

test('a real pan asks a new question', () => {
  const here = { latitude: 55.6759, longitude: 12.5655, latitudeDelta: 0.01, longitudeDelta: 0.01 };
  const away = { ...here, latitude: 55.6859 };
  assert.equal(isSameQuery(here, away), false);
});

test('zooming without moving asks a new question', () => {
  const here = { latitude: 55.6759, longitude: 12.5655, latitudeDelta: 0.01, longitudeDelta: 0.01 };
  const out = { ...here, latitudeDelta: 0.05, longitudeDelta: 0.05 };
  assert.equal(isSameQuery(here, out), false);
});

test('nothing fetched yet is never the same question', () => {
  const here = { latitude: 55.6759, longitude: 12.5655, latitudeDelta: 0.01, longitudeDelta: 0.01 };
  assert.equal(isSameQuery(null, here), false);
});

const VIEW = { latitude: 40.748, longitude: -73.985, latitudeDelta: 0.01, longitudeDelta: 0.01 };
const NONE = { top: 0, right: 0, bottom: 0, left: 0 };

test('no arrow for a stop already on screen', () => {
  assert.equal(edgeArrow(VIEW, { lat: 40.749, lng: -73.984 }, 400, 800, NONE), null);
});

test('a stop due east is an arrow on the right edge, pointing right', () => {
  const arrow = edgeArrow(VIEW, { lat: 40.748, lng: -73.97 }, 400, 800, NONE);
  assert.ok(arrow);
  assert.equal(arrow.x, 400);
  assert.equal(arrow.y, 400);
  assert.equal(arrow.angle, 90);
});

test('a stop north-west leaves by whichever edge the line crosses first', () => {
  // Twice as far north as west, on a screen twice as tall as wide: the corner.
  const arrow = edgeArrow(VIEW, { lat: 40.758, lng: -73.995 }, 400, 800, NONE);
  assert.ok(arrow);
  assert.ok(Math.abs(arrow.x) < 1e-9 && Math.abs(arrow.y) < 1e-9);
  // Up and to the left, steeper than 45 because the screen is tall.
  assert.ok(Math.abs(arrow.angle - (Math.atan2(-1, 2) * 180) / Math.PI) < 1e-9);
});

test('the inset is the edge: a stop under the pill still gets its arrow', () => {
  const underPill = { lat: 40.7445, lng: -73.985 };
  assert.equal(edgeArrow(VIEW, underPill, 400, 800, NONE), null);
  const arrow = edgeArrow(VIEW, underPill, 400, 800, { ...NONE, bottom: 160 });
  assert.ok(arrow);
  assert.equal(arrow.y, 640);
  assert.equal(arrow.angle, 180);
});

test('around keeps you in the middle and the stop inside the frame', () => {
  const you = { lat: 40.748, lng: -73.985 };
  const r = around(you, [{ lat: 40.758, lng: -73.98 }], 0.002);
  assert.equal(r.latitude, you.lat);
  assert.equal(r.longitude, you.lng);
  assert.equal(edgeArrow(r, { lat: 40.758, lng: -73.98 }, 400, 800, NONE), null);
  // The worst case, a stop out on the diagonal, stays clear of "+ Add" (top
  // right, down to ~110pt on a 400x800 map) and the pill (bottom ~90pt).
  const corner = { lat: 40.758, lng: -73.975 };
  const framed = around(you, [corner], 0.002);
  const clear = { top: 150, right: 0, bottom: 130, left: 0 };
  assert.equal(edgeArrow(framed, corner, 400, 800, clear), null);
  assert.equal(around(you, [you], 0.002).latitudeDelta, 0.002);
});
