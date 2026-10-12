/** Your initial, or nobody: one circle at any size, on a memory's byline.
 *  There is no photo: your Collector is the one picture of you (docs/10,
 *  "One you"). */

import { StyleSheet, Text, View } from 'react-native';

import Glyph from './Glyph.tsx';
import { color, font } from './theme.ts';

type Props = {
  name: string | null | undefined;
  size: number;
};

export default function Avatar({ name, size }: Props) {
  const circle = { width: size, height: size, borderRadius: size / 2 };
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
  circle: {
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: color.track,
    overflow: 'hidden',
  },
  initial: { ...font.title, color: color.ink },
});
