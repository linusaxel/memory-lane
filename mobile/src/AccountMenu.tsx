/** You, top right: your photo or initial in a glass circle, and under it a
 *  native menu. Your name, your numbers and Edit profile, then Settings. */

import { Button, Host, Menu, RNHostView, Section } from '@expo/ui/swift-ui';
import { accessibilityLabel, disabled } from '@expo/ui/swift-ui/modifiers';
import { GlassView, isLiquidGlassAvailable } from 'expo-glass-effect';
import { StyleSheet, View } from 'react-native';

import type { Profile } from './api.ts';
import Avatar from './Avatar.tsx';
import { color, lift } from './theme';

const PROVIDER = { apple: 'Apple', google: 'Google' } as const;

const GLASS = isLiquidGlassAvailable();

type Props = {
  profile: Profile | null;
  name: string;
  onEditProfile: () => void;
  onSettings: () => void;
};

export default function AccountMenu({ profile, name, onEditProfile, onSettings }: Props) {
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
        modifiers={[accessibilityLabel('You')]}
        label={
          <RNHostView matchContents>
            <View style={styles.face}>
              <Avatar url={profile?.avatar_url} name={name} size={38} />
            </View>
          </RNHostView>
        }
      >
        <Section title={name.trim() || 'Anonymous'}>
          <Button label={numbers} systemImage="flame" modifiers={[disabled(true)]} />
          <Button label={signedIn} systemImage="person.badge.key" modifiers={[disabled(true)]} />
          <Button label="Edit profile" systemImage="person.crop.circle" onPress={onEditProfile} />
        </Section>
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
});
