import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { test } from 'node:test';

import { hashtagParts, hashtags } from './hashtags.ts';

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
