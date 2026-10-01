/** The map's one button, bottom centre, like Pokémon GO's Poké Ball: your
 *  face in an ember ring. It opens a card of everything that is not the map
 *  itself - the walk, the journal, filing, how it works, settings - so the
 *  map keeps four controls. docs/10, "One button, like a Poké Ball". */

import { Pressable, StyleSheet, Text, View } from 'react-native';

import Avatar from './Avatar.tsx';
import Glyph from './Glyph.tsx';
import { GlassButton } from './Glass.tsx';
import { button, buttonText, color, dim, floating, font, label, radius } from './theme.ts';

type Props = {
  open: boolean;
  onToggle: (open: boolean) => void;
  avatarUrl: string | null | undefined;
  name: string;
  /** A heart or a note came back on something you filed. */
  news: boolean;
  collected: number;
  nearby: number;
  /** Plan a walk only before one: on a walk the card has no walk to plan. */
  onPlan: (() => void) | null;
  onJournal: () => void;
  onAdd: () => void;
  onHow: () => void;
  onSettings: () => void;
};

export default function Hub({
  open,
  onToggle,
  avatarUrl,
  name,
  news,
  collected,
  nearby,
  onPlan,
  onJournal,
  onAdd,
  onHow,
  onSettings,
}: Props) {
  // Every tile closes the card first, so what it opens is never under it.
  const pick = (go: () => void) => () => {
    onToggle(false);
    go();
  };
  return (
    <>
      {open && (
        <Pressable style={styles.scrim} onPress={() => onToggle(false)} accessibilityLabel="Close menu" />
      )}
      {open && (
        <View style={styles.card}>
          {onPlan && (
            <Pressable style={dim([button.solid, styles.plan])} onPress={pick(onPlan)} accessibilityRole="button">
              <Glyph name="figure.walk" size={18} weight="semibold" color={color.paper} />
              <Text style={[buttonText, { color: color.paper }]}>Plan a walk</Text>
            </Pressable>
          )}
          <View style={styles.grid}>
            <Tile glyph="book.closed" title="Journal" note={`${collected} collected · ${nearby} nearby`} dot={news} onPress={pick(onJournal)} />
            <Tile glyph="plus" title="Add a memory" note="Right where you are" onPress={pick(onAdd)} />
            <Tile glyph="questionmark.circle" title="How it works" onPress={pick(onHow)} />
            <Tile glyph="gearshape" title="Settings" onPress={pick(onSettings)} />
          </View>
        </View>
      )}
      <GlassButton
        place={styles.place}
        style={styles.button}
        accessibilityRole="button"
        accessibilityLabel="Menu"
        accessibilityHint={news ? 'Something new on your memories' : undefined}
        accessibilityState={{ expanded: open }}
        onPress={() => onToggle(!open)}
      >
        <View style={styles.ring}>
          <Avatar url={avatarUrl} name={name} size={50} />
        </View>
        {news && <View style={styles.badge} />}
      </GlassButton>
    </>
  );
}

function Tile({
  glyph,
  title,
  note,
  dot = false,
  onPress,
}: {
  glyph: 'book.closed' | 'plus' | 'questionmark.circle' | 'gearshape';
  title: string;
  note?: string;
  dot?: boolean;
  onPress: () => void;
}) {
  return (
    <Pressable style={dim(styles.tile)} onPress={onPress} accessibilityRole="button" accessibilityLabel={title}>
      <View style={styles.tileTop}>
        <Glyph name={glyph} size={20} weight="medium" color={glyph === 'plus' ? color.ember : color.ink} />
        {dot && <View style={styles.dot} />}
      </View>
      <Text style={styles.tileTitle}>{title}</Text>
      {note && <Text style={styles.tileNote}>{note}</Text>}
    </Pressable>
  );
}

const BUTTON = 64;

const styles = StyleSheet.create({
  scrim: { position: 'absolute', top: 0, right: 0, bottom: 0, left: 0, backgroundColor: color.scrim },
  card: { ...floating, position: 'absolute', left: 16, right: 16, bottom: 44 + BUTTON + 12, padding: 16, gap: 12 },
  plan: { flexDirection: 'row', gap: 8 },
  grid: { flexDirection: 'row', flexWrap: 'wrap', gap: 10 },
  tile: {
    flexBasis: '47%',
    flexGrow: 1,
    minHeight: 88,
    padding: 14,
    gap: 4,
    borderRadius: radius.field,
    borderWidth: 1,
    borderColor: color.rule,
  },
  tileTop: { flexDirection: 'row', justifyContent: 'space-between', marginBottom: 4 },
  tileTitle: { ...font.uiBold, fontSize: 16, color: color.ink },
  tileNote: { ...label, fontSize: 12 },
  dot: { width: 8, height: 8, borderRadius: 4, backgroundColor: color.ember },

  place: { position: 'absolute', bottom: 44, alignSelf: 'center' },
  button: { width: BUTTON, height: BUTTON, borderRadius: BUTTON / 2, alignItems: 'center', justifyContent: 'center' },
  ring: { padding: 2, borderRadius: BUTTON / 2, borderWidth: 2, borderColor: color.ember },
  badge: {
    position: 'absolute',
    top: 4,
    right: 4,
    width: 14,
    height: 14,
    borderRadius: 7,
    borderWidth: 2,
    borderColor: color.paper,
    backgroundColor: color.ember,
  },
});
