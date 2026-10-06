import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { test } from 'node:test';

import { blocks, inline, plain, serialize, splitRuns } from './story.ts';

// The server's cases (tests/test_story.py): one list, two parsers.
const cases: [string, string][] = JSON.parse(
  readFileSync(new URL('../../tests/fixtures/story.json', import.meta.url), 'utf8'),
);

test('reads the same words the server does', () => {
  for (const [md, words] of cases) assert.equal(plain(md), words, md);
});

test('blocks and serialize round-trip', () => {
  for (const [md] of cases) assert.equal(serialize(blocks(md)), md.trim(), md);
});

test('every kind of block', () => {
  assert.deepEqual(
    blocks('## Head\n\n---\n\n> q\n\n![Cap](photo:7 m right)\n\n![](photo:8)\n\nText'),
    [
      { kind: 'h', text: 'Head' },
      { kind: 'divider' },
      { kind: 'quote', text: 'q' },
      { kind: 'photo', id: 7, size: 'm', place: 'right', caption: 'Cap' },
      { kind: 'photo', id: 8, size: 'l', place: 'center', caption: '' },
      { kind: 'p', text: 'Text' },
    ],
  );
});

test('an empty block is not written', () => {
  assert.equal(serialize([{ kind: 'p', text: ' ' }, { kind: 'divider' }]), '---');
});

test('marks stay in for the editor, out for the reader', () => {
  assert.deepEqual(inline('a **b** *c*'), [
    { text: 'a ' },
    { text: 'b', bold: true },
    { text: ' ' },
    { text: 'c', italic: true },
  ]);
  assert.equal(
    inline('a **b**', true)
      .map((r) => r.text)
      .join(''),
    'a **b**',
  );
});

test('runs split at an offset keep their styles on both sides', () => {
  const runs = inline('ab **cd** e');
  assert.deepEqual(splitRuns(runs, 3), [
    [{ text: 'ab ' }],
    [{ text: 'cd', bold: true }, { text: ' e' }],
  ]);
  assert.deepEqual(splitRuns(runs, 4), [
    [{ text: 'ab ' }, { text: 'c', bold: true }],
    [{ text: 'd', bold: true }, { text: ' e' }],
  ]);
  assert.deepEqual(splitRuns(runs, 0), [[], runs]);
  assert.deepEqual(splitRuns(runs, 99), [runs, []]);
});
