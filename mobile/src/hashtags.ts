// A description's #words are its tags, and the server reads them with the same
// rule (pipeline/tags.py, from_text): `#` then letters, digits or `_`, Latin
// with its accents spelled out, not after a word character or another `#`.
// tests/fixtures/hashtags.json holds both to the same answers. No lookbehind
// and no \p{L}, so there is nothing for Hermes to disagree about.
const WORD = '0-9A-Za-z_À-ÖØ-öø-ɏ';
const LETTER = new RegExp('[A-Za-zÀ-ÖØ-öø-ɏ]');
const BEFORE = new RegExp(`[${WORD}#]`);
const MAX_HASHTAGS = 8;
const MAX_TAG_LENGTH = 50;

type Part = { text: string; tag: boolean };

/** Where each #word sits: [start, end) including the `#`. */
function spans(text: string): [number, number][] {
  const found: [number, number][] = [];
  for (const match of text.matchAll(new RegExp(`#([${WORD}]+)`, 'g'))) {
    const at = match.index ?? 0;
    if (at > 0 && BEFORE.test(text[at - 1])) continue;
    if (!LETTER.test(match[1]) || match[1].length > MAX_TAG_LENGTH) continue;
    found.push([at, at + match[0].length]);
  }
  return found;
}

/** The text cut into runs, the #words marked, for drawing them highlighted. */
export function hashtagParts(text: string): Part[] {
  const parts: Part[] = [];
  let from = 0;
  for (const [start, end] of spans(text)) {
    if (start > from) parts.push({ text: text.slice(from, start), tag: false });
    parts.push({ text: text.slice(start, end), tag: true });
    from = end;
  }
  if (from < text.length) parts.push({ text: text.slice(from), tag: false });
  return parts;
}

/** hashtagParts, with each linked name's first use cut out as its own run.
 *  A name that overlaps an earlier one is left as text. */
export function summaryParts(
  text: string,
  links: { text: string; url: string }[] = [],
): (Part & { url?: string })[] {
  const found = links
    .map((link) => ({ ...link, at: text.indexOf(link.text) }))
    .filter((link) => link.text && link.at >= 0)
    .sort((a, b) => a.at - b.at);
  const parts: (Part & { url?: string })[] = [];
  let from = 0;
  for (const link of found) {
    if (link.at < from) continue;
    parts.push(...hashtagParts(text.slice(from, link.at)));
    parts.push({ text: link.text, tag: false, url: link.url });
    from = link.at + link.text.length;
  }
  parts.push(...hashtagParts(text.slice(from)));
  return parts;
}

/** The tags the server will store for this text. */
export function hashtags(text: string): string[] {
  const seen: string[] = [];
  for (const [start, end] of spans(text)) {
    const tag = text.slice(start + 1, end).toLowerCase();
    if (!seen.includes(tag)) seen.push(tag);
  }
  return seen.slice(0, MAX_HASHTAGS);
}
