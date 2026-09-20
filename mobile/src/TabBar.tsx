/** Two tabs, hand-rolled.
 *
 * Not react-navigation: there are two destinations, no stack, no deep links and
 * no params. A router would be more code than the thing it routes, and both
 * screens stay mounted anyway - see App.tsx for why the map must not unmount.
 */

import { Pressable, StyleSheet, Text, View } from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';

export type Tab = 'map' | 'collection';

type Props = {
  tab: Tab;
  unlockedCount: number;
  onSelect: (tab: Tab) => void;
};

export default function TabBar({ tab, unlockedCount, onSelect }: Props) {
  const insets = useSafeAreaInsets();

  return (
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
      style={styles.item}
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
    backgroundColor: '#fff',
    borderTopWidth: 1,
    borderTopColor: '#f4f4f5',
    paddingTop: 10,
  },
  item: { flex: 1, flexDirection: 'row', alignItems: 'center', justifyContent: 'center', gap: 7 },
  label: { fontSize: 15, fontWeight: '600', color: '#a1a1aa' },
  active: { color: '#18181b' },
  badge: {
    minWidth: 21,
    paddingHorizontal: 6,
    paddingVertical: 2,
    borderRadius: 11,
    backgroundColor: '#f4f4f5',
  },
  badgeActive: { backgroundColor: '#18181b' },
  badgeText: { fontSize: 12, fontWeight: '700', color: '#a1a1aa', textAlign: 'center' },
  badgeTextActive: { color: '#fff' },
});
