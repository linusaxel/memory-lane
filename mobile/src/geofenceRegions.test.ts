import assert from 'node:assert/strict';
import { test } from 'node:test';

import type { LocatedMemory } from './api.ts';
import {
  liveSurprise,
  mayNotify,
  maySurprise,
  memoriesToWatch,
  regionsFor,
} from './geofenceRegions.ts';

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

const HOUR = 60 * 60 * 1000;
const NOTHING = { last: 0, byId: {} };

test('the first memory you walk into notifies', () => {
  assert.deepEqual(mayNotify('1', 10 * HOUR, NOTHING), {
    last: 10 * HOUR,
    byId: { '1': 10 * HOUR },
  });
});

test('a cluster entered at once notifies once', () => {
  const sent = mayNotify('1', 10 * HOUR, NOTHING)!;
  assert.equal(mayNotify('2', 10 * HOUR + 1000, sent), null);
  assert.notEqual(mayNotify('2', 11 * HOUR, sent), null);
});

test('dithering on one boundary notifies once a day', () => {
  const sent = mayNotify('1', 10 * HOUR, NOTHING)!;
  assert.equal(mayNotify('1', 20 * HOUR, sent), null);
  assert.notEqual(mayNotify('1', 35 * HOUR, sent), null);
});

test('a day-old alert is forgotten, so the record stays small', () => {
  const sent = mayNotify('1', 10 * HOUR, NOTHING)!;
  assert.deepEqual(Object.keys(mayNotify('2', 40 * HOUR, sent)!.byId), ['2']);
});

test('a surprise waits for a day the app was not opened', () => {
  assert.equal(maySurprise('2026-10-07', '2026-10-07'), false);
  assert.equal(maySurprise('2026-10-06', '2026-10-07'), true);
  assert.equal(maySurprise(null, '2026-10-07'), true);
});

test('a surprise is gone once it expires', () => {
  const surprise = { memoryId: 1, place: 'Vega', expiresAt: '2026-10-07T12:30:00Z' };
  assert.equal(liveSurprise(surprise, Date.parse('2026-10-07T12:29:00Z')), surprise);
  assert.equal(liveSurprise(surprise, Date.parse('2026-10-07T12:31:00Z')), null);
});
