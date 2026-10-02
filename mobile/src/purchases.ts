/** The store, through RevenueCat: the subscription and the key packs. Every call is a no-op or a null without a
 *  key (the simulator, e2e, a fork), and the paywall shows "not available"
 *  rather than a button that cannot work.
 *
 *  The app never decides who has paid: after a purchase or a restore it asks
 *  the server to read RevenueCat back (`refreshSubscription`), and the server's
 *  answer is the one that opens anything. docs/10, "RevenueCat sells it; our
 *  table decides". */
import { Platform } from 'react-native';
import Purchases, { type PurchasesPackage } from 'react-native-purchases';

const KEY =
  Platform.OS === 'ios'
    ? process.env.EXPO_PUBLIC_REVENUECAT_IOS_KEY
    : process.env.EXPO_PUBLIC_REVENUECAT_ANDROID_KEY;

let configured = false;

function ready(): boolean {
  if (!KEY) return false;
  if (!configured) {
    Purchases.configure({ apiKey: KEY });
    configured = true;
  }
  return true;
}

/** RevenueCat's app user id is our account id, so the webhook names a user we
 *  know. Null (signed out, or the dev-build Skip) is nobody: no purchase. */
export async function identify(userId: string | null): Promise<void> {
  if (!ready()) return;
  if (userId) await Purchases.logIn(userId);
  else if (!(await Purchases.isAnonymous())) await Purchases.logOut();
}

/** Monthly and yearly, in the store's own currency and wording. */
export async function plans(): Promise<PurchasesPackage[]> {
  if (!ready()) return [];
  const current = (await Purchases.getOfferings()).current;
  return [current?.monthly, current?.annual].filter((p): p is PurchasesPackage => !!p);
}

/** False when the person backed out of the store's sheet: not an error. */
export async function buy(plan: PurchasesPackage): Promise<boolean> {
  try {
    await Purchases.purchasePackage(plan);
    return true;
  } catch (e) {
    if ((e as { userCancelled?: boolean | null }).userCancelled) return false;
    throw e;
  }
}

export async function restore(): Promise<void> {
  if (ready()) await Purchases.restorePurchases();
}

export async function manage(): Promise<void> {
  if (ready()) await Purchases.showManageSubscriptions();
}
