/** The map's dock: Journal · Plan a walk · Add, one glass bar along the
 *  bottom, a game's action bar, Plan a walk dead centre. Every button says its
 *  name under it. Locate is a glass circle over the bar's right end, as Apple
 *  Maps keeps it. Never over a memory: App hides it while one is up (UI.md
 *  rule 13). */

import type { ReactNode } from 'react';
import { Pressable, StyleSheet, Text, View } from 'react-native';

import { GlassButton, GlassCard } from './Glass';
import Icon from './Icon';
import { color, contour, font } from './theme';

type Props = {
  journalNew: boolean;
  /** The map is following you: Locate draws filled, as Apple Maps does. */
  onYou: boolean;
  onJournal: () => void;
  onAdd: () => void;
  onPlanPress: () => void;
  onPlan: () => void;
  onLocate: () => void;
};

function Slot({
  label,
  say = label,
  hint,
  go,
  onPress,
  children,
}: {
  label: string;
  /** What VoiceOver says, when the name under it is short for it. */
  say?: string;
  hint?: string;
  /** Plan a walk: named in gold. */
  go?: boolean;
  onPress: () => void;
  children: ReactNode;
}) {
  return (
    <Pressable
      hitSlop={4}
      accessibilityRole="button"
      accessibilityLabel={say}
      accessibilityHint={hint}
      onPress={onPress}
      style={({ pressed }) => [styles.slot, pressed && styles.pressed]}
    >
      <View style={styles.icon}>{children}</View>
      <Text style={[styles.name, go && styles.go]}>{label}</Text>
    </Pressable>
  );
}

export default function MapDock(p: Props) {
  return (
    <View style={styles.dock} pointerEvents="box-none">
      <GlassCard style={styles.bar}>
        <Slot
          label="Journal"
          hint={p.journalNew ? 'Something new on your memories' : undefined}
          onPress={p.onJournal}
        >
          <Icon name="journal" size={26} color={color.ink} />
          {p.journalNew && <View style={styles.newDot} />}
        </Slot>
        <Slot
          label="Plan a walk"
          go
          onPress={() => {
            p.onPlanPress();
            p.onPlan();
          }}
        >
          <Icon name="map" size={30} color={color.ink} />
        </Slot>
        <Slot label="Add" say="Add a memory here" onPress={p.onAdd}>
          <Icon name="add" size={28} color={color.ink} />
        </Slot>
        <View style={contour} pointerEvents="none" />
      </GlassCard>
      <GlassButton
        place={styles.locate}
        style={styles.circle}
        accessibilityRole="button"
        accessibilityLabel="Center on me"
        onPress={p.onLocate}
      >
        <Icon name="locate" size={22} color={color.ink} filled={p.onYou} />
      </GlassButton>
    </View>
  );
}

const styles = StyleSheet.create({
  // At 70, 12pt over Apple's logo and Legal link, as the row it replaced.
  dock: { position: 'absolute', left: 12, right: 12, bottom: 70 },
  bar: {
    flexDirection: 'row',
    alignItems: 'flex-end',
    justifyContent: 'space-around',
    paddingTop: 10,
    paddingBottom: 8,
    paddingHorizontal: 6,
    minHeight: 68,
  },
  slot: { flex: 1, alignItems: 'center', gap: 2, minHeight: 44 },
  locate: { position: 'absolute', right: 2, bottom: 80 },
  circle: {
    width: 44,
    height: 44,
    borderRadius: 22,
    alignItems: 'center',
    justifyContent: 'center',
  },
  pressed: { transform: [{ scale: 0.92 }] },
  icon: { height: 34, justifyContent: 'center', alignItems: 'center' },
  name: { ...font.uiBold, fontSize: 11, color: color.inkSoft },
  go: { color: color.gold },
  newDot: {
    position: 'absolute',
    top: 0,
    right: -6,
    width: 10,
    height: 10,
    borderRadius: 5,
    borderWidth: 1.5,
    borderColor: color.paper,
    backgroundColor: color.gold,
  },
});
