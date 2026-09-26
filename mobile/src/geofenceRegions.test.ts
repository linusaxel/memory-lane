import assert from 'node:assert/strict';
import { test } from 'node:test';

import type { LocatedMemory } from './api.ts';
import { memoriesToWatch, regionsFor } from './geofenceRegions.ts';

let nextId = 1;

function memory(opts: {
  locked?: boolean;
  radius?: number | null;
  lat?: number;
  lng?: number;
  name?: string;
}): LocatedMemory {
  return {
    id: nextId++,
    locked: opts.locked ?? true,
    unlock_radius_meters: opts.radius === undefined ? 20 : opts.radius,
    place: {
      name: opts.name ?? 'Vega',
      coordinates: { lat: opts.lat ?? 55.6759, lng: opts.lng ?? 12.5655 },
    },
  } as unknown as LocatedMemory;
}

test('an unlocked memory is nothing to walk to', () => {
  assert.deepEqual(memoriesToWatch([memory({ locked: false })]), []);
});

test('a locked memory is watched', () => {
  const m = memory({});
  assert.deepEqual(memoriesToWatch([m]), [m]);
});

test('iOS refuses more than 20 regions, so watching stops there', () => {
  const memories = Array.from({ length: 25 }, () => memory({}));
  assert.equal(memoriesToWatch(memories).length, 20);
});

test('a region carries the memory id, its coordinates, and its own radius', () => {
  const m = memory({ radius: 175, lat: 1, lng: 2 });
  assert.deepEqual(regionsFor([m]), [
    {
      identifier: String(m.id),
      latitude: 1,
      longitude: 2,
      radius: 175,
      notifyOnEnter: true,
      notifyOnExit: false,
    },
  ]);
});

test('a gate smaller than iOS can watch is watched at the smallest it can', () => {
  assert.equal(regionsFor([memory({ radius: 20 })])[0].radius, 100);
  assert.equal(regionsFor([memory({ radius: null })])[0].radius, 100);
});
