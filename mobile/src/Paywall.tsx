/** The subscription: more than one walk a day (F35, docs/10 "A walk
 *  planner, nothing else"). Keys are earned, never sold.
 *
 *  Prices come from the store, never from here. Without a RevenueCat key
 *  (the simulator, e2e) there is nothing to sell and it says so: never a
 *  button that cannot work. Paying is not what opens anything: the server
 *  reads the store back, and its Profile is the answer.
 */

import { useEffect, useState } from 'react';
import {
  Image,
  Modal,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  View,
  useColorScheme,
  useWindowDimensions,
} from 'react-native';
import type { PurchasesPackage } from 'react-native-purchases';
import Svg, { Defs, Ellipse, Path, RadialGradient, Stop } from 'react-native-svg';

import { API_BASE, refreshSubscription, type Profile } from './api.ts';
import { buy, plans, restore } from './purchases.ts';
import { openLink } from './link.ts';
import Button from './Button.tsx';
import CloseButton from './CloseButton.tsx';
import Glyph from './Glyph.tsx';
import { LOCKETS } from './lockets.ts';
import {
  color,
  dim,
  foil,
  font,
  label,
  metal,
  radius,
  screenTitle,
  solid,
  velvet,
} from './theme.ts';

// Apple's standard licence, which App Review accepts in place of our own terms.
const TERMS_URL = 'https://www.apple.com/legal/internet-services/itunes/dev/stdeula/';

type Props = {
  visible: boolean;
  onClose: () => void;
  device: string | null;
  profile: Profile | null;
  onProfile: (next: Profile) => void;
};

/** The pitch is your own walking so far, once there is any: xp counts only
 *  finished walks. A count still at zero says nothing. */
function soFar(profile: Profile | null): string | null {
  if (!profile || profile.xp <= 0) return null;
  const parts: string[] = [];
  const { unlocked, streak, steps } = profile;
  if (unlocked > 0) parts.push(`${unlocked} ${unlocked === 1 ? 'memory' : 'memories'} opened`);
  if (streak > 1) parts.push(`${streak} days in a row`);
  if (steps > 0) parts.push(`${steps.toLocaleString()} steps`);
  return parts.length ? `So far: ${parts.join(' · ')}` : null;
}

export default function Paywall({ visible, onClose, device, profile, onProfile }: Props) {
  const [offered, setOffered] = useState<PurchasesPackage[] | null>(null);
  const [chosen, setChosen] = useState(0);
  // What is paying: Subscribe or Restore spins while the other waits.
  const [paying, setPaying] = useState<string | null>(null);
  const busy = paying != null;
  const pitch = soFar(profile);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!visible) return;
    setError(null);
    setChosen(0);
    plans()
      .then(setOffered)
      .catch(() => setOffered([]));
  }, [visible]);

  const settle = async (which: string, pay: () => Promise<boolean>) => {
    if (!device) return;
    setPaying(which);
    setError(null);
    try {
      if (!(await pay())) return;
      const who = await refreshSubscription(device);
      onProfile(who);
      if (who.subscribed) onClose();
      else setError('Nothing bought on this account yet.');
    } catch {
      setError("That didn't go through. Try again.");
    } finally {
      setPaying(null);
    }
  };
  const plan = offered?.[chosen];

  return (
    <Modal
      visible={visible}
      animationType="slide"
      presentationStyle="pageSheet"
      onRequestClose={onClose}
    >
      <ScrollView style={styles.screen} contentContainerStyle={styles.body}>
        <Velvet />
        <Text style={styles.title}>More than one walk a day</Text>
        {pitch && (
          <Text style={styles.pitch} testID="paywall-so-far">
            {pitch}
          </Text>
        )}
        <View style={styles.perks}>
          <Perk glyph="infinity" text="As many walks a day as you like" />
          <Perk glyph="number" text="Walks that lean towards your themes and years" />
          <Perk glyph="gift" text="Your first walk each day stays free" />
        </View>

        {offered === null ? null : offered.length === 0 ? (
          <Text style={styles.note} testID="subscriptions-unavailable">
            Subscriptions aren't available right now.
          </Text>
        ) : (
          <>
            <View style={styles.plans}>
              {offered.map((option, i) => (
                <PlanCard
                  key={option.identifier}
                  plan={option}
                  on={i === chosen}
                  onPress={() => setChosen(i)}
                />
              ))}
            </View>
            <Button
              kind="foil"
              label="Subscribe"
              busy={paying === 'buy'}
              disabled={busy || !plan}
              onPress={() => plan && settle('buy', () => buy(plan))}
            />
          </>
        )}
        {error && <Text style={styles.error}>{error}</Text>}

        <View style={styles.row}>
          {!!offered?.length && (
            <>
              <Button
                kind="text"
                label="Restore purchase"
                busy={paying === 'restore'}
                disabled={busy}
                onPress={() =>
                  settle('restore', async () => {
                    await restore();
                    return true;
                  })
                }
              />
              <Text style={styles.dot}>·</Text>
            </>
          )}
          <Button kind="text" label="Not now" onPress={onClose} />
        </View>
        <Text style={styles.fine}>Renews automatically. Cancel any time in Settings.</Text>
        <View style={styles.row}>
          <Pressable
            style={dim()}
            accessibilityRole="link"
            onPress={() => openLink(TERMS_URL).catch(() => {})}
          >
            <Text style={styles.link}>Terms of use</Text>
          </Pressable>
          <Pressable
            style={dim()}
            accessibilityRole="link"
            onPress={() => openLink(`${API_BASE}/privacy`).catch(() => {})}
          >
            <Text style={styles.link}>Privacy policy</Text>
          </Pressable>
        </View>
        <CloseButton onPress={onClose} place={styles.close} />
      </ScrollView>
    </Modal>
  );
}

/** The six lockets laid out on plum velvet: what a year of walking earns. */
function Velvet() {
  const { width } = useWindowDimensions();
  const dark = useColorScheme() === 'dark';
  const w = Math.min(width - 48, 420);
  const h = w * 0.52;
  const size = w / 7.2;
  return (
    <View style={{ width: w, height: h, alignSelf: 'center' }}>
      <Svg width={w} height={h}>
        <Defs>
          <RadialGradient id="velvet" cx="40%" cy="30%" r="75%">
            <Stop offset="0" stopColor={velvet.hi} />
            <Stop offset="0.6" stopColor={velvet.mid} />
            <Stop offset="1" stopColor={velvet.deep} />
          </RadialGradient>
        </Defs>
        <Ellipse
          cx={w / 2}
          cy={h / 2}
          rx={w / 2 - 2}
          ry={h / 2 - 2}
          fill="url(#velvet)"
          stroke={dark ? metal.rim : 'none'}
          strokeOpacity={0.6}
        />
        <Ellipse
          cx={w / 2}
          cy={h / 2}
          rx={w / 2 - 14}
          ry={h / 2 - 12}
          fill="none"
          stroke={metal.light}
          strokeOpacity={0.55}
          strokeDasharray="4 5"
        />
        <Path
          d={`M${w / 2} ${h - 34} l6 6 -6 6 -6 -6z`}
          fill={solid(true).seal}
          stroke={metal.mid}
        />
      </Svg>
      {LOCKETS.map((locket, i) => {
        // Strung along a smile, the middle two highest.
        const t = (i - 2.5) / 2.5;
        const x = w / 2 + t * (w / 2 - size * 0.95) - size / 2;
        const y = h * 0.16 + t * t * h * 0.16;
        return (
          <Image
            key={locket.id}
            source={locket.opened}
            style={{ position: 'absolute', left: x, top: y, width: size, height: size * 1.25 }}
            resizeMode="contain"
          />
        );
      })}
    </View>
  );
}

function Perk({ glyph, text }: { glyph: 'infinity' | 'number' | 'gift'; text: string }) {
  return (
    <View style={styles.perk}>
      <View style={styles.perkIcon}>
        <Glyph name={glyph} size={17} weight="semibold" color={color.gold} />
      </View>
      <Text style={styles.perkText}>{text}</Text>
    </View>
  );
}

function PlanCard({
  plan,
  on,
  onPress,
}: {
  plan: PurchasesPackage;
  on: boolean;
  onPress: () => void;
}) {
  const yearly = plan.packageType === 'ANNUAL';
  return (
    <Pressable
      style={dim([styles.plan, on && styles.planOn])}
      onPress={onPress}
      accessibilityRole="radio"
      accessibilityState={{ selected: on }}
      accessibilityLabel={`${yearly ? 'Yearly' : 'Monthly'}, ${plan.product.priceString}`}
    >
      {yearly && (
        <View style={styles.best}>
          <Text style={styles.bestText}>Best value</Text>
        </View>
      )}
      <View style={styles.planTop}>
        <Text style={styles.planName}>{yearly ? 'Yearly' : 'Monthly'}</Text>
        <View style={[styles.check, on && styles.checkOn]}>
          {on && <Glyph name="checkmark" size={11} weight="bold" color={color.paper} />}
        </View>
      </View>
      <Text style={styles.price} adjustsFontSizeToFit numberOfLines={1}>
        {plan.product.priceString}
        <Text style={styles.per}>{yearly ? ' / year' : ' / month'}</Text>
      </Text>
      <Text style={styles.fineLeft}>
        {yearly && plan.product.pricePerMonthString
          ? `${plan.product.pricePerMonthString} a month`
          : yearly
            ? 'Billed once a year'
            : 'Billed every month'}
      </Text>
    </Pressable>
  );
}

const styles = StyleSheet.create({
  screen: { flex: 1, backgroundColor: color.paper },
  body: { paddingHorizontal: 24, paddingTop: 44, paddingBottom: 56, gap: 16 },
  close: { position: 'absolute', top: 16, right: 16 },
  title: { ...screenTitle, textAlign: 'center', marginTop: 8 },
  pitch: { ...font.uiBold, fontSize: 16, color: color.plum, textAlign: 'center', marginTop: -8 },
  note: { ...font.prose, fontSize: 16, lineHeight: 24, color: color.inkSoft, textAlign: 'center' },
  perks: { gap: 12, marginVertical: 4 },
  perk: { flexDirection: 'row', alignItems: 'center', gap: 14 },
  perkIcon: {
    width: 40,
    height: 40,
    borderRadius: 20,
    backgroundColor: color.quiet,
    alignItems: 'center',
    justifyContent: 'center',
  },
  perkText: { ...font.uiMedium, flex: 1, fontSize: 17, lineHeight: 23, color: color.ink },
  plans: { flexDirection: 'row', gap: 12, marginTop: 10 },
  plan: {
    flex: 1,
    padding: 14,
    paddingTop: 16,
    gap: 4,
    borderRadius: radius.card - 6,
    borderWidth: 1,
    borderColor: color.rule,
    backgroundColor: color.paperRaised,
  },
  planOn: { borderWidth: 2, borderColor: color.gold, backgroundColor: color.quiet },
  planTop: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' },
  planName: { ...font.uiBold, fontSize: 16, color: color.ink },
  check: {
    width: 22,
    height: 22,
    borderRadius: 11,
    borderWidth: 1.5,
    borderColor: color.rule,
    alignItems: 'center',
    justifyContent: 'center',
  },
  checkOn: { backgroundColor: color.gold, borderColor: color.gold },
  price: { ...font.title, fontSize: 24, lineHeight: 30, color: color.ink },
  per: { ...font.title, fontSize: 18, color: color.inkSoft },
  best: {
    position: 'absolute',
    top: -11,
    left: 12,
    paddingHorizontal: 10,
    paddingVertical: 2,
    borderRadius: radius.pill,
    backgroundColor: metal.light,
  },
  bestText: { ...font.uiBold, fontSize: 12, color: foil.text },
  row: { flexDirection: 'row', justifyContent: 'center', alignItems: 'center', gap: 12 },
  dot: { ...label, color: color.inkFaint },
  fine: { ...label, fontWeight: '500', textAlign: 'center' },
  fineLeft: { ...label, fontWeight: '500', fontSize: 12 },
  error: { ...font.ui, fontSize: 14, lineHeight: 20, color: color.danger, textAlign: 'center' },
  link: { ...font.uiMedium, fontSize: 13, color: color.inkFaint, textDecorationLine: 'underline' },
});
