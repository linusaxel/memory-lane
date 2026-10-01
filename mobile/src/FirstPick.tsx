/** The first run's one choice, on the map rather than a screen of its own
 *  (F36): three locked memories near you, and the one you pick opens from
 *  wherever you are. Every one after it opens where it happened (docs/10,
 *  "Pick one to start, then where you stand"). */

import { Pressable, StyleSheet, Text, View } from 'react-native';

import type { LocatedMemory } from './api.ts';
import { distance } from './format.ts';
import { button, buttonText, color, dim, floating, font, label } from './theme.ts';

type Props = {
  picks: LocatedMemory[];
  /** No position yet: the picks are around the map's centre, and the card
   *  offers yours. */
  located: boolean;
  onLocate: () => void;
  /** Opens its peek, where "Open this one from here" spends the welcome. */
  onPick: (memory: LocatedMemory) => void;
};

export default function FirstPick({ picks, located, onLocate, onPick }: Props) {
  return (
    <View style={styles.card}>
      <Text style={styles.title}>Choose one to open from here</Text>
      <Text style={styles.text}>The rest open when you stand on them.</Text>
      {!located && (
        <Pressable
          style={dim(styles.locate)}
          accessibilityRole="button"
          accessibilityHint="Asks for permission to use your location"
          onPress={onLocate}
        >
          <Text style={styles.locateText}>Show the ones near me</Text>
        </Pressable>
      )}
      {picks.map((memory) => {
        const meta = [
          memory.year,
          memory.distance_meters != null && distance(memory.distance_meters, { suffix: 'away' }),
        ]
          .filter(Boolean)
          .join(' · ');
        return (
          <Pressable
            key={memory.id}
            style={dim(styles.row)}
            accessibilityRole="button"
            accessibilityLabel={`${memory.place.name}${meta ? `, ${meta}` : ''}`}
            onPress={() => onPick(memory)}
          >
            <Text style={styles.place} numberOfLines={1}>
              {memory.place.name}
            </Text>
            {!!meta && <Text style={styles.meta}>{meta}</Text>}
          </Pressable>
        );
      })}
    </View>
  );
}

const styles = StyleSheet.create({
  card: { ...floating, position: 'absolute', left: 18, right: 18, bottom: 134, padding: 20, gap: 6 },
  title: { ...font.display, fontSize: 22, lineHeight: 28, color: color.ink },
  text: { ...font.prose, fontSize: 15, lineHeight: 22, color: color.inkSoft, marginBottom: 6 },
  locate: { ...button.solid, marginVertical: 6 },
  locateText: { ...buttonText, color: color.paper },
  row: { paddingVertical: 10, borderTopWidth: 1, borderTopColor: color.rule, gap: 2 },
  place: { ...font.displaySemi, fontSize: 17, color: color.ink },
  meta: label,
});
