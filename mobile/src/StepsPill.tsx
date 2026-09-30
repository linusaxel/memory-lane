/** The top of the map: what opens memories today. The big line is the one
 *  thing to know (free ones, the balance, or what is left to walk) and rolls
 *  when it changes; short of an unlock, a small ring fills toward it. */

import { Host, Text as SwiftText } from '@expo/ui/swift-ui';
import { Animation, animation, contentTransition, font as swiftFont, foregroundColor } from '@expo/ui/swift-ui/modifiers';
import { useEffect, useRef, useState } from 'react';
import { Platform, StyleSheet, Text, View, useColorScheme, type StyleProp, type ViewStyle } from 'react-native';
import Svg, { Circle } from 'react-native-svg';

import { GlassButton } from './Glass.tsx';
import { color, label, pill, solid } from './theme.ts';
import { HOLD_MS } from './UnlockButton.tsx';
import { countDown, type Wallet } from './wallet.ts';

const RING = 18;
const STROKE = 3;
const ARC = Math.PI * (RING - STROKE);

type Props = {
  wallet: Wallet;
  /** A hold is under way: the price counts down here as the ring fills. */
  holding: boolean;
  place: StyleProp<ViewStyle>;
  onPress: () => void;
};

export default function StepsPill({ wallet, holding, place, onPress }: Props) {
  const real = solid(useColorScheme() === 'dark');
  const [tenths, setTenths] = useState(0);
  // Held at the hold's start, so the new balance landing before the hold is
  // let go of does not take the price off twice.
  const from = useRef(wallet.figure);
  if (!holding) from.current = wallet.figure;
  useEffect(() => {
    setTenths(0);
    if (!holding) return;
    const id = setInterval(() => setTenths((t) => Math.min(t + 1, 10)), HOLD_MS / 10);
    return () => clearInterval(id);
  }, [holding]);
  const figure = holding ? countDown(from.current, wallet.price, tenths / 10) : wallet.figure;
  const line = `${figure.toLocaleString()} ${wallet.unit}`;
  return (
    <GlassButton
      place={place}
      style={styles.pill}
      accessibilityRole="button"
      accessibilityLabel={wallet.spoken}
      accessibilityHint="Counts your steps again"
      onPress={onPress}
    >
      {wallet.short > 0 && (
        <Svg width={RING} height={RING}>
          <Circle cx={RING / 2} cy={RING / 2} r={(RING - STROKE) / 2} stroke={real.rule} strokeWidth={STROKE} fill="none" />
          <Circle
            cx={RING / 2}
            cy={RING / 2}
            r={(RING - STROKE) / 2}
            stroke={real.ember}
            strokeWidth={STROKE}
            strokeLinecap="round"
            fill="none"
            strokeDasharray={`${ARC * wallet.progress} ${ARC}`}
            transform={`rotate(-90 ${RING / 2} ${RING / 2})`}
          />
        </Svg>
      )}
      <View style={styles.lines}>
        {Platform.OS === 'ios' ? (
          <Host matchContents>
            <SwiftText
              modifiers={[
                swiftFont({ design: 'rounded', weight: 'semibold', size: 15 }),
                foregroundColor(real.ink),
                contentTransition('numericText'),
                animation(Animation.spring(), figure),
              ]}
            >
              {line}
            </SwiftText>
          </Host>
        ) : (
          <Text style={styles.figure}>{line}</Text>
        )}
        <Text style={styles.note} numberOfLines={1}>
          {wallet.note}
        </Text>
      </View>
    </GlassButton>
  );
}

const styles = StyleSheet.create({
  pill,
  lines: { alignItems: 'center' },
  figure: { ...label, fontSize: 15, color: color.ink },
  note: { ...label, fontSize: 12, color: color.inkSoft },
});
