/** The top of the map: what opens memories. The line is the one thing to know
 *  (the welcome one, or the keys) and rolls when it changes; out of keys, the
 *  small line says today's walk is still free. */

import { Host, Text as SwiftText } from '@expo/ui/swift-ui';
import { Animation, animation, contentTransition, font as swiftFont, foregroundColor } from '@expo/ui/swift-ui/modifiers';
import { useEffect, useRef, useState } from 'react';
import { Platform, StyleSheet, Text, View, useColorScheme, type StyleProp, type ViewStyle } from 'react-native';

import { GlassButton } from './Glass.tsx';
import Glyph from './Glyph.tsx';
import { color, label, pill, solid } from './theme.ts';
import { HOLD_MS } from './UnlockButton.tsx';
import { countDown, lineOf, type Wallet } from './wallet.ts';

type Props = {
  wallet: Wallet;
  /** A hold is under way: the key comes off here as the ring completes. */
  holding: boolean;
  /** What that hold costs: nothing on a stop of today's walk. */
  price: number;
  place: StyleProp<ViewStyle>;
  onPress: () => void;
};

export default function KeysPill({ wallet, holding, price, place, onPress }: Props) {
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
  const figure = holding ? countDown(from.current, price, tenths / 10) : wallet.figure;
  const line = lineOf(wallet, figure);
  return (
    <GlassButton
      place={place}
      style={styles.pill}
      accessibilityRole="button"
      accessibilityLabel={wallet.spoken}
      accessibilityHint="How keys and unlocking work"
      onPress={onPress}
    >
      {!wallet.starting && <Glyph name="key.fill" size={15} color={real.ember} />}
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
        {wallet.note !== '' && (
          <Text style={styles.note} numberOfLines={1}>
            {wallet.note}
          </Text>
        )}
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
