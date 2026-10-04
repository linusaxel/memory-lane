/** The lock, low on the map where a thumb reaches, for the memory you are
 *  standing on, with ‹ › beside it when more than one is in reach. The slide
 *  that opens it is the bottom row's middle, in App, sharing `drive` and
 *  `progress` (docs/10, "Slide to unlock"). */

import { useEffect, type RefObject } from 'react';
import { AccessibilityInfo, Pressable, StyleSheet, View } from 'react-native';
import type { SharedValue } from 'react-native-reanimated';

import type { LocatedMemory } from './api.ts';
import Glyph from './Glyph.tsx';
import LocketUnlock, { type Iris, type LocketDrive } from './LocketUnlock.tsx';
import { color, dim } from './theme.ts';

type Props = {
  memory: LocatedMemory;
  /** How many memories are in reach: more than one shows ‹ ›. */
  count: number;
  onStep: (by: 1 | -1) => void;
  /** Asks the server. True opens the locket, false springs it back. */
  requestUnlock: () => Promise<boolean>;
  /** The locket is diving in: bring the memory up. */
  onDiveStart: (from: Iris) => void;
  onOpened: () => void;
  error: string | null;
  /** The slide's handle on the locket, and the hold they share. */
  drive: RefObject<LocketDrive | null>;
  progress: SharedValue<number>;
};

export default function UnlockHere({
  memory,
  count,
  onStep,
  requestUnlock,
  onDiveStart,
  onOpened,
  error,
  drive,
  progress,
}: Props) {
  const many = count > 1;
  const { lat, lng } = memory.place.coordinates;
  // ‹ › brings a fresh locket, so the thumb starts over with it.
  useEffect(() => {
    progress.value = 0;
  }, [memory.id, progress]);

  useEffect(() => {
    if (error) AccessibilityInfo.announceForAccessibility(error);
  }, [error]);

  return (
    <View style={styles.stack} pointerEvents="box-none">
      {many && (
        <Arrow glyph="chevron.left" name="Previous memory here" onPress={() => onStep(-1)} />
      )}
      <LocketUnlock
        // A fresh locket per memory: ‹ › must not carry a half-turned key over.
        key={memory.id}
        locket={memory.locket}
        placeName={memory.place.name}
        coordinates={`${Math.abs(lat).toFixed(2)} ${lat < 0 ? 'S' : 'N'} · ${Math.abs(lng).toFixed(2)} ${lng < 0 ? 'W' : 'E'}`}
        requestUnlock={requestUnlock}
        onDiveStart={onDiveStart}
        onOpened={onOpened}
        size={LOCKET}
        ref={drive}
        progress={progress}
      />
      {many && <Arrow glyph="chevron.right" name="Next memory here" onPress={() => onStep(1)} />}
    </View>
  );
}

type ArrowProps = { glyph: 'chevron.left' | 'chevron.right'; name: string; onPress: () => void };

function Arrow({ glyph, name, onPress }: ArrowProps) {
  return (
    <Pressable
      style={dim(styles.arrow)}
      onPress={onPress}
      accessibilityRole="button"
      accessibilityLabel={name}
    >
      <Glyph name={glyph} size={22} weight="semibold" color={color.ink} />
    </Pressable>
  );
}

const LOCKET = 180;

const styles = StyleSheet.create({
  // Above the bottom row (App's `bottom`, at 70), whose middle is the slide.
  // ‹ › flank the locket with room between, so aiming for one cannot start
  // the hold.
  stack: {
    position: 'absolute',
    left: 16,
    right: 16,
    bottom: 134,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 24,
  },
  arrow: { width: 44, height: 44, alignItems: 'center', justifyContent: 'center' },
});
