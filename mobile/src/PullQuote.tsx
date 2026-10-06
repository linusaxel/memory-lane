/** A quote, set apart: a big gold open-quote in Gloock, the words centred in
 *  Newsreader italic, and what they are under them (docs/10, "Jewel Box").
 *  The source's own words on the open sheet, and a story's `>` lines. */

import type { ReactNode } from 'react';
import { StyleSheet, Text, View } from 'react-native';

import { color, font, label } from './theme.ts';

export default function PullQuote({
  children,
  caption,
}: {
  children: ReactNode;
  caption?: string;
}) {
  return (
    <View style={styles.box}>
      <Text style={styles.mark} accessibilityElementsHidden importantForAccessibility="no">
        “
      </Text>
      <Text style={styles.words}>{children}</Text>
      {caption && <Text style={styles.caption}>{caption}</Text>}
    </View>
  );
}

const styles = StyleSheet.create({
  box: { alignItems: 'center', gap: 8, paddingHorizontal: 8 },
  mark: { ...font.title, fontSize: 64, lineHeight: 64, height: 44, color: color.gold },
  words: {
    ...font.storyItalic,
    fontSize: 21,
    lineHeight: 30,
    color: color.ink,
    textAlign: 'center',
  },
  caption: { ...label, textAlign: 'center' },
});
