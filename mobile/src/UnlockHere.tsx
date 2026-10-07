/** The lock, low on the map where a thumb reaches, for the memory you are
 *  standing on, with ‹ › beside it when more than one is in reach. The slide
 *  that opens it is its own row under it, in App, sharing `drive` and
 *  `progress` (docs/10, "Slide to unlock"). */

import { useEffect, type RefObject } from 'react';
import { AccessibilityInfo, Pressable, StyleSheet, Text, View, useColorScheme } from 'react-native';
import type { SharedValue } from 'react-native-reanimated';
import Svg, { Circle, Defs, Line, RadialGradient, Stop } from 'react-native-svg';

import type { LocatedMemory } from './api.ts';
import Glyph from './Glyph.tsx';
import LocketUnlock, { type LocketDrive } from './LocketUnlock.tsx';
import DiamondRule from './DiamondRule.tsx';
import { color, dim, font, metal, solid, story } from './theme.ts';

type Props = {
  memory: LocatedMemory;
  /** How many memories are in reach: more than one shows ‹ ›. */
  count: number;
  onStep: (by: 1 | -1) => void;
  /** Asks the server. True opens the locket, false springs it back. */
  requestUnlock: () => Promise<boolean>;
  /** The locket is diving in: bring the memory up. */
  onDiveStart: () => void;
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
  const glow = solid(useColorScheme() === 'dark').glow;
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
      <View style={styles.row} pointerEvents="box-none">
        {many && (
          <Arrow glyph="chevron.left" name="Previous memory here" onPress={() => onStep(-1)} />
        )}
        <View pointerEvents="box-none">
          {/* It hangs on its chain from the top of the screen, and glows because
          it opens: emerald, soft, and never a ring (docs/10, "Jewel Box"). */}
          <Svg width={4} height={1000} style={styles.chain} pointerEvents="none">
            <Line
              x1={2}
              y1={0}
              x2={2}
              y2={1000}
              stroke={metal.mid}
              strokeWidth={2}
              strokeDasharray="5 4"
            />
          </Svg>
          <Svg width={GLOW} height={GLOW} style={styles.glow} pointerEvents="none">
            <Defs>
              <RadialGradient id="reach">
                <Stop offset="0" stopColor={glow} stopOpacity={1} />
                <Stop offset="0.45" stopColor={glow} stopOpacity={0.6} />
                <Stop offset="1" stopColor={glow} stopOpacity={0} />
              </RadialGradient>
            </Defs>
            <Circle cx={GLOW / 2} cy={GLOW / 2} r={GLOW / 2} fill="url(#reach)" />
          </Svg>
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
        </View>
        {many && <Arrow glyph="chevron.right" name="Next memory here" onPress={() => onStep(1)} />}
      </View>
      <DiamondRule place={styles.rule} />
      <Text style={styles.place} numberOfLines={2}>
        {memory.place.name}
      </Text>
      <Text style={styles.here}>You're standing on it</Text>
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

const LOCKET = 250;
const GLOW = LOCKET * 1.5;

const styles = StyleSheet.create({
  // Above the slide (App's `slideRow`, at 70, 64 tall), with room between.
  // ‹ › flank the locket with room between, so aiming for one cannot start
  // the hold.
  stack: {
    position: 'absolute',
    left: 24,
    right: 24,
    bottom: 70 + 64 + 56,
    alignItems: 'center',
  },
  row: { flexDirection: 'row', alignItems: 'center', justifyContent: 'center', gap: 24 },
  chain: { position: 'absolute', left: LOCKET / 2 - 2, bottom: LOCKET - 6 },
  glow: { position: 'absolute', left: (LOCKET - GLOW) / 2, top: (LOCKET - GLOW) / 2 },
  rule: { width: 160, marginTop: 8 },
  place: { ...story.title, textAlign: 'center', marginTop: 14 },
  here: { ...font.prose, fontSize: 17, color: color.inkSoft, marginTop: 6 },
  arrow: { width: 44, height: 44, alignItems: 'center', justifyContent: 'center' },
});
