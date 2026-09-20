/** Three tabs, hand-rolled.
 *
 * Not react-navigation: no stack, no deep links, no params. A router would be
 * more code than the thing it routes, and every screen stays mounted anyway -
 * see App.tsx for why the map must not unmount.
 */

import { Pressable, StyleSheet, Text, View } from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';

import { color, dim, font, label as themeLabel } from './theme.ts';

export type Tab = 'map' | 'collection' | 'you';

type Props = {
  tab: Tab;
  unlockedCount: number;
  onSelect: (tab: Tab) => void;
};

export default function TabBar({ tab, unlockedCount, onSelect }: Props) {
  const insets = useSafeAreaInsets();

  return (
    // Solid, not glass. The bar sits in the layout rather than over the map, so
    // there is nothing behind it to blur - and an overlay bar would cover the
    // Apple Maps attribution, which rule 7 does not allow.
    <View style={[styles.bar, { paddingBottom: Math.max(insets.bottom, 10) }]}>
      <Item label="Map" active={tab === 'map'} onPress={() => onSelect('map')} />
      <Item
        label="Unlocked"
        // The count is the point of the tab: it is the only number in the app
        // that goes up because you went outside.
        badge={unlockedCount}
        active={tab === 'collection'}
        onPress={() => onSelect('collection')}
      />
      <Item label="You" active={tab === 'you'} onPress={() => onSelect('you')} />
    </View>
  );
}

function Item({
  label,
  active,
  badge,
  onPress,
}: {
  label: string;
  active: boolean;
  badge?: number;
  onPress: () => void;
}) {
  return (
    <Pressable
      style={dim(styles.item)}
      onPress={onPress}
      accessibilityRole="tab"
      accessibilityState={{ selected: active }}
      accessibilityLabel={badge ? `${label}, ${badge}` : label}
    >
      <Text style={[styles.label, active && styles.active]}>{label}</Text>
      {badge ? (
        <View style={[styles.badge, active && styles.badgeActive]}>
          <Text style={[styles.badgeText, active && styles.badgeTextActive]}>{badge}</Text>
        </View>
      ) : null}
    </Pressable>
  );
}

const styles = StyleSheet.create({
  bar: {
    flexDirection: 'row',
    backgroundColor: color.paper,
    borderTopWidth: 1,
    borderTopColor: color.rule,
    paddingTop: 14,
  },
  item: { flex: 1, flexDirection: 'row', alignItems: 'center', justifyContent: 'center', gap: 8 },
  label: { ...themeLabel, letterSpacing: 1.2 },
  active: { color: color.ink },
  badge: {
    minWidth: 20,
    paddingHorizontal: 6,
    paddingVertical: 2,
    borderRadius: 3,
    borderWidth: 1,
    borderColor: color.rule,
  },
  badgeActive: { backgroundColor: color.ink, borderColor: color.ink },
  badgeText: { fontFamily: font.monoBold, fontSize: 10, color: color.inkFaint, textAlign: 'center' },
  badgeTextActive: { color: color.paper },
});
