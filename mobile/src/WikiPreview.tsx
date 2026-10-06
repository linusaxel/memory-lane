/** A linked name, explained in the card: Wikipedia's own summary of it, so a
 *  walker standing on the spot learns who that was without leaving the story
 *  (docs/10, "Wikipedia previews inline"). The whole article stays one tap
 *  away in the Safari sheet. Says nothing until it has something; a link it
 *  cannot preview goes to `onFail`, which opens the sheet instead. */

import { useEffect, useState } from 'react';
import { Image, Pressable, StyleSheet, Text, View } from 'react-native';

import CloseButton from './CloseButton.tsx';
import { wikiSummaryUrl } from './format.ts';
import { openLink } from './link.ts';
import { color, dim, font, radius } from './theme.ts';

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
    <View style={styles.card} testID="wiki-preview">
      {page.thumbnail && !imageFailed && (
        <Image
          source={{ uri: page.thumbnail.source }}
          style={styles.thumb}
          onError={() => setImageFailed(true)}
        />
      )}
      <View style={styles.text}>
        <Text style={styles.title} numberOfLines={2}>
          {page.title}
        </Text>
        <Text style={styles.extract} numberOfLines={4}>
          {page.extract}
        </Text>
        <Pressable
          style={dim()}
          onPress={() => openLink(url).catch(() => {})}
          accessibilityRole="link"
          hitSlop={8}
        >
          <Text style={styles.more}>Read on Wikipedia ↗</Text>
        </Pressable>
      </View>
      <CloseButton onPress={onClose} label="Close preview" place={styles.close} />
    </View>
  );
}

const styles = StyleSheet.create({
  // A card under the paragraph the name is in: what the link would open, in
  // brief. The story's own type stays the story's.
  card: {
    flexDirection: 'row',
    gap: 12,
    padding: 14,
    paddingRight: 48,
    borderRadius: radius.card - 4,
    borderWidth: 1,
    borderColor: color.goldLine,
    backgroundColor: color.paperRaised,
  },
  close: { position: 'absolute', top: 8, right: 8 },
  text: { flex: 1, gap: 4 },
  title: { ...font.title, fontSize: 20, lineHeight: 25, color: color.ink },
  thumb: { width: 64, height: 64, borderRadius: 14, backgroundColor: color.rule },
  extract: { ...font.prose, fontSize: 15, lineHeight: 21, color: color.inkSoft },
  more: { ...font.uiBold, fontSize: 15, color: color.gold, marginTop: 4 },
});
