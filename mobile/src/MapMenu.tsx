/** The map's one corner menu, top right: which pins the map draws before a
 *  walk (all of them, only what is still locked, or only what you have
 *  opened), then Settings. A native menu in a glass circle. */

import { Button, Host, Image, Menu, Section } from '@expo/ui/swift-ui';
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

type Props = {
  shows: MapShows;
  onShow: (shows: MapShows) => void;
  // Before a walk only: on one the map draws just the walk.
  filter: boolean;
  onSettings: () => void;
};

export default function MapMenu({ shows, onShow, filter, onSettings }: Props) {
  const thinned = filter && shows !== 'all';
  const menu = (
    <Host matchContents>
      <Menu
        modifiers={[
          accessibilityLabel(
            thinned ? `More, showing ${CHOICES.find((choice) => choice.value === shows)?.label}` : 'More',
          ),
        ]}
        label={
          <Image
            // The filter's glyph while it hides something, so a thinned map says why.
            systemName={thinned ? 'line.3.horizontal.decrease.circle.fill' : 'ellipsis'}
            color={color.ink}
            size={18}
            modifiers={[frame({ width: 44, height: 44 })]}
          />
        }
      >
        {filter && (
          <Section title="Show on map">
            {CHOICES.map((choice) => (
              <Button
                key={choice.value}
                label={choice.label}
                systemImage={choice.value === shows ? 'checkmark' : undefined}
                onPress={() => onShow(choice.value)}
              />
            ))}
          </Section>
        )}
        <Button label="Settings" systemImage="gearshape" onPress={onSettings} />
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
