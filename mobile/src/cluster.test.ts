import assert from 'node:assert/strict';
import { test } from 'node:test';

import { CLUSTER_SPAN_M, groupByLocation, groupLabel, layerOf, precisionFor } from './cluster.ts';
import type { Layer, LocatedMemory } from './api.ts';

function memory(
  id: number,
  name: string,
  lat: number,
  lng: number,
  layer: Layer = 'historical',
): LocatedMemory {
  return {
    id,
    summary: `memory ${id}`,
    place: { id, name, coordinates: { lat, lng }, precision_meters: 50 },
    distance_meters: 0,
    content: {
      id: 1,
      title: null,
      url: 'https://x',
      timestamp_start: 0,
      timestamp_url: 'https://x',
      source: null,
    },
    tags: [],
    confidence: 'high',
    layer,
    locked: false,
    unlock_radius_meters: null,
    author: null,
    media: [],
    media_count: 0,
    anniversary: false,
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

test('a shared centroid has no span; scattered places do', () => {
  const [stacked] = groupByLocation([
    memory(1, 'Gotham', TS_LAT, TS_LNG),
    memory(2, "Caroline's", TS_LAT, TS_LNG),
  ]);
  assert.equal(stacked.spanMeters, 0);

  // Katz and Gotham are ~2.5km apart; at a city grid they share one cell.
  const [clustered] = groupByLocation(
    [memory(1, 'Katz', 40.7223, -73.9874), memory(2, 'Gotham', 40.7431, -73.9967)],
    1,
  );
  assert.ok(clustered.spanMeters > CLUSTER_SPAN_M, `got ${clustered.spanMeters}`);
});

test('a looser grid merges what a street grid keeps apart', () => {
  // A grid buckets, so what merges depends on the cell edges as well as the
  // distance: these two sit either side of one at 2dp and share a cell at 1dp.
  const apart = [memory(1, 'Katz', 40.7223, -73.9874), memory(2, 'Gotham', 40.7431, -73.9967)];
  assert.equal(groupByLocation(apart, 4).length, 2);
  assert.equal(groupByLocation(apart, 1).length, 1);
});

test('precision follows the viewport in bands, not continuously', () => {
  // Two deltas inside one band must give one precision, or the groups memo
  // rebuilds on every pan.
  assert.equal(precisionFor(0.01), precisionFor(0.04));
  assert.equal(precisionFor(0.01), 4);
  assert.equal(precisionFor(0.09), 3); // FALLBACK_REGION, ~10km
  assert.equal(precisionFor(1), 2);
  assert.equal(precisionFor(40), 1);
});

test('the coarsest grid still separates cities', () => {
  // New York and Copenhagen must never share a pin, however far you zoom out.
  const groups = groupByLocation(
    [memory(1, 'Katz', 40.7223, -73.9874), memory(2, 'Vega', 55.6688, 12.5426)],
    1,
  );
  assert.equal(groups.length, 2);
});

test('a group wears its layer only when the whole stack agrees', () => {
  const [mine] = groupByLocation([memory(1, 'My corner', TS_LAT, TS_LNG, 'stranger')]);
  assert.equal(layerOf(mine), 'stranger');

  // A submission filed outside Katz shares Katz's cell. Claiming the stack for
  // either layer would be a lie the sheet immediately contradicts.
  const [mixed] = groupByLocation([
    memory(1, 'Katz', TS_LAT, TS_LNG),
    memory(2, 'My corner', TS_LAT, TS_LNG, 'stranger'),
  ]);
  assert.equal(layerOf(mixed), 'historical');
});
