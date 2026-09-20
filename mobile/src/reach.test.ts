import assert from 'node:assert/strict';
import { test } from 'node:test';

import type { LocatedMemory } from './api.ts';
import type { MemoryGroup } from './cluster.ts';
import { nearestLocked, reachOf } from './reach.ts';

const HERE = { lat: 55.6759, lng: 12.5655 };

function group(lat: number, lng: number, locked: boolean[], radius = 150): MemoryGroup {
  return {
    key: `${lat},${lng}`,
    lat,
    lng,
    memories: locked.map(
      (isLocked, i) =>
        ({
          id: i,
          locked: isLocked,
          unlock_radius_meters: isLocked ? radius : null,
          place: { coordinates: { lat, lng } },
        }) as unknown as LocatedMemory,
    ),
  };
}

/** ~0.0009 degrees of latitude is ~100m; ~0.009 is ~1km. */
const NEAR: [number, number] = [HERE.lat + 0.0009, HERE.lng];
const FAR: [number, number] = [HERE.lat + 0.009, HERE.lng];

test('a group with nothing locked is open wherever you stand', () => {
  assert.equal(reachOf(group(...FAR, [false, false]), HERE), 'open');
  assert.equal(reachOf(group(...FAR, [false]), null), 'open');
});

test('one locked memory under a marker locks the marker', () => {
  assert.equal(reachOf(group(...NEAR, [false, true]), HERE), 'unlockable');
});

test('no position is not the same as being near', () => {
  assert.equal(reachOf(group(...NEAR, [true]), null), 'locked');
});

test('a kilometre away is out of reach', () => {
  assert.equal(reachOf(group(...FAR, [true]), HERE), 'locked');
});

test('the radius comes from the server, not from the app', () => {
  // The same 100m pin, told two different radii. If this stops mattering, the
  // client has started deciding the gate.
  assert.equal(reachOf(group(...NEAR, [true], 50), HERE), 'locked');
  assert.equal(reachOf(group(...NEAR, [true], 500), HERE), 'unlockable');
});

test('the nearest lock is the closest locked group', () => {
  const near = group(HERE.lat + 0.004, HERE.lng, [true]);
  const far = group(...FAR, [true]);
  const found = nearestLocked([far, near], HERE);

  assert.equal(found?.group, near);
  assert.ok(found && found.meters > 400 && found.meters < 500, `got ${found?.meters}`);
});

test('nothing to walk to when something is already in reach', () => {
  assert.equal(nearestLocked([group(...FAR, [true]), group(...NEAR, [true])], HERE), null);
});

test('open groups are not somewhere to walk to', () => {
  assert.equal(nearestLocked([group(...FAR, [false])], HERE), null);
});

test('a lock on another continent is not a hint', () => {
  // Copenhagen, with a corpus in New York. "Nearest locked memory 6,181 km"
  // is a fact about the corpus, not somewhere to walk - the empty-state card
  // is what should speak instead.
  const faraway = group(40.7128, -74.006, [true]);
  assert.equal(nearestLocked([faraway], HERE), null);
});

test('a lock at the edge of a long day out still counts', () => {
  const nearEdge = group(HERE.lat + 0.2, HERE.lng, [true]); // ~22km
  assert.ok(nearestLocked([nearEdge], HERE));
});
