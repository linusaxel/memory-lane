import assert from 'node:assert/strict';
import { test } from 'node:test';

import { groupByLocation, groupLabel } from './cluster.ts';
import type { LocatedMemory } from './api.ts';

function memory(id: number, name: string, lat: number, lng: number): LocatedMemory {
  return {
    id,
    summary: `memory ${id}`,
    place: { id, name, coordinates: { lat, lng }, precision_meters: 50 },
    distance_meters: 0,
    content: { id: 1, title: null, url: 'https://x', timestamp_start: 0, timestamp_url: 'https://x' },
    tags: [],
    confidence: 'high',
  } as LocatedMemory;
}

// The real one: the Times Square centroid the model falls back to.
const TS_LAT = 40.7589;
const TS_LNG = -73.9851;

test('memories on one centroid collapse to a single group', () => {
  const stacked = [
    memory(1, 'Gotham Comedy Club', TS_LAT, TS_LNG),
    memory(2, "Caroline's", TS_LAT, TS_LNG),
    memory(3, 'New York Comedy Club', TS_LAT, TS_LNG),
  ];
  const groups = groupByLocation(stacked);
  assert.equal(groups.length, 1);
  assert.equal(groups[0].memories.length, 3);
});

test('genuinely distinct addresses stay apart', () => {
  const groups = groupByLocation([
    memory(1, 'Katz', 40.7223, -73.9874),
    memory(2, 'Gotham', 40.7431, -73.9967),
  ]);
  assert.equal(groups.length, 2);
});

test('coordinates closer than the model’s own precision merge', () => {
  // ~1m apart. The model calls 50m "exact", so this is noise, not a distinction.
  const groups = groupByLocation([
    memory(1, 'A', 40.75891, -73.98511),
    memory(2, 'B', 40.75892, -73.98512),
  ]);
  assert.equal(groups.length, 1);
});

test('a lone memory keeps its own place name as the label', () => {
  const [group] = groupByLocation([memory(1, 'Katz', 40.7223, -73.9874)]);
  assert.equal(groupLabel(group), 'Katz');
});

test('a stack of different venues says how many', () => {
  const [group] = groupByLocation([
    memory(1, 'Gotham', TS_LAT, TS_LNG),
    memory(2, "Caroline's", TS_LAT, TS_LNG),
  ]);
  assert.equal(groupLabel(group), '2 places here');
});

test('repeats of one venue are counted, not renamed', () => {
  const [group] = groupByLocation([
    memory(1, 'Gotham Comedy Club', TS_LAT, TS_LNG),
    memory(2, 'Gotham Comedy Club', TS_LAT, TS_LNG),
  ]);
  assert.equal(groupLabel(group), 'Gotham Comedy Club (2)');
});

test('denser groups sort last so they paint on top', () => {
  const groups = groupByLocation([
    memory(1, 'Stacked A', TS_LAT, TS_LNG),
    memory(2, 'Stacked B', TS_LAT, TS_LNG),
    memory(3, 'Alone', 40.7223, -73.9874),
  ]);
  assert.equal(groups[groups.length - 1].memories.length, 2);
});

test('keys are stable across calls so markers are not remounted', () => {
  const input = [memory(1, 'Katz', 40.7223, -73.9874)];
  assert.equal(groupByLocation(input)[0].key, groupByLocation(input)[0].key);
});

test('no memories, no groups', () => {
  assert.deepEqual(groupByLocation([]), []);
});
