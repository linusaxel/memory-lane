/** What a render error shows instead of a blank screen. Try again remounts the
 *  app from the top; what it had cached survives, so that is usually enough. */

import { Component, type ReactNode } from 'react';
import { StyleSheet, Text, View, useColorScheme } from 'react-native';
import * as SplashScreen from 'expo-splash-screen';
import Svg, { Circle, Ellipse, Path } from 'react-native-svg';

import Button from './Button.tsx';
import DiamondRule from './DiamondRule.tsx';
import { color, font, screenTitle, solid } from './theme.ts';

export class Crashed extends Component<{ children: ReactNode }, { failed: boolean }> {
  state = { failed: false };

  static getDerivedStateFromError() {
    return { failed: true };
  }

  componentDidCatch(error: Error) {
    console.error('Render error', error);
    // A crash before StartupLogo mounts would leave the splash over this.
    SplashScreen.hideAsync().catch(() => {});
  }

  render() {
    if (!this.state.failed) return this.props.children;
    return (
      <View style={styles.page}>
        <Broken />
        <Text style={styles.title}>Something broke.</Text>
        <DiamondRule place={styles.rule} />
        <Text style={styles.body}>Your walk and your memories are safe.</Text>
        <Button
          kind="go"
          label="Try again"
          place={styles.button}
          onPress={() => this.setState({ failed: false })}
        />
      </View>
    );
  }
}

/** A locket sprung open, drawn in line (the handoff's B-37). Svg takes a real
 *  colour, not a dynamic one, hence `solid`. */
function Broken() {
  const { gold, seal } = solid(useColorScheme() === 'dark');
  return (
    <Svg width={200} height={190} viewBox="0 0 200 190" fill="none">
      <Path
        d="M118 6c-6 6-2 12 0 16s-4 9-1 14 4 8 2 13"
        stroke={gold}
        strokeWidth={2}
        strokeDasharray="2.5 3.5"
        strokeOpacity={0.7}
        strokeLinecap="round"
      />
      <Circle cx={121} cy={56} r={6} stroke={gold} strokeWidth={2.2} />
      <Ellipse cx={121} cy={117} rx={44} ry={54} stroke={gold} strokeWidth={2.4} />
      <Ellipse
        cx={121}
        cy={117}
        rx={35}
        ry={44}
        stroke={gold}
        strokeWidth={1.2}
        strokeDasharray="3 4"
        strokeOpacity={0.7}
      />
      <Ellipse
        cx={44}
        cy={124}
        rx={32}
        ry={48}
        transform="rotate(-14 44 124)"
        stroke={gold}
        strokeWidth={2.4}
      />
      <Ellipse
        cx={44}
        cy={124}
        rx={24}
        ry={38}
        transform="rotate(-14 44 124)"
        stroke={gold}
        strokeWidth={1.2}
        strokeOpacity={0.55}
      />
      <Path d="M74 112h3M74 120h3M74 128h3" stroke={gold} strokeWidth={2.2} strokeLinecap="round" />
      <Path d="M160 168l2 5.6 5.6 2-5.6 2-2 5.6-2-5.6-5.6-2 5.6-2z" fill={seal} />
    </Svg>
  );
}

const styles = StyleSheet.create({
  page: {
    flex: 1,
    backgroundColor: color.paper,
    justifyContent: 'center',
    alignItems: 'center',
    padding: 32,
  },
  title: { ...screenTitle, textAlign: 'center', marginTop: 24 },
  rule: { width: 160, marginTop: 16 },
  body: { ...font.prose, fontSize: 17, color: color.inkSoft, textAlign: 'center', marginTop: 16 },
  button: { marginTop: 28, minWidth: 220 },
});
