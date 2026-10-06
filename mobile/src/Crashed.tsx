/** What a render error shows instead of a blank screen. Try again remounts the
 *  app from the top; what it had cached survives, so that is usually enough. */

import { Component, type ReactNode } from 'react';
import { StyleSheet, Text, View } from 'react-native';

import Button from './Button.tsx';
import { color, font, screenTitle } from './theme.ts';

export class Crashed extends Component<{ children: ReactNode }, { failed: boolean }> {
  state = { failed: false };

  static getDerivedStateFromError() {
    return { failed: true };
  }

  componentDidCatch(error: Error) {
    console.error('Render error', error);
  }

  render() {
    if (!this.state.failed) return this.props.children;
    return (
      <View style={styles.page}>
        <Text style={styles.title}>Something broke.</Text>
        <Text style={styles.body}>Your walk and your memories are safe. Try again.</Text>
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

const styles = StyleSheet.create({
  page: { flex: 1, backgroundColor: color.paper, justifyContent: 'center', padding: 32 },
  title: { ...screenTitle, fontSize: 28, lineHeight: 34 },
  body: { ...font.prose, fontSize: 17, color: color.inkSoft, marginTop: 8 },
  button: { marginTop: 28 },
});
