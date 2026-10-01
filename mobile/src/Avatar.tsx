/** Your face, or your initial, or nobody: one circle at any size. The map's
 *  Journal pill, the journal header, Edit profile and a memory's byline. */

import { Image, StyleSheet, Text, View } from 'react-native';

import { mediaUrl } from './api.ts';
import Glyph from './Glyph.tsx';
import { color, font } from './theme.ts';

type Props = {
  url: string | null | undefined;
  name: string | null | undefined;
  size: number;
};

export default function Avatar({ url, name, size }: Props) {
  const circle = { width: size, height: size, borderRadius: size / 2 };
  if (url) {
    return <Image source={{ uri: mediaUrl({ url }) }} style={[styles.circle, circle]} accessibilityIgnoresInvertColors />;
  }
  const initial = name && name !== 'Anonymous' ? name.trim().charAt(0).toUpperCase() : '';
  return (
    <View style={[styles.circle, circle]}>
      {initial ? (
        <Text style={[styles.initial, { fontSize: size * 0.45 }]}>{initial}</Text>
      ) : (
        <Glyph name="person.fill" size={size * 0.5} color={color.inkFaint} />
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  circle: { alignItems: 'center', justifyContent: 'center', backgroundColor: color.rule, overflow: 'hidden' },
  initial: { ...font.uiBold, color: color.inkSoft },
});
