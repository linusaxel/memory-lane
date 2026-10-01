/** The lock, alone in the middle of the map, for the memory you are standing
 *  on. No words: a hold opens the sheet on the story (docs/10, "The lock
 *  alone"). */

import { Pressable, StyleSheet, View } from 'react-native';

import Approach from './Approach.tsx';
import UnlockButton from './UnlockButton.tsx';
import { shortfall } from './wallet.ts';

type Props = {
  onUnlock: () => void;
  onHold: (holding: boolean) => void;
  busy: boolean;
  error: string | null;
  /** Steps still to walk before this opens. Then there is no ring to hold,
   *  only a faded lock that offers the way round it. */
  short: number;
  onSkip: () => void;
};

export default function UnlockHere({ onUnlock, onHold, busy, error, short, onSkip }: Props) {
  return (
    <View style={styles.centre} pointerEvents="box-none">
      {short > 0 ? (
        <Pressable
          accessibilityRole="button"
          accessibilityLabel={shortfall(short)}
          accessibilityHint="Skip the steps"
          onPress={onSkip}
        >
          <Approach meters={0} radius={1} size={136} />
        </Pressable>
      ) : (
        <UnlockButton onUnlock={onUnlock} onHold={onHold} busy={busy} error={error} />
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  centre: { ...StyleSheet.absoluteFill, alignItems: 'center', justifyContent: 'center' },
});
