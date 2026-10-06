/** You, top right: your photo or initial in a glass circle, and under it a
 *  native menu. Your name, your numbers and Edit profile, then the board and
 *  Settings and Appearance. */

import { Button, Host, Menu, Picker, RNHostView, Section, Text } from '@expo/ui/swift-ui';
import { accessibilityLabel, disabled, pickerStyle, tag } from '@expo/ui/swift-ui/modifiers';
import { GlassView, isLiquidGlassAvailable } from 'expo-glass-effect';
import { useState } from 'react';
import { StyleSheet, View } from 'react-native';

import type { Profile } from './api.ts';
import { type Look, look, setLook } from './appearance.ts';
import Avatar from './Avatar.tsx';
import { color, glassEdge, glassLift, lift } from './theme';

const PROVIDER = { apple: 'Apple', google: 'Google' } as const;

const GLASS = isLiquidGlassAvailable();

type Props = {
  profile: Profile | null;
  name: string;
  onEditProfile: () => void;
  onSettings: () => void;
  onBoard: () => void;
};

export default function AccountMenu({ profile, name, onEditProfile, onSettings, onBoard }: Props) {
  const [chosen, choose] = useState<Look>(look);
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
              <Avatar url={profile?.avatar_url} name={name} size={46} />
            </View>
          </RNHostView>
        }
      >
        <Section title={name.trim() || 'Anonymous'}>
          <Button label={numbers} systemImage="flame" modifiers={[disabled(true)]} />
          <Button label={signedIn} systemImage="person.badge.key" modifiers={[disabled(true)]} />
          <Button label="Edit profile" systemImage="person.crop.circle" onPress={onEditProfile} />
        </Section>
        <Button label="Board" systemImage="list.number" onPress={onBoard} />
        <Button label="Settings" systemImage="gearshape" onPress={onSettings} />
        <Picker
          modifiers={[pickerStyle('menu')]}
          label="Appearance"
          systemImage="circle.lefthalf.filled"
          selection={chosen}
          onSelectionChange={(next: Look) => {
            choose(next);
            setLook(next);
          }}
        >
          <Text modifiers={[tag('unspecified')]}>System</Text>
          <Text modifiers={[tag('light')]}>Light</Text>
          <Text modifiers={[tag('dark')]}>Dark</Text>
        </Picker>
      </Menu>
    </Host>
  );
  return GLASS ? (
    <View style={glassLift}>
      <GlassView style={[styles.circle, glassEdge]} glassEffectStyle="regular" isInteractive>
        {menu}
      </GlassView>
    </View>
  ) : (
    <View style={[styles.circle, glassEdge, lift, { backgroundColor: color.paperRaised }]}>
      {menu}
    </View>
  );
}

const styles = StyleSheet.create({
  circle: {
    width: 48,
    height: 48,
    borderRadius: 24,
    alignItems: 'center',
    justifyContent: 'center',
    overflow: 'hidden',
  },
  face: { width: 48, height: 48, alignItems: 'center', justifyContent: 'center' },
});
