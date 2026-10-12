/** The game menus' pieces (docs/10, "Game menus"): foil and velvet fills, the
 *  ribbon over a card's title, a panel with a foil tab, a coin, the
 *  Collector's medal and its bar. Decorative fills say nothing to VoiceOver:
 *  the words beside them do. */

import type { ReactNode } from 'react';
import {
  StyleSheet,
  Text,
  View,
  type StyleProp,
  type ViewProps,
  type ViewStyle,
} from 'react-native';
import { LinearGradient } from 'expo-linear-gradient';

import CollectorLook from './CollectorLook.tsx';
import type { ClassId } from './collector.ts';
import { color, foil, font, metal, radius, velvet } from './theme.ts';

type Box = { style?: StyleProp<ViewStyle>; children?: ReactNode };

export function Foil({ style, children }: Box) {
  return (
    <View style={[styles.clip, style]}>
      <LinearGradient
        colors={foil.colors}
        locations={[0, 0.5, 1]}
        style={StyleSheet.absoluteFill}
      />
      {children}
    </View>
  );
}

export function Velvet({ style, children, ...rest }: ViewProps) {
  return (
    <View style={[styles.clip, style]} {...rest}>
      <LinearGradient
        colors={[velvet.hi, velvet.mid, velvet.deep]}
        start={{ x: 0.15, y: 0 }}
        end={{ x: 0.85, y: 1 }}
        style={StyleSheet.absoluteFill}
      />
      {children}
    </View>
  );
}

/** "◆ THIS WEEK'S WALK ◆" over a card's title. */
export function Ribbon({ label, onVelvet }: { label: string; onVelvet?: boolean }) {
  return (
    <View style={styles.ribbon}>
      <View style={styles.diamond} />
      <Text style={[styles.ribbonText, onVelvet && { color: color.onVelvetGold }]}>
        {label.toUpperCase()}
      </Text>
      <View style={styles.diamond} />
    </View>
  );
}

/** A raised card with a foil tab naming it. */
export function Panel({ title, style, children }: Box & { title: string }) {
  return (
    <View style={[styles.panel, style]}>
      <Foil style={styles.tab}>
        <Text style={styles.tabText}>{title.toUpperCase()}</Text>
      </Foil>
      {children}
    </View>
  );
}

/** A foil coin: a stop's number, a check. */
export function Coin({ size = 32, children }: { size?: number; children: ReactNode }) {
  return (
    <Foil style={[styles.coin, { width: size, height: size, borderRadius: size / 2 }]}>
      {typeof children === 'string' || typeof children === 'number' ? (
        <Text style={[styles.coinText, { fontSize: size * 0.44 }]}>{children}</Text>
      ) : (
        children
      )}
    </Foil>
  );
}

/** The Collector in a foil ring, its rank on a coin at the foot. */
export function Medal({ id, stage, size }: { id: ClassId; stage: number; size: number }) {
  const badge = Math.max(20, Math.round(size * 0.38));
  return (
    <View style={{ width: size, height: size }}>
      <Foil style={[styles.ring, { borderRadius: size / 2 }]}>
        <View style={[styles.well, { borderRadius: size / 2 }]}>
          <CollectorLook id={id} stage={stage} size={size * 1.05} place={styles.look} />
        </View>
      </Foil>
      <View style={[styles.badge, { width: badge, height: badge, borderRadius: badge / 2 }]}>
        <Coin size={badge - 4}>{stage + 1}</Coin>
      </View>
    </View>
  );
}

/** The rank bar on velvet: foil filling a dark groove, notched in quarters.
 *  On `paper`, plum filling the track, as earned reads on paper. */
export function Bar({
  into,
  height = 10,
  paper,
}: {
  into: number;
  height?: number;
  paper?: boolean;
}) {
  const width = `${Math.round(into * 100)}%` as const;
  return (
    <View style={[styles.groove, paper && styles.track, { height, borderRadius: height / 2 }]}>
      {paper ? (
        <View style={[styles.fill, styles.plum, { width }]} />
      ) : (
        <Foil style={[styles.fill, { width }]} />
      )}
      {[0.25, 0.5, 0.75].map((at) => (
        <View key={at} style={[styles.notch, { left: `${at * 100}%` }]} />
      ))}
    </View>
  );
}

const styles = StyleSheet.create({
  clip: { overflow: 'hidden' },
  ribbon: { flexDirection: 'row', alignItems: 'center', gap: 6 },
  diamond: { width: 6, height: 6, transform: [{ rotate: '45deg' }], backgroundColor: metal.mid },
  ribbonText: { ...font.display, fontSize: 11, letterSpacing: 2, color: color.gold },
  panel: {
    backgroundColor: color.paperRaised,
    borderRadius: 20,
    borderWidth: StyleSheet.hairlineWidth,
    borderColor: color.goldLine,
    borderBottomWidth: 3,
    borderBottomColor: color.rule,
    padding: 14,
    paddingTop: 20,
    marginTop: 12,
  },
  tab: {
    position: 'absolute',
    top: -11,
    left: 14,
    paddingHorizontal: 10,
    paddingVertical: 4,
    borderRadius: 9,
  },
  tabText: { ...font.display, fontSize: 11, letterSpacing: 1.4, color: foil.text },
  coin: { alignItems: 'center', justifyContent: 'center' },
  coinText: { ...font.display, color: foil.text },
  ring: { flex: 1, padding: 3 },
  well: {
    flex: 1,
    overflow: 'hidden',
    backgroundColor: color.paperRaised,
    alignItems: 'center',
    justifyContent: 'flex-end',
  },
  look: { marginBottom: '-12%' },
  badge: {
    position: 'absolute',
    right: -4,
    bottom: -4,
    backgroundColor: velvet.deep,
    alignItems: 'center',
    justifyContent: 'center',
  },
  groove: { backgroundColor: color.scrim, overflow: 'hidden', borderRadius: radius.pill },
  fill: { position: 'absolute', top: 0, bottom: 0, left: 0, borderRadius: radius.pill },
  track: { backgroundColor: color.track },
  plum: { backgroundColor: color.plum },
  notch: { position: 'absolute', top: 0, bottom: 0, width: 1, backgroundColor: velvet.deep },
});
