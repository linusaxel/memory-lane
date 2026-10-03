/** Who said this, with their face on it.
 *
 * A summary with no source reads as the app asserting it, and the app was not
 * there. It is also the only answer to the question the summaries kept raising
 * and never answering: over half of them opened with "the speaker", and nothing
 * anywhere on screen said who that was. The channel is who that was.
 *
 * Tappable, because a credit that cannot be followed is decoration. The avatar
 * is a remote image and may not load; the name never depends on it.
 */

import { useState } from 'react';
import { Image, Pressable, StyleSheet, Text, View } from 'react-native';

import type { Source } from './api.ts';
import { openLink } from './link.ts';
import { color, dim, story } from './theme.ts';

type Props = {
  source: Source;
  /** Where a tap goes, when it is more exact than the channel: the passage, or
   *  the video at the right second. The credit is the story's only source link. */
  url?: string;
  /** What VoiceOver hears for that tap: "Read it in the book". */
  spoken?: string;
};

export default function SourceLine({ source, url = source.url ?? undefined, spoken }: Props) {
  // A channel avatar is decoration; with none, or one that will not load, the
  // credit stands alone - an empty circle read as a missing picture.
  const [iconFailed, setIconFailed] = useState(false);

  const body = (
    <View style={styles.row}>
      {source.icon_url && !iconFailed && (
        <Image
          source={{ uri: source.icon_url }}
          style={styles.avatar}
          onError={() => setIconFailed(true)}
        />
      )}
      <Text style={styles.from} numberOfLines={2}>
        Retold by AI from <Text style={styles.name}>{source.name}</Text>
        {/* Ember, as every link here is, and pointing out: it leaves the app.
            Inside the text, so it follows the last word when the name wraps. */}
        {url && <Text style={styles.out}> ↗</Text>}
      </Text>
    </View>
  );

  if (!url) return body;

  return (
    <Pressable
      style={dim()}
      onPress={() => openLink(url).catch(() => {})}
      accessibilityRole="link"
      accessibilityLabel={spoken ?? `Retold by AI from ${source.name}`}
    >
      {body}
    </Pressable>
  );
}

const AVATAR = 20;

const styles = StyleSheet.create({
  // MemorySheet's byline, under the place name.
  row: { flexDirection: 'row', alignItems: 'center', gap: 8 },
  avatar: { width: AVATAR, height: AVATAR, borderRadius: AVATAR / 2, backgroundColor: color.rule },
  from: { ...story.meta, flex: 1 },
  name: { color: color.ink },
  out: { color: color.ember },
});
