import assert from 'node:assert/strict';
import { test } from 'node:test';

import type { LocatedMemory } from './api.ts';
import { memoriesToWatch, regionsFor } from './geofenceRegions.ts';

let nextId = 1;

function memory(opts: {
  locked?: boolean;
  opens_at?: string | null;
  radius?: number | null;
  lat?: number;
  lng?: number;
  name?: string;
}): LocatedMemory {
  return {
    id: nextId++,
    locked: opts.locked ?? true,
    opens_at: opts.opens_at ?? null,
    unlock_radius_meters: opts.radius ?? 150,
    place: {
      name: opts.name ?? 'Vega',
      coordinates: { lat: opts.lat ?? 55.6759, lng: opts.lng ?? 12.5655 },
    },
  } as unknown as LocatedMemory;
}

test('an unlocked memory is nothing to walk to', () => {
  assert.deepEqual(memoriesToWatch([memory({ locked: false })]), []);
});

test('a sealed memory does not open by walking there, so it is not watched', () => {
  assert.deepEqual(
    memoriesToWatch([memory({ opens_at: '2099-01-01' })]),
    [],
  );
});

test('a locked, unsealed memory is watched', () => {
  const m = memory({});
  assert.deepEqual(memoriesToWatch([m]), [m]);
});

test('iOS refuses more than 20 regions, so watching stops there', () => {
  const memories = Array.from({ length: 25 }, () => memory({}));
  assert.equal(memoriesToWatch(memories).length, 20);
});

test('a region carries the memory id, its coordinates, and its own radius', () => {
  const m = memory({ radius: 75, lat: 1, lng: 2 });
  assert.deepEqual(regionsFor([m]), [
    {
      identifier: String(m.id),
      latitude: 1,
      longitude: 2,
      radius: 75,
      notifyOnEnter: true,
      notifyOnExit: false,
    },
  ]);
});

test('a missing server radius falls back rather than watching an unbounded region', () => {
  const m = memory({ radius: null });
  assert.equal(regionsFor([m])[0].radius, 150);
});
