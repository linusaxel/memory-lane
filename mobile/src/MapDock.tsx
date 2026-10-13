/** The map's dock: Journal · Plan a walk · Add, one glass bar along the
 *  bottom, a game's action bar, Plan a walk dead centre. Every button says its
 *  name under it. Never over a memory: App hides it while one is up (UI.md
 *  rule 13). */

import type { ReactNode } from 'react';
import { Pressable, StyleSheet, Text, View } from 'react-native';

import { GlassCard } from './Glass';
import Icon from './Icon';
import { color, contour, font } from './theme';

type Props = {
  journalNew: boolean;
  onJournal: () => void;
  onAdd: () => void;
  onPlanPress: () => void;
  onPlan: () => void;
  /** On a walk: Plan a walk stays in its place, dimmed, so the dock never changes. */
  planOff?: boolean;
};

function Slot({
  label,
  say = label,
  hint,
  go,
  off,
  onPress,
  children,
}: {
  label: string;
  /** What VoiceOver says, when the name under it is short for it. */
  say?: string;
  hint?: string;
  /** Plan a walk: named in gold. */
  go?: boolean;
  off?: boolean;
  onPress: () => void;
  children: ReactNode;
}) {
  return (
    <Pressable
      hitSlop={4}
      accessibilityRole="button"
      accessibilityLabel={say}
      accessibilityHint={hint}
      accessibilityState={{ disabled: off }}
      disabled={off}
      onPress={onPress}
      style={({ pressed }) => [styles.slot, pressed && styles.pressed, off && styles.off]}
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
          off={p.planOff}
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
  pressed: { transform: [{ scale: 0.92 }] },
  off: { opacity: 0.4 },
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
