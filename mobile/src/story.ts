// A story is a little markdown, all of it in `summary` (docs/10, "A story has
// a little markdown"): blocks split by a blank line, and inside a block only
// **bold** and *italic*. A summary with none of it - every extracted memory -
// is one paragraph, read as before. api/story.py plain() mirrors plain() here;
// tests/fixtures/story.json holds both to the same answers.

export type Size = 's' | 'm' | 'l';
export type Place = 'left' | 'center' | 'right';
export type Block =
  | { kind: 'p' | 'h' | 'quote'; text: string }
  | { kind: 'divider' }
  | { kind: 'photo'; id: number; size: Size; place: Place; caption: string };

export type Run = { text: string; bold?: boolean; italic?: boolean; mark?: boolean };

const PHOTO = /^!\[(.*)\]\(photo:(\d+)(?: ([sml]))?(?: (left|center|right))?\)$/s;
// A mark hugs its words, so "2 * 3 * 4" stays arithmetic.
const MARK = /\*\*([^\s*](?:.*?[^\s*])?)\*\*|\*([^\s*](?:.*?[^\s*])?)\*/g;

export function blocks(md: string): Block[] {
  return md
    .trim()
    .split(/\n\s*\n/)
    .filter((chunk) => chunk.trim())
    .map((chunk): Block => {
      const line = chunk.trim();
      const photo = line.match(PHOTO);
      if (photo) {
        return {
          kind: 'photo',
          id: Number(photo[2]),
          size: (photo[3] as Size) ?? 'l',
          place: (photo[4] as Place) ?? 'center',
          caption: photo[1],
        };
      }
      if (/^-{3,}$/.test(line)) return { kind: 'divider' };
      if (line.startsWith('## ')) return { kind: 'h', text: line.slice(3) };
      if (line.startsWith('>')) return { kind: 'quote', text: line.replace(/^> ?/gm, '') };
      return { kind: 'p', text: line };
    });
}

export function serialize(story: Block[]): string {
  return story
    .map((b) => {
      if (b.kind === 'divider') return '---';
      if (b.kind === 'photo') return `![${b.caption.replace(/\n/g, ' ')}](photo:${b.id} ${b.size} ${b.place})`;
      const text = b.text.trim();
      if (!text) return '';
      if (b.kind === 'h') return `## ${text.replace(/\n/g, ' ')}`;
      if (b.kind === 'quote') return text.replace(/^/gm, '> ');
      return text;
    })
    .filter(Boolean)
    .join('\n\n');
}

/** A block's text cut into styled runs. With `marks`, the asterisks stay in
 *  as runs of their own, for the editor to draw faint. */
export function inline(text: string, marks = false): Run[] {
  const runs: Run[] = [];
  let from = 0;
  for (const match of text.matchAll(MARK)) {
    const at = match.index ?? 0;
    if (at > from) runs.push({ text: text.slice(from, at) });
    const bold = match[1] !== undefined;
    const marker = bold ? '**' : '*';
    const style = bold ? { bold: true } : { italic: true };
    if (marks) runs.push({ text: marker, mark: true });
    runs.push({ text: match[1] ?? match[2], ...style });
    if (marks) runs.push({ text: marker, mark: true });
    from = at + match[0].length;
  }
  if (from < text.length) runs.push({ text: text.slice(from) });
  return runs;
}

/** The words alone: no marks, no dividers, no photos. */
export function plain(md: string): string {
  return blocks(md)
    .flatMap((b) => (b.kind === 'p' || b.kind === 'h' || b.kind === 'quote' ? [b.text] : []))
    .map((text) => inline(text).map((r) => r.text).join(''))
    .join('\n\n');
}

/** The ids of the photos a story places; the rest go after it, as before. */
export function photoIds(md: string): number[] {
  return blocks(md).flatMap((b) => (b.kind === 'photo' ? [b.id] : []));
}
