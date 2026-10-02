/** Keys, and the subscription: a key opens one memory you stand on; a
 *  subscription opens every one, and walks are not one a day (F35, docs/10
 *  "Keys open a lock, and today's walk is free").
 *
 *  Prices come from the store, never from here. Without a RevenueCat key
 *  (the simulator, e2e) there is nothing to sell and it says so: never a
 *  button that cannot work. Paying is not what opens anything: the server
 *  reads the store back, and its Profile is the answer.
 */

import { useEffect, useState } from 'react';
import { Linking, Modal, Pressable, ScrollView, StyleSheet, Text, View } from 'react-native';
import type { PurchasesPackage } from 'react-native-purchases';

import { API_BASE, refreshSubscription, type Profile } from './api.ts';
import { buy, keyPacks, plans, restore } from './purchases.ts';
import { button, buttonText, color, dim, font, label } from './theme.ts';

// Apple's standard licence, which App Review accepts in place of our own terms.
const TERMS_URL = 'https://www.apple.com/legal/internet-services/itunes/dev/stdeula/';

type Props = {
  visible: boolean;
  onClose: () => void;
  device: string | null;
  onProfile: (next: Profile) => void;
  /** Keys before this sheet opened, so a pack bought is seen landing. */
  keys: number;
};

export default function Paywall({ visible, onClose, device, onProfile, keys }: Props) {
  const [offered, setOffered] = useState<PurchasesPackage[] | null>(null);
  const [packs, setPacks] = useState<PurchasesPackage[]>([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!visible) return;
    setError(null);
    plans()
      .then(setOffered)
      .catch(() => setOffered([]));
    keyPacks()
      .then(setPacks)
      .catch(() => setPacks([]));
  }, [visible]);

  const settle = async (pay: () => Promise<boolean>) => {
    if (!device) return;
    setBusy(true);
    setError(null);
    try {
      if (!(await pay())) return;
      const who = await refreshSubscription(device);
      onProfile(who);
      if (who.subscribed || who.keys > keys) onClose();
      else setError('Nothing bought on this account yet.');
    } catch {
      setError("That didn't go through. Try again.");
    } finally {
      setBusy(false);
    }
  };

  return (
    <Modal visible={visible} animationType="slide" presentationStyle="pageSheet" onRequestClose={onClose}>
      <ScrollView style={styles.screen} contentContainerStyle={styles.body}>
        <Text style={styles.title}>Open any memory you stand on</Text>
        <Text style={styles.note}>
          Today's walk opens for nothing, and finishing it earns a key. Anywhere else, a
          key opens one memory you're standing on.
        </Text>

        {packs.length === 0 ? (
          <Text style={styles.note} testID="keys-unavailable">Keys aren't available right now.</Text>
        ) : (
          <View style={styles.plans}>
            {packs.map((pack) => {
              const n = Number(pack.product.identifier.split('_')[1]);
              return (
                <Pressable
                  key={pack.identifier}
                  style={dim(styles.outline)}
                  disabled={busy}
                  accessibilityRole="button"
                  onPress={() => settle(() => buy(pack))}
                >
                  <Text style={styles.outlineText}>
                    {`${n} ${n === 1 ? 'key' : 'keys'} · ${pack.product.priceString}`}
                  </Text>
                </Pressable>
              );
            })}
            <Text style={styles.fine}>Bought keys never expire.</Text>
          </View>
        )}

        <Text style={styles.heading}>Or every memory, always</Text>
        {offered === null ? null : offered.length === 0 ? (
          <Text style={styles.note} testID="subscriptions-unavailable">Subscriptions aren't available right now.</Text>
        ) : (
          <View style={styles.plans}>
            {offered.map((plan, i) => (
              <Pressable
                key={plan.identifier}
                style={dim(i === 0 ? styles.solid : styles.outline)}
                disabled={busy}
                accessibilityRole="button"
                onPress={() => settle(() => buy(plan))}
              >
                <Text style={i === 0 ? styles.solidText : styles.outlineText}>
                  {`${plan.packageType === 'ANNUAL' ? 'Yearly' : 'Monthly'} · ${plan.product.priceString}`}
                </Text>
              </Pressable>
            ))}
            <Text style={styles.fine}>
              Renews automatically. Cancel anytime in your store settings.
            </Text>
            <Pressable
              style={dim(styles.link)}
              disabled={busy}
              accessibilityRole="button"
              onPress={() =>
                settle(async () => {
                  await restore();
                  return true;
                })
              }
            >
              <Text style={styles.linkText}>Restore purchases</Text>
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
            onPress={() => Linking.openURL(TERMS_URL).catch(() => {})}
          >
            <Text style={styles.linkText}>Terms of use</Text>
          </Pressable>
          <Pressable
            style={dim(styles.link)}
            accessibilityRole="link"
            onPress={() => Linking.openURL(`${API_BASE}/privacy`).catch(() => {})}
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
  heading: { ...font.displaySemi, fontSize: 19, lineHeight: 25, color: color.ink, marginTop: 12 },
  plans: { gap: 12, marginTop: 12 },
  solid: { ...button.solid },
  solidText: { ...buttonText, color: color.paper },
  outline: { ...button.outline },
  outlineText: { ...buttonText, color: color.ink },
  quiet: { ...button.quiet, marginTop: 6 },
  fine: { ...label, fontSize: 12, color: color.inkFaint },
  error: { ...font.ui, fontSize: 13, lineHeight: 20, color: color.ember },
  links: { flexDirection: 'row', gap: 24, marginTop: 12 },
  link: { alignSelf: 'flex-start' },
  linkText: {
    ...font.uiMedium,
    fontSize: 13,
    color: color.ink,
    textDecorationLine: 'underline',
  },
});
