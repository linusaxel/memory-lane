import assert from 'node:assert/strict';
import { test } from 'node:test';

import type { LocatedMemory } from './api.ts';
import type { MemoryGroup } from './cluster.ts';
import { nearestLocked, reachOf } from './reach.ts';

const HERE = { lat: 55.6759, lng: 12.5655 };

/** Nothing earned. Most of these tests are about the gate, not the collection. */
const NONE: ReadonlySet<number> = new Set();

let nextId = 1;

/** `memoryAt` is where the memories actually are, which is not always the point
 *  the marker is drawn on - that is the whole of what a looser cluster does. */
function group(
  lat: number,
  lng: number,
  locked: boolean[],
  radius = 150,
  memoryAt: [number, number] = [lat, lng],
): MemoryGroup {
  return {
    key: `${lat},${lng}`,
    lat,
    lng,
    spanMeters: 0,
    memories: locked.map(
      (isLocked) =>
        ({
          id: nextId++,
          locked: isLocked,
          unlock_radius_meters: isLocked ? radius : null,
          place: { coordinates: { lat: memoryAt[0], lng: memoryAt[1] } },
        }) as unknown as LocatedMemory,
    ),
  };
}

/** ~0.0009 degrees of latitude is ~100m; ~0.0027 is ~300m; ~0.009 is ~1km. */
const NEAR: [number, number] = [HERE.lat + 0.0009, HERE.lng];
const MIDDLE: [number, number] = [HERE.lat + 0.0027, HERE.lng];
const FAR: [number, number] = [HERE.lat + 0.009, HERE.lng];

test('a group with nothing locked and nothing earned is plain', () => {
  assert.equal(reachOf(group(...FAR, [false, false]), HERE, NONE), 'plain');
  assert.equal(reachOf(group(...FAR, [false]), null, NONE), 'plain');
});

test('a group this device has earned is stamped, wherever you stand', () => {
  // The walk is what buys the stamp, so it has to survive walking away.
  const g = group(...FAR, [false]);
  const earned = new Set([g.memories[0].id]);
  assert.equal(reachOf(g, HERE, earned), 'stamped');
  assert.equal(reachOf(g, null, earned), 'stamped');
});

test('one earned memory stamps the marker it shares', () => {
  const g = group(...FAR, [false, false]);
  assert.equal(reachOf(g, HERE, new Set([g.memories[1].id])), 'stamped');
});

test('something still locked outranks something already earned', () => {
  // A marker with anything left to open is an invitation, not a souvenir.
  const g = group(...NEAR, [false, true]);
  assert.equal(reachOf(g, HERE, new Set([g.memories[0].id])), 'unlockable');
});

test('one locked memory under a marker locks the marker', () => {
  assert.equal(reachOf(group(...NEAR, [false, true]), HERE, NONE), 'unlockable');
});

test('no position is not the same as being near', () => {
  assert.equal(reachOf(group(...NEAR, [true]), null, NONE), 'locked');
});

test('a few minutes away is warm, a kilometre away is not', () => {
  assert.equal(reachOf(group(...MIDDLE, [true]), HERE, NONE), 'warm');
  assert.equal(reachOf(group(...FAR, [true]), HERE, NONE), 'locked');
});

test('the radius comes from the server, not from the app', () => {
  // The same 100m pin, told two different radii. If this stops mattering, the
  // client has started deciding the gate. 50m puts it outside the gate but
  // still inside the walk; 500m puts it inside the gate.
  assert.equal(reachOf(group(...NEAR, [true], 50), HERE, NONE), 'warm');
  assert.equal(reachOf(group(...NEAR, [true], 500), HERE, NONE), 'unlockable');
});

test('reach is measured to the memories, not to the point they are drawn on', () => {
  // A loosely clustered group is drawn on a rounded coordinate that can sit a
  // long way from everything under it. Measuring to the marker would say "walk
  // a kilometre" while you are standing on the thing.
  const offset = group(...FAR, [true], 150, NEAR);
  assert.equal(reachOf(offset, HERE, NONE), 'unlockable');
});

test('the nearest lock is the closest locked group', () => {
  const near = group(HERE.lat + 0.004, HERE.lng, [true]);
  const far = group(...FAR, [true]);
  const found = nearestLocked([far, near], HERE, NONE);

  assert.equal(found?.group, near);
  assert.ok(found && found.meters > 400 && found.meters < 500, `got ${found?.meters}`);
});

test('nothing to walk to when something is already in reach', () => {
  assert.equal(nearestLocked([group(...FAR, [true]), group(...NEAR, [true])], HERE, NONE), null);
});

test('plain groups are not somewhere to walk to', () => {
  assert.equal(nearestLocked([group(...FAR, [false])], HERE, NONE), null);
});

test('a stamped group is not somewhere to walk to either', () => {
  // Otherwise the pill reads "Nearest locked - 40 m" about something you have
  // already stood on and read.
  const g = group(...FAR, [false]);
  assert.equal(nearestLocked([g], HERE, new Set([g.memories[0].id])), null);
});

test('a lock on another continent is not a hint', () => {
  // Copenhagen, with a corpus in New York. "Nearest locked memory 6,181 km"
  // is a fact about the corpus, not somewhere to walk - the empty-state card
  // is what should speak instead.
  const faraway = group(40.7128, -74.006, [true]);
  assert.equal(nearestLocked([faraway], HERE, NONE), null);
});

test('a lock at the edge of a long day out still counts', () => {
  const nearEdge = group(HERE.lat + 0.2, HERE.lng, [true]); // ~22km
  assert.ok(nearestLocked([nearEdge], HERE, NONE));
});
