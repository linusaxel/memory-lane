/** You, top right: your photo or initial in a glass circle, and under it a
 *  native menu. Your name, your numbers and Edit profile; before a walk which
 *  pins the map draws (all, only what is still locked, or only what you have
 *  opened); then Settings. */

import { Button, Host, Menu, RNHostView, Section } from '@expo/ui/swift-ui';
import { accessibilityLabel, disabled } from '@expo/ui/swift-ui/modifiers';
import { GlassView, isLiquidGlassAvailable } from 'expo-glass-effect';
import { StyleSheet, View } from 'react-native';

import type { Profile } from './api.ts';
import Avatar from './Avatar.tsx';
import Glyph from './Glyph.tsx';
import { color, lift } from './theme';

export type MapShows = 'all' | 'locked' | 'unlocked';

/** What you already opened is in the Journal; the map is for what is left. */
export const MAP_SHOWS_DEFAULT: MapShows = 'locked';

const CHOICES: { value: MapShows; label: string }[] = [
  { value: 'all', label: 'All memories' },
  { value: 'locked', label: 'Locked' },
  { value: 'unlocked', label: 'Unlocked' },
];

const PROVIDER = { apple: 'Apple', google: 'Google' } as const;

const GLASS = isLiquidGlassAvailable();

type Props = {
  profile: Profile | null;
  name: string;
  shows: MapShows;
  onShow: (shows: MapShows) => void;
  // Before a walk only: on one the map draws just the walk.
  filter: boolean;
  onEditProfile: () => void;
  onSettings: () => void;
};

export default function AccountMenu({ profile, name, shows, onShow, filter, onEditProfile, onSettings }: Props) {
  const thinned = filter && shows !== MAP_SHOWS_DEFAULT;
  const numbers = [
    profile?.streak ? `${profile.streak}-day streak` : null,
    `${profile?.unlocked ?? 0} opened`,
    `${profile?.submitted ?? 0} filed`,
  ]
    .filter(Boolean)
    .join(' · ');
  const signedIn = profile?.providers.length
    ? `Signed in with ${profile.providers.map((provider) => PROVIDER[provider]).join(' and ')}`
    : 'Not signed in';
  const menu = (
    <Host matchContents>
      <Menu
        modifiers={[
          accessibilityLabel(
            thinned ? `You, showing ${CHOICES.find((choice) => choice.value === shows)?.label}` : 'You',
          ),
        ]}
        label={
          <RNHostView matchContents>
            <View style={styles.face}>
              <Avatar url={profile?.avatar_url} name={name} size={38} />
              {/* The filter's glyph while it hides something, so a thinned map says why. */}
              {thinned && (
                <View style={styles.thinned}>
                  <Glyph name="line.3.horizontal.decrease" size={9} weight="bold" color={color.paper} />
                </View>
              )}
            </View>
          </RNHostView>
        }
      >
        <Section title={name.trim() || 'Anonymous'}>
          <Button label={numbers} systemImage="flame" modifiers={[disabled(true)]} />
          <Button label={signedIn} systemImage="person.badge.key" modifiers={[disabled(true)]} />
          <Button label="Edit profile" systemImage="person.crop.circle" onPress={onEditProfile} />
        </Section>
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
  face: { width: 44, height: 44, alignItems: 'center', justifyContent: 'center' },
  thinned: {
    position: 'absolute',
    right: 1,
    bottom: 1,
    width: 16,
    height: 16,
    borderRadius: 8,
    borderWidth: 1.5,
    borderColor: color.paper,
    backgroundColor: color.ember,
    alignItems: 'center',
    justifyContent: 'center',
  },
});
