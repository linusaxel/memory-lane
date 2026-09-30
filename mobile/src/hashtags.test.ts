import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { test } from 'node:test';

import { hashtagParts, hashtags, summaryParts } from './hashtags.ts';

// The server's cases (tests/test_hashtags.py): one list, two parsers.
const cases: [string, string[]][] = JSON.parse(
  readFileSync(new URL('../../tests/fixtures/hashtags.json', import.meta.url), 'utf8'),
);

test('reads the same tags the server stores', () => {
  for (const [text, tags] of cases) assert.deepEqual(hashtags(text), tags, text);
});

test('the parts put the text back together, the #words marked', () => {
  for (const [text] of cases) assert.equal(hashtagParts(text).map((p) => p.text).join(''), text);
  assert.deepEqual(hashtagParts('Tacos #food, then home'), [
    { text: 'Tacos ', tag: false },
    { text: '#food', tag: true },
    { text: ', then home', tag: false },
  ]);
});

const STAUNING = { text: 'Thorvald Stauning', url: 'https://en.wikipedia.org/wiki/Thorvald_Stauning' };

test('a linked name is its own run, the rest stays text', () => {
  assert.deepEqual(summaryParts('Thorvald Stauning walked in.', [STAUNING]), [
    { text: 'Thorvald Stauning', tag: false, url: STAUNING.url },
    { text: ' walked in.', tag: false },
  ]);
});

test('only the first use is linked, and #tags still show', () => {
  const parts = summaryParts('#beer with Thorvald Stauning, Thorvald Stauning again', [STAUNING]);
  assert.equal(parts.filter((p) => p.url).length, 1);
  assert.deepEqual(parts[0], { text: '#beer', tag: true });
});

test('a name the text lacks, or one inside an earlier link, is ignored', () => {
  const parts = summaryParts('Christiansborg Palace', [
    { text: 'Christiansborg Palace', url: 'a' },
    { text: 'Palace', url: 'b' },
    { text: 'Amalienborg', url: 'c' },
  ]);
  assert.deepEqual(parts, [{ text: 'Christiansborg Palace', tag: false, url: 'a' }]);
});

test('no links is the summary as before', () => {
  assert.deepEqual(summaryParts('Plain.'), [{ text: 'Plain.', tag: false }]);
});
