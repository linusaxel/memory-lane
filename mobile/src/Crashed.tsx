/** What a render error shows instead of a blank screen. Try again remounts the
 *  app from the top; what it had cached survives, so that is usually enough. */

import { Component, type ReactNode } from 'react';
import { StyleSheet, Text, View } from 'react-native';
import * as SplashScreen from 'expo-splash-screen';

import Button from './Button.tsx';
import DiamondRule from './DiamondRule.tsx';
import { color, font, screenTitle } from './theme.ts';

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
    return <Broke onRetry={() => this.setState({ failed: false })} />;
  }
}

/** The page itself. App.tsx shows it for a dev link too: a real throw in a
 *  dev build is covered by React Native's own red error screen. */
export function Broke({ onRetry }: { onRetry: () => void }) {
  return (
    <View style={styles.page}>
      <Text style={styles.title}>Something broke.</Text>
      <DiamondRule place={styles.rule} />
      <Text style={styles.body}>Your walk and your memories are safe.</Text>
      <Button kind="go" label="Try again" place={styles.button} onPress={onRetry} />
    </View>
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
