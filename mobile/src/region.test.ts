import assert from 'node:assert/strict';
import { test } from 'node:test';

import { MAX_RADIUS_KM, MIN_RADIUS_KM, regionToRadiusKm } from './region.ts';

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
