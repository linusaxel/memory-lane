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
    bottom: 34,
    backgroundColor: '#fff',
    borderRadius: 20,
    padding: 22,
    gap: 6,
    shadowColor: '#000',
    shadowOpacity: 0.18,
    shadowRadius: 16,
    shadowOffset: { width: 0, height: 6 },
    elevation: 6,
  },
  title: { fontSize: 20, fontWeight: '700', color: '#18181b', letterSpacing: -0.4 },
  body: { fontSize: 15, lineHeight: 22, color: '#52525b' },
  allow: {
    marginTop: 12,
    backgroundColor: '#18181b',
    paddingVertical: 15,
    borderRadius: 12,
    alignItems: 'center',
  },
  allowText: { color: '#fff', fontSize: 16, fontWeight: '600' },
  dismiss: { paddingVertical: 10, alignItems: 'center' },
  dismissText: { color: '#71717a', fontSize: 15 },
});
