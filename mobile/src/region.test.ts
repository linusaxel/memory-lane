import assert from 'node:assert/strict';
import { test } from 'node:test';

import { MAX_RADIUS_KM, MIN_RADIUS_KM, metersBetween, regionToRadiusKm } from './region.ts';

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
