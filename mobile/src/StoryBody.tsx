/** A story's text laid out the way it was written (story.ts): the open sheet
 *  reads with this, and the editor's Preview shows it. A summary with no marks
 *  in it is one paragraph and reads exactly as it always has. */

import { useState, type ReactNode } from 'react';
import { Image, Text, View, StyleSheet, type StyleProp, type ViewStyle } from 'react-native';

import { mediaUrl, type MediaItem } from './api.ts';
import Flourish from './Flourish.tsx';
import { lede, summaryParts } from './hashtags.ts';
import { blocks, inline, type Block, type Run } from './story.ts';
import { color, font, label, radius, story } from './theme.ts';

type Link = { text: string; url: string };
type Props = {
  summary: string;
  media: MediaItem[];
  links?: Link[];
  onLink?: (url: string) => void;
  /** Wraps each part, so the sheet can stagger them in. */
  part?: (i: number, node: ReactNode) => ReactNode;
};

const FRACTION = { s: 1 / 3, m: 1 / 2, l: 1 };
const GAP = 12;

export default function StoryBody({ summary, media, links, onLink, part = (_, n) => n }: Props) {
  const [width, setWidth] = useState(0);
  const story = blocks(summary).filter(
    (b) => b.kind !== 'photo' || media.some((m) => m.id === b.id && m.kind === 'photo'),
  );

  const words = (runs: Run[]) =>
    runs.map((run, r) => (
      <Text key={r} style={[run.bold && styles.bold, run.italic && styles.italic]}>
        {summaryParts(run.text, links).map((p, i) =>
          p.url ? (
            <Text
              key={i}
              style={styles.link}
              accessibilityRole="link"
              onPress={() => onLink?.(p.url!)}
            >
              {p.text}
            </Text>
          ) : p.tag ? (
            <Text key={i} style={styles.hashtag}>
              {p.text}
            </Text>
          ) : (
            p.text
          ),
        )}
      </Text>
    ));

  const nodes: ReactNode[] = [];
  for (let i = 0; i < story.length; i++) {
    const b = story[i];
    const next = story[i + 1];
    if (b.kind === 'photo') {
      const item = media.find((m) => m.id === b.id)!;
      const floats = b.size !== 'l' && b.place !== 'center';
      if (floats && next?.kind === 'p' && width > 0) {
        nodes.push(
          <Wrap
            key={i}
            block={b}
            item={item}
            runs={inline(next.text)}
            width={width}
            words={words}
          />,
        );
        i++;
      } else {
        nodes.push(<Figure key={i} block={b} item={item} width={width} style={styles[b.place]} />);
      }
      continue;
    }
    if (b.kind === 'divider') nodes.push(<Flourish key={i} />);
    else if (b.kind === 'h')
      nodes.push(
        <Text key={i} style={styles.heading} accessibilityRole="header">
          {words(inline(b.text))}
        </Text>,
      );
    else if (b.kind === 'quote')
      nodes.push(
        <View key={i} style={styles.quote}>
          <Text style={styles.body}>{words(inline(b.text))}</Text>
        </View>,
      );
    else if (i === 0) {
      // The lede is the first paragraph's first sentence, set apart as before.
      const [first, rest] = lede(b.text);
      nodes.push(
        <View key={i} style={styles.lede}>
          <Text style={styles.body}>{words(inline(first))}</Text>
          {rest !== '' && <Text style={styles.body}>{words(inline(rest))}</Text>}
        </View>,
      );
    } else
      nodes.push(
        <Text key={i} style={styles.body}>
          {words(inline(b.text))}
        </Text>,
      );
  }

  return (
    <View style={styles.column} onLayout={(e) => setWidth(e.nativeEvent.layout.width)}>
      {nodes.map((node, i) => part(i, node))}
    </View>
  );
}

type PhotoBlock = Extract<Block, { kind: 'photo' }>;

function Figure({
  block,
  item,
  width,
  style,
  onLayout,
}: {
  block: PhotoBlock;
  item: MediaItem;
  width: number;
  style?: StyleProp<ViewStyle>;
  onLayout?: (height: number) => void;
}) {
  const [failed, setFailed] = useState(false);
  const w = width * FRACTION[block.size];
  return (
    <View
      style={[{ width: w || '100%' }, styles.figure, style]}
      onLayout={(e) => onLayout?.(e.nativeEvent.layout.height)}
    >
      {failed ? (
        <View style={[styles.photo, styles.gone]}>
          <Text style={styles.goneText}>Photo didn't load</Text>
        </View>
      ) : (
        <Image
          testID="photo"
          source={{ uri: mediaUrl(item) }}
          style={styles.photo}
          accessibilityLabel={block.caption || undefined}
          onError={() => setFailed(true)}
        />
      )}
      {block.caption !== '' && <Text style={styles.caption}>{block.caption}</Text>}
    </View>
  );
}

/** A photo to one side and a paragraph running down beside it, then under it.
 *  The paragraph is set once out of sight at the narrow width; the lines that
 *  fit beside the photo go there and the rest run full width.
 *  ponytail: splits on whole lines, so the line level with the photo's foot
 *  may stop short; a native exclusion path is the upgrade if that shows. */
function Wrap({
  block,
  item,
  runs,
  width,
  words,
}: {
  block: PhotoBlock;
  item: MediaItem;
  runs: Run[];
  width: number;
  words: (runs: Run[]) => ReactNode;
}) {
  const [photoHeight, setPhotoHeight] = useState(0);
  const [cut, setCut] = useState<number | null>(null);
  const side = width - width * FRACTION[block.size] - GAP;
  const [beside, under] = split(runs, cut ?? 0);

  return (
    <View>
      {photoHeight > 0 && (
        <Text
          style={[styles.body, styles.measure, { width: side }]}
          accessibilityElementsHidden
          importantForAccessibility="no-hide-descendants"
          onTextLayout={(e) => {
            let fits = 0;
            for (const line of e.nativeEvent.lines) {
              if (line.y + line.height > photoHeight) break;
              fits += line.text.length;
            }
            setCut(fits);
          }}
        >
          {runs.map((r) => r.text).join('')}
        </Text>
      )}
      <View style={[styles.wrapRow, block.place === 'right' && styles.reverse]}>
        <Figure block={block} item={item} width={width} onLayout={setPhotoHeight} />
        <Text style={[styles.body, { width: side }]}>{cut == null ? null : words(beside)}</Text>
      </View>
      {under.length > 0 && <Text style={styles.body}>{words(under)}</Text>}
    </View>
  );
}

/** Runs cut in two at a character offset into their joined text. */
function split(runs: Run[], at: number): [Run[], Run[]] {
  const before: Run[] = [];
  const after: Run[] = [];
  let seen = 0;
  for (const run of runs) {
    const end = seen + run.text.length;
    if (end <= at) before.push(run);
    else if (seen >= at) after.push(run);
    else {
      before.push({ ...run, text: run.text.slice(0, at - seen) });
      after.push({ ...run, text: run.text.slice(at - seen).replace(/^\s+/, '') });
    }
    seen = end;
  }
  return [before, after];
}

const styles = StyleSheet.create({
  // MemorySheet's rhythm: 8 inside a part, 24 between parts.
  column: { gap: 24 },
  lede: { gap: 8 },
  body: story.body,
  heading: { ...story.body, ...font.storyBold },
  bold: font.storyBold,
  italic: { fontStyle: 'italic' },
  hashtag: font.storyBold,
  link: { textDecorationLine: 'underline' },
  quote: { paddingLeft: 12, borderLeftWidth: 3, borderLeftColor: color.rule },
  figure: { gap: 6 },
  left: { alignSelf: 'flex-start' },
  center: { alignSelf: 'center' },
  right: { alignSelf: 'flex-end' },
  photo: {
    width: '100%',
    aspectRatio: 4 / 3,
    borderRadius: radius.field,
    backgroundColor: color.rule,
  },
  gone: { alignItems: 'center', justifyContent: 'center' },
  goneText: { ...label, color: color.inkSoft },
  caption: { ...story.meta, color: color.inkSoft },
  wrapRow: { flexDirection: 'row', alignItems: 'flex-start', gap: GAP },
  reverse: { flexDirection: 'row-reverse' },
  measure: { position: 'absolute', opacity: 0 },
});
