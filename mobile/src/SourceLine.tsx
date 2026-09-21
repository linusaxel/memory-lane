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
import { color, dim, font, label } from './theme.ts';

type Props = {
  source: Source;
  /** The episode, when there is one. The channel is who; this is which. */
  title?: string | null;
};

export default function SourceLine({ source, title }: Props) {
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
      <View style={styles.text}>
        <Text style={styles.from}>From</Text>
        <Text style={styles.name} numberOfLines={1}>
          {source.name}
        </Text>
        {title ? (
          <Text style={styles.title} numberOfLines={2}>
            {title}
          </Text>
        ) : null}
      </View>
    </View>
  );

  if (!source.url) return body;

  return (
    <Pressable
      style={dim()}
      onPress={() => Linking.openURL(source.url!).catch(() => {})}
      accessibilityRole="link"
      accessibilityLabel={`From ${source.name} on YouTube`}
    >
      {body}
    </Pressable>
  );
}

const AVATAR = 40;

const styles = StyleSheet.create({
  // No separator of its own: it sits in MemorySheet's pinned credit strip,
  // which carries the one hairline for all three credit variants.
  row: { flexDirection: 'row', alignItems: 'center', gap: 12 },
  avatar: { width: AVATAR, height: AVATAR, borderRadius: AVATAR / 2, backgroundColor: color.rule },
  avatarEmpty: { borderWidth: 1, borderColor: color.rule },
  text: { flex: 1, gap: 1 },
  from: { ...label, fontSize: 9 },
  name: { fontFamily: font.displaySemi, fontSize: 16, color: color.ink },
  title: { fontFamily: font.mono, fontSize: 11, lineHeight: 16, color: color.inkFaint },
});
