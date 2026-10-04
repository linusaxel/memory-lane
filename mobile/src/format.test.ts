import assert from 'node:assert/strict';
import { test } from 'node:test';

import {
  count,
  distance,
  duration,
  happened,
  sourceAction,
  walkDate,
  when,
  wikiSummaryUrl,
} from './format.ts';

test('metres below a kilometre, kilometres above', () => {
  assert.equal(distance(420), '420 m');
  assert.equal(distance(999), '999 m');
  assert.equal(distance(1400), '1.4 km');
});

test('one decimal below 10 km and none above', () => {
  // The rule ReachBanner stated and MemorySheet did not follow: a memory opened
  // from the collection used to render "6181.0 km away".
  assert.equal(distance(9900), '9.9 km');
  assert.equal(distance(6_189_000), '6,189 km');
});

test('a suffix is appended, not baked in', () => {
  assert.equal(distance(420, { suffix: 'away' }), '420 m away');
});

test('durations are m:ss until there is an hour', () => {
  assert.equal(duration(41), '0:41');
  assert.equal(duration(125), '2:05');
  assert.equal(duration(3661, { hours: true }), '1:01:01');
  // Without hours, minutes keep counting past sixty - a recording, not a video.
  assert.equal(duration(3661), '61:01');
});

test('a negative duration clamps rather than rendering a minus', () => {
  assert.equal(duration(-3), '0:00');
});

test('a missing timestamp is null, not Invalid Date', () => {
  // Real bug: unlocks stored before timestamps existed rendered "Invalid Date"
  // in the collection. They were still earned.
  assert.equal(when(undefined), null);
  assert.equal(when(Number.NaN), null);
});

test('recent unlocks read as words, older ones as a date', () => {
  const now = Date.UTC(2026, 8, 20, 12);
  const days = (n: number) => now - n * 86_400_000;
  assert.equal(when(days(0), now), 'today');
  assert.equal(when(days(1), now), 'yesterday');
  assert.equal(when(days(5), now), '5 days ago');
  assert.notEqual(when(days(400), now), '400 days ago');
});

test('a clock skewed into the future still says today', () => {
  const now = Date.UTC(2026, 8, 20, 12);
  assert.equal(when(now + 60_000, now), 'today');
});

test("a walk's date is the day it was walked, in any timezone", () => {
  assert.equal(walkDate('2026-09-22', 'en-US'), 'Tue, Sep 22');
});

test('small counts in words, large ones in digits', () => {
  assert.equal(count(3), 'three');
  assert.equal(count(12), '12');
});

test('when it happened says only as much as the source did', () => {
  assert.deepEqual(happened('1936-06-17', 'day'), { year: '1936', within: '17 June' });
  assert.deepEqual(happened('1936-06-01', 'month'), { year: '1936', within: 'June' });
  assert.deepEqual(happened('1936-01-01', 'year'), { year: '1936', within: null });
  assert.deepEqual(happened('1936-01-01', 'decade'), { year: '1930s', within: null });
  assert.deepEqual(happened('1936-01-01', null), { year: '1936', within: null });
  assert.equal(happened(null, 'day'), null);
});

test('the source button says where it goes', () => {
  const ref = {
    id: 1,
    title: null,
    url: 'https://www.youtube.com/watch?v=abc&t=724',
    timestamp_start: 724,
    source: null,
    kind: 'video',
    published_year: null,
  };
  assert.deepEqual(sourceAction(ref), {
    text: 'Watch from 12:04',
    spoken: 'Watch from 12:04 into the video',
  });
  assert.equal(sourceAction({ ...ref, timestamp_start: null }).text, 'Watch on YouTube');
  const page = { ...ref, timestamp_start: null, url: 'https://historiskatlas.dk/Kanonkuglehuset' };
  assert.equal(sourceAction({ ...page, kind: 'book' }).text, 'Read it in the book');
  assert.equal(
    sourceAction({ ...page, kind: 'newspaper', published_year: 1856 }).text,
    'Read the 1856 article',
  );
  assert.equal(sourceAction({ ...page, kind: 'archive' }).text, 'Read it at historiskatlas.dk');
  assert.equal(
    sourceAction({
      ...page,
      kind: 'archive',
      source: { name: 'Historisk Atlas', url: null, icon_url: null },
    }).text,
    'Read it at Historisk Atlas',
  );
  assert.equal(sourceAction({ ...page, kind: null }).text, 'Read the original');
});

test('a Wikipedia link previews from its summary, in its own language', () => {
  assert.equal(
    wikiSummaryUrl('https://en.wikipedia.org/wiki/Leonora_Christina_Ulfeldt'),
    'https://en.wikipedia.org/api/rest_v1/page/summary/Leonora_Christina_Ulfeldt',
  );
  assert.equal(
    wikiSummaryUrl('https://da.m.wikipedia.org/wiki/K%C3%B8benhavn#Historie'),
    'https://da.wikipedia.org/api/rest_v1/page/summary/K%C3%B8benhavn',
  );
  assert.equal(wikiSummaryUrl('https://www.youtube.com/watch?v=abc'), null);
  assert.equal(wikiSummaryUrl('https://www.gutenberg.org/ebooks/1'), null);
});
