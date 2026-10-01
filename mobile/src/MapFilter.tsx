/** Which pins the map draws before a walk: all of them, only what is still
 *  locked, or only what you have opened. A native menu in a glass circle,
 *  top right, left of Settings. */

import { Button, Host, Image, Menu } from '@expo/ui/swift-ui';
import { accessibilityLabel, frame } from '@expo/ui/swift-ui/modifiers';
import { GlassView, isLiquidGlassAvailable } from 'expo-glass-effect';
import { StyleSheet, View } from 'react-native';

import { color, lift } from './theme';

export type MapShows = 'all' | 'locked' | 'unlocked';

const CHOICES: { value: MapShows; label: string }[] = [
  { value: 'all', label: 'All memories' },
  { value: 'locked', label: 'Locked' },
  { value: 'unlocked', label: 'Unlocked' },
];

const GLASS = isLiquidGlassAvailable();

export default function MapFilter({ shows, onShow }: { shows: MapShows; onShow: (shows: MapShows) => void }) {
  const menu = (
    <Host matchContents>
      <Menu
        modifiers={[accessibilityLabel(`Show on map: ${CHOICES.find((choice) => choice.value === shows)?.label}`)]}
        label={
          <Image
            // Filled while it hides something, so a thinned map says why.
            systemName={shows === 'all' ? 'line.3.horizontal.decrease' : 'line.3.horizontal.decrease.circle.fill'}
            color={color.ink}
            size={18}
            modifiers={[frame({ width: 44, height: 44 })]}
          />
        }
      >
        {CHOICES.map((choice) => (
          <Button
            key={choice.value}
            label={choice.label}
            systemImage={choice.value === shows ? 'checkmark' : undefined}
            onPress={() => onShow(choice.value)}
          />
        ))}
      </Menu>
    </Host>
  );
  return GLASS ? (
    <GlassView style={styles.circle} glassEffectStyle="regular" isInteractive>
      {menu}
    </GlassView>
  ) : (
    <View style={[styles.circle, lift, { backgroundColor: color.paperRaised }]}>{menu}</View>
  );
}

const styles = StyleSheet.create({
  circle: { width: 44, height: 44, borderRadius: 22, alignItems: 'center', justifyContent: 'center', overflow: 'hidden' },
});
