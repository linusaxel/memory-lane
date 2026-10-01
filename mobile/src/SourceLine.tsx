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
import { Image, Linking, Pressable, StyleSheet, Text, View } from 'react-native';

import type { Source } from './api.ts';
import { color, dim, story } from './theme.ts';

type Props = {
  source: Source;
  /** The rest of the sheet's meta line, after the credit: " · 1978 · 40 m away". */
  after?: string;
};

export default function SourceLine({ source, after }: Props) {
  // A channel avatar is decoration; if it will not load, fall back to the same
  // empty circle a channel without one gets rather than a grey disc that looks
  // like it is still loading.
  const [iconFailed, setIconFailed] = useState(false);

  const body = (
    <View style={styles.row}>
      {source.icon_url && !iconFailed ? (
        <Image
          source={{ uri: source.icon_url }}
          style={styles.avatar}
          onError={() => setIconFailed(true)}
        />
      ) : (
        <View style={[styles.avatar, styles.avatarEmpty]} />
      )}
      <Text style={styles.from} numberOfLines={2}>
        Retold from <Text style={styles.name}>{source.name}</Text>
        {after}
      </Text>
    </View>
  );

  if (!source.url) return body;

  return (
    <Pressable
      style={dim()}
      onPress={() => Linking.openURL(source.url!).catch(() => {})}
      accessibilityRole="link"
      accessibilityLabel={`Retold from ${source.name}`}
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
  avatarEmpty: { borderWidth: 1, borderColor: color.rule },
  from: { ...story.meta, flex: 1 },
  name: { color: color.ink },
});
