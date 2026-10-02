import assert from 'node:assert/strict';
import { test } from 'node:test';

import type { LocatedMemory } from './api.ts';
import type { MemoryGroup } from './cluster.ts';
import { approachOf, isFar, reachOf } from './reach.ts';

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

test('the approach ring is full the moment the gate can open', () => {
  assert.equal(approachOf(150, 150), 1);
  assert.equal(approachOf(20, 150), 1);
  assert.equal(approachOf(0, 150), 1);
});

test('the approach ring is empty until the walk is worth starting', () => {
  // Three radii is where a pin stops being "too far" and starts being "a
  // short walk away", so the ring should have nothing in it until then.
  assert.equal(approachOf(450, 150), 0);
  assert.equal(approachOf(6000, 150), 0);
});

test('the approach ring rises over the walk in', () => {
  const half = approachOf(300, 150);
  assert.ok(half > 0.49 && half < 0.51, `expected about half, got ${half}`);
  assert.ok(approachOf(200, 150) > half, 'closer must read as fuller');
  assert.ok(approachOf(400, 150) < half, 'further must read as emptier');
});

test('no position is no progress, not full progress', () => {
  // The figure underneath renders an em dash in this case; a ring showing
  // itself full because it divided by nothing would be a lie about the gate.
  assert.equal(approachOf(null, 150), 0);
  assert.equal(approachOf(100, 0), 0);
});

test('a locked pin past a short walk is far; opened ones and no position never are', () => {
  const twoKm: [number, number] = [HERE.lat + 0.018, HERE.lng];
  assert.equal(isFar(group(...twoKm, [true]), HERE), true);
  assert.equal(isFar(group(...MIDDLE, [true]), HERE), false);
  assert.equal(isFar(group(...twoKm, [false]), HERE), false);
  assert.equal(isFar(group(...twoKm, [true]), null), false);
});
