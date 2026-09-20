/** Asked before the system dialog, not instead of it.
 *
 * The app used to fire requestForegroundPermissions on mount, which is the one
 * pattern every guide names as the mistake: a system dialog with no context,
 * one tap, permanent. Explaining first roughly doubles opt-in, and here it also
 * explains the product - "memories unlock when you stand near them" is the
 * whole pitch, and there is nowhere better to say it.
 *
 * It is a card over a working map, never a takeover. A blank first screen is a
 * store rejection (rule 1 in UI.md), and "Not now" has to leave something
 * behind.
 */

import { Pressable, StyleSheet, Text, View } from 'react-native';

import { color, font } from './theme.ts';

type Props = {
  /** True once the system has refused for good; only Settings can undo that. */
  blocked: boolean;
  onAllow: () => void;
  onDismiss: () => void;
};

export default function LocationPrimer({ blocked, onAllow, onDismiss }: Props) {
  return (
    <View style={styles.card}>
      <Text style={styles.title}>Memories unlock where they happened</Text>
      <Text style={styles.body}>
        {blocked
          ? 'Location is off for Memory Lane. Turn it on in Settings to unlock memories by standing near them.'
          : 'Walk within 150 m of a pin and you can open it. Until then you can see where the memories are, but not what they say.'}
      </Text>

      <Pressable style={styles.allow} onPress={onAllow} accessibilityRole="button">
        <Text style={styles.allowText}>{blocked ? 'Open Settings' : 'Turn on location'}</Text>
      </Pressable>
      <Pressable style={styles.dismiss} onPress={onDismiss} accessibilityRole="button">
        <Text style={styles.dismissText}>Just show me the map</Text>
      </Pressable>
    </View>
  );
}

const styles = StyleSheet.create({
  card: {
    position: 'absolute',
    left: 16,
    right: 16,
    bottom: 26,
    backgroundColor: color.paper,
    borderWidth: 1,
    borderColor: color.rule,
    borderRadius: 6,
    padding: 24,
    gap: 8,
    shadowColor: '#000',
    shadowOpacity: 0.14,
    shadowRadius: 18,
    shadowOffset: { width: 0, height: 8 },
    elevation: 6,
  },
  title: { fontFamily: font.display, fontSize: 23, lineHeight: 30, color: color.ink },
  body: { fontFamily: font.prose, fontSize: 16, lineHeight: 25, color: color.inkSoft },
  allow: {
    marginTop: 14,
    backgroundColor: color.ink,
    paddingVertical: 16,
    borderRadius: 4,
    alignItems: 'center',
  },
  allowText: {
    color: color.paper,
    fontFamily: font.monoBold,
    fontSize: 12,
    letterSpacing: 1.2,
    textTransform: 'uppercase',
  },
  dismiss: { paddingVertical: 12, alignItems: 'center' },
  dismissText: {
    fontFamily: font.monoBold,
    fontSize: 11,
    letterSpacing: 1.1,
    textTransform: 'uppercase',
    color: color.inkFaint,
  },
});
