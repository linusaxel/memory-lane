/** A linked name, explained in the card: Wikipedia's own summary of it, so a
 *  walker standing on the spot learns who that was without leaving the story
 *  (docs/10, "Wikipedia previews inline"). The whole article stays one tap
 *  away in the Safari sheet. Says nothing until it has something; a link it
 *  cannot preview goes to `onFail`, which opens the sheet instead. */

import { useEffect, useState } from 'react';
import { Image, Pressable, StyleSheet, Text, View } from 'react-native';

import CloseButton from './CloseButton.tsx';
import Glyph from './Glyph.tsx';
import { wikiSummaryUrl } from './format.ts';
import { openLink } from './link.ts';
import { color, dim, story } from './theme.ts';

type Props = { url: string; onClose: () => void; onFail: () => void };
type Summary = { title: string; extract: string; thumbnail?: { source: string } };

export default function WikiPreview({ url, onClose, onFail }: Props) {
  const [page, setPage] = useState<Summary | null>(null);
  const [imageFailed, setImageFailed] = useState(false);

  useEffect(() => {
    let live = true;
    setPage(null);
    setImageFailed(false);
    fetch(wikiSummaryUrl(url)!)
      .then((r) => (r.ok ? r.json() : Promise.reject(r.status)))
      .then((p: Summary) => live && (p.extract ? setPage(p) : onFail()))
      .catch(() => live && onFail());
    return () => {
      live = false;
    };
    // onFail is a fresh arrow each render; only a new link refetches.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [url]);

  if (!page) return null;

  return (
    <View style={styles.callout} testID="wiki-preview">
      <View style={styles.titleRow}>
        <Glyph name="book.closed" size={13} color={color.gold} />
        <Text style={styles.title} numberOfLines={2}>
          {page.title}
        </Text>
        <CloseButton onPress={onClose} label="Close preview" />
      </View>
      {page.thumbnail && !imageFailed && (
        <Image
          source={{ uri: page.thumbnail.source }}
          style={styles.thumb}
          onError={() => setImageFailed(true)}
        />
      )}
      <Text style={styles.extract}>{page.extract}</Text>
      <Pressable
        style={dim()}
        onPress={() => openLink(url).catch(() => {})}
        accessibilityRole="link"
        hitSlop={8}
      >
        <Text style={styles.more}>Read on Wikipedia ↗</Text>
      </Pressable>
    </View>
  );
}

const styles = StyleSheet.create({
  // MemorySheet's quote callout: the gold bar, a title row, the text.
  callout: { paddingLeft: 12, borderLeftWidth: 3, borderLeftColor: color.gold, gap: 8 },
  titleRow: { flexDirection: 'row', alignItems: 'center', gap: 6 },
  title: { ...story.meta, color: color.ink, flex: 1 },
  thumb: { width: 72, height: 72, borderRadius: 8, backgroundColor: color.rule },
  extract: story.body,
  more: { ...story.meta, color: color.gold },
});
