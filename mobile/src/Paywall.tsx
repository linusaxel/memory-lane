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
  ActivityIndicator,
  Modal,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  View,
} from 'react-native';
import type { PurchasesPackage } from 'react-native-purchases';

import { API_BASE, refreshSubscription, type Profile } from './api.ts';
import { buy, plans, restore } from './purchases.ts';
import { openLink } from './link.ts';
import { button, buttonText, color, dim, font, label } from './theme.ts';

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
  return parts.length ? `So far: ${parts.join(' · ')}.` : null;
}

export default function Paywall({ visible, onClose, device, profile, onProfile }: Props) {
  const [offered, setOffered] = useState<PurchasesPackage[] | null>(null);
  // Which button is paying: it spins while the others wait.
  const [paying, setPaying] = useState<string | null>(null);
  const busy = paying != null;
  const pitch = soFar(profile);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!visible) return;
    setError(null);
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

  return (
    <Modal
      visible={visible}
      animationType="slide"
      presentationStyle="pageSheet"
      onRequestClose={onClose}
    >
      <ScrollView style={styles.screen} contentContainerStyle={styles.body}>
        <Text style={styles.title}>More than one walk a day</Text>
        {pitch && (
          <Text style={styles.fine} testID="paywall-so-far">
            {pitch}
          </Text>
        )}
        <Text style={styles.note}>
          Another loop past memories you haven't heard yet, whenever the day leaves room, and walks
          that lean towards the themes and years you like. Your first walk each day stays free.
        </Text>

        {offered === null ? null : offered.length === 0 ? (
          <Text style={styles.note} testID="subscriptions-unavailable">
            Subscriptions aren't available right now.
          </Text>
        ) : (
          <View style={styles.plans}>
            {offered.map((plan, i) => (
              <Pressable
                key={plan.identifier}
                style={dim(i === 0 ? styles.solid : styles.outline)}
                disabled={busy}
                accessibilityRole="button"
                onPress={() => settle(plan.identifier, () => buy(plan))}
              >
                {paying === plan.identifier ? (
                  <ActivityIndicator color={i === 0 ? color.paper : color.ink} />
                ) : (
                  <Text style={i === 0 ? styles.solidText : styles.outlineText}>
                    {`${plan.packageType === 'ANNUAL' ? 'Yearly' : 'Monthly'} · ${plan.product.priceString} ›`}
                  </Text>
                )}
                {plan.packageType === 'ANNUAL' && plan.product.pricePerMonthString && (
                  <Text style={i === 0 ? styles.solidSub : styles.fine}>
                    {`${plan.product.pricePerMonthString} a month`}
                  </Text>
                )}
              </Pressable>
            ))}
            <Text style={styles.fine}>
              No commitment. Renews automatically; cancel anytime in your store settings.
            </Text>
            <Pressable
              style={dim(styles.link)}
              disabled={busy}
              accessibilityRole="button"
              onPress={() =>
                settle('restore', async () => {
                  await restore();
                  return true;
                })
              }
            >
              {paying === 'restore' ? (
                <ActivityIndicator color={color.inkSoft} />
              ) : (
                <Text style={styles.linkText}>Restore purchases</Text>
              )}
            </Pressable>
          </View>
        )}
        {error && <Text style={styles.error}>{error}</Text>}

        <Pressable style={dim(styles.quiet)} onPress={onClose} accessibilityRole="button">
          <Text style={styles.outlineText}>Not now</Text>
        </Pressable>

        <View style={styles.links}>
          <Pressable
            style={dim(styles.link)}
            accessibilityRole="link"
            onPress={() => openLink(TERMS_URL).catch(() => {})}
          >
            <Text style={styles.linkText}>Terms of use</Text>
          </Pressable>
          <Pressable
            style={dim(styles.link)}
            accessibilityRole="link"
            onPress={() => openLink(`${API_BASE}/privacy`).catch(() => {})}
          >
            <Text style={styles.linkText}>Privacy policy</Text>
          </Pressable>
        </View>
      </ScrollView>
    </Modal>
  );
}

const styles = StyleSheet.create({
  screen: { flex: 1, backgroundColor: color.paper },
  body: { paddingHorizontal: 24, paddingTop: 36, paddingBottom: 72, gap: 18 },
  title: { ...font.display, fontSize: 34, lineHeight: 40, color: color.ink },
  note: { ...font.prose, fontSize: 17, lineHeight: 27, color: color.inkFaint },
  plans: { gap: 12, marginTop: 12 },
  solid: { ...button.solid },
  solidText: { ...buttonText, color: color.paper },
  solidSub: { ...label, fontSize: 12, color: color.paper },
  outline: { ...button.outline },
  outlineText: { ...buttonText, color: color.ink },
  quiet: { ...button.quiet, marginTop: 6 },
  fine: { ...label, fontSize: 12, color: color.inkFaint },
  error: { ...font.ui, fontSize: 13, lineHeight: 20, color: color.gold },
  links: { flexDirection: 'row', gap: 24, marginTop: 12 },
  link: { alignSelf: 'flex-start' },
  linkText: {
    ...font.uiMedium,
    fontSize: 13,
    color: color.ink,
    textDecorationLine: 'underline',
  },
});
