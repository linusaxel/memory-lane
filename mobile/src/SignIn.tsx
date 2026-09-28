/** Google and Apple, and nothing else - and nothing before it.
 *
 * No passwords: nothing for us to store, reset or leak, and no reset-email flow
 * to build. Apple is not a preference either - App Store review requires Sign
 * in with Apple as soon as any other third-party sign-in exists on iOS.
 *
 * It is the gate: no account, no app (docs/10, *Sign-in comes first*). The
 * screen is the whole onboarding: the logo, the name, one line, and two buttons.
 *
 * Both flows end the same way - a provider-signed ID token goes to the server,
 * which decides whether it is real and which account it belongs to. The app
 * never sees a session token, because none is issued.
 *
 * **Neither button works in Expo Go.** Apple needs the entitlement and Google
 * needs the app's own URL scheme, so both want a development build. The Google
 * button hides itself when no client id is configured rather than opening a
 * browser that will fail; Apple's hides itself off iOS and on anything that
 * reports the API unavailable. A dev build therefore gets a way past the gate
 * that a release build cannot take: see `Skip` below.
 */

import { useEffect, useState } from 'react';
import {
  ActivityIndicator,
  Platform,
  Pressable,
  StyleSheet,
  Text,
  View,
  useColorScheme,
} from 'react-native';
import AsyncStorage from '@react-native-async-storage/async-storage';
import * as AppleAuthentication from 'expo-apple-authentication';
import * as Google from 'expo-auth-session/providers/google';
import * as WebBrowser from 'expo-web-browser';
import { useSafeAreaInsets } from 'react-native-safe-area-context';

import { deleteAccount, fetchProfile, signIn, signOut, type Profile } from './api.ts';
import { LogoTile } from './StartupLogo.tsx';
import { button, buttonText, color, dim, font, label } from './theme.ts';

// Closes the browser tab the moment the redirect comes back. Without it the
// person is left staring at a finished Google page wondering what to tap.
WebBrowser.maybeCompleteAuthSession();

/**
 * Set at dev-server start, and baked into the bundle. Absent in Expo Go and in
 * any checkout that has not been given real client ids - which is the normal
 * state of this repo, so the button is conditional rather than broken.
 */
const GOOGLE = {
  iosClientId: process.env.EXPO_PUBLIC_GOOGLE_IOS_CLIENT_ID,
  androidClientId: process.env.EXPO_PUBLIC_GOOGLE_ANDROID_CLIENT_ID,
  webClientId: process.env.EXPO_PUBLIC_GOOGLE_WEB_CLIENT_ID,
};

const PROVIDER_NAME = { google: 'Google', apple: 'Apple' } as const;

/** True only when this build could actually complete a Google sign-in. */
const GOOGLE_CONFIGURED = !!(
  GOOGLE.iosClientId ||
  GOOGLE.androidClientId ||
  GOOGLE.webClientId
);

const KEY = 'memorylane.signed-in.v1';

/** The last answer the server gave, so a signed-in person with no network is
 *  not stopped at the gate (F10, F16). The server's profile is the truth; this
 *  only decides what to show before it arrives, or when it cannot. */
export async function loadSignedIn(): Promise<boolean> {
  try {
    return (await AsyncStorage.getItem(KEY)) === 'true';
  } catch {
    return false;
  }
}

export async function saveSignedIn(on: boolean): Promise<void> {
  try {
    await (on ? AsyncStorage.setItem(KEY, 'true') : AsyncStorage.removeItem(KEY));
  } catch {
    // Worst case: the gate shows until the profile answers.
  }
}

type Setters = {
  device: string | null;
  onProfile: (next: Profile) => void;
  onError: (message: string | null) => void;
  onBusy: (busy: boolean) => void;
};

/** iOS-only, and false on a simulator without an iCloud account signed in, so
 *  it is asked rather than inferred from the platform. */
function useAppleAvailable() {
  const [available, setAvailable] = useState(false);
  useEffect(() => {
    if (Platform.OS !== 'ios') return;
    AppleAuthentication.isAvailableAsync().then(setAvailable).catch(() => {});
  }, []);
  return available;
}

async function withApple({ device, onProfile, onError, onBusy }: Setters, linkToken?: string) {
  if (!device) return;
  onError(null);
  try {
    const credential = await AppleAuthentication.signInAsync({
      requestedScopes: [
        AppleAuthentication.AppleAuthenticationScope.FULL_NAME,
        AppleAuthentication.AppleAuthenticationScope.EMAIL,
      ],
    });
    if (!credential.identityToken) {
      onError("Apple sign-in didn't work. Try again.");
      return;
    }
    // Apple hands the name over on the first authorization and never again,
    // so it travels now or it is lost. The server only uses it to fill a
    // blank - a name somebody chose is never overwritten.
    const name = [credential.fullName?.givenName, credential.fullName?.familyName]
      .filter(Boolean)
      .join(' ');
    onBusy(true);
    onProfile(await signIn('apple', device, credential.identityToken, name || null, linkToken));
  } catch (e) {
    // Cancelling is not an error and must not leave a message behind.
    if ((e as { code?: string })?.code !== 'ERR_REQUEST_CANCELED') {
      onError("Sign-in didn't finish. Try again.");
    }
  } finally {
    onBusy(false);
  }
}

/** Apple's own control, because their guidelines require their styling
 *  wherever it appears. Black would vanish on the dark paper, and a native
 *  button cannot take a DynamicColorIOS pair, so it is asked. */
function AppleButton({ onPress, ...props }: Setters & { onPress?: () => void }) {
  const dark = useColorScheme() === 'dark';
  return (
    <AppleAuthentication.AppleAuthenticationButton
      buttonType={AppleAuthentication.AppleAuthenticationButtonType.CONTINUE}
      buttonStyle={
        dark
          ? AppleAuthentication.AppleAuthenticationButtonStyle.WHITE
          : AppleAuthentication.AppleAuthenticationButtonStyle.BLACK
      }
      cornerRadius={26}
      style={styles.apple}
      onPress={onPress ?? (() => withApple(props))}
    />
  );
}

/**
 * Its own component because the hook throws outright with no client id -
 * "Client Id property `iosClientId` must be defined" - and a hook cannot be
 * called conditionally. Hiding the button was not enough; the whole thing has
 * to not be rendered, which is what GOOGLE_CONFIGURED decides below.
 */
function GoogleButton({ device, onProfile, onError, onBusy }: Setters) {
  const [, response, prompt] = Google.useIdTokenAuthRequest(GOOGLE);

  // The flow finishes in a browser and comes back through `response` rather
  // than by resolving the prompt, so the exchange has to live in an effect.
  useEffect(() => {
    if (response?.type !== 'success' || !device) return;
    const idToken = response.params?.id_token;
    if (!idToken) {
      onError("Google sign-in didn't work. Try again.");
      return;
    }
    onBusy(true);
    signIn('google', device, idToken)
      .then(onProfile)
      .catch(() => onError("Sign-in didn't finish. Try again."))
      .finally(() => onBusy(false));
  }, [response, device, onProfile, onError, onBusy]);

  return (
    <Pressable
      style={dim(styles.google)}
      accessibilityRole="button"
      onPress={() => {
        onError(null);
        prompt().catch(() => onError("Couldn't open Google sign-in."));
      }}
    >
      <Text style={styles.googleText}>Continue with Google</Text>
    </Pressable>
  );
}

/** Apple onto a Google account. Google again first: the server won't add a
 *  sign-in on the device id alone, or anyone holding it could add their own. */
function LinkApple(props: Setters) {
  const [, response, prompt] = Google.useIdTokenAuthRequest(GOOGLE);

  // Keyed on the response alone: re-running on every new `props` would open
  // Apple's sheet again each render.
  useEffect(() => {
    if (response?.type !== 'success') return;
    const proof = response.params?.id_token;
    if (!proof) {
      props.onError("Google sign-in didn't work. Try again.");
      return;
    }
    withApple(props, proof);
  }, [response]);

  return (
    <AppleButton
      {...props}
      onPress={() => {
        props.onError(null);
        prompt().catch(() => props.onError("Couldn't open Google sign-in."));
      }}
    />
  );
}

type ScreenProps = {
  device: string | null;
  onProfile: (next: Profile) => void;
  /** Dev builds only: past the gate with no account. */
  onSkip: () => void;
};

/** The first screen, and the only one until an account is attached. */
export function SignInScreen({ device, onProfile, onSkip }: ScreenProps) {
  const insets = useSafeAreaInsets();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const appleAvailable = useAppleAvailable();
  const setters = { device, onProfile, onError: setError, onBusy: setBusy };

  return (
    <View style={[styles.screen, { paddingTop: insets.top, paddingBottom: insets.bottom + 24 }]}>
      {/* Where StartupLogo left it, so the logo lands and the page grows
          around it rather than cutting to something new. */}
      <View style={styles.hero}>
        <LogoTile size={120} />
        <Text style={styles.title}>Memory Lane</Text>
        <Text style={styles.tagline}>
          The corner you pass every day has a story. Walk there to read it.
        </Text>
      </View>

      <View style={styles.actions}>
        {appleAvailable && <AppleButton {...setters} />}
        {GOOGLE_CONFIGURED && <GoogleButton {...setters} />}
        {!appleAvailable && !GOOGLE_CONFIGURED && (
          <Text style={styles.note}>Sign-in is not available in this build.</Text>
        )}
        {busy && <ActivityIndicator size="small" color={color.inkFaint} />}
        {error && <Text style={styles.error}>{error}</Text>}
        {/* Metro strips this from a release bundle, the same guarantee
            devLocation.ts rests on. A button rather than an EXPO_PUBLIC_DEV_*
            knob: e2e/run.sh blanks those, and this way e2e drives the gate. */}
        {__DEV__ && (
          <Pressable style={dim(styles.skip)} onPress={onSkip} accessibilityRole="button">
            <Text style={styles.skipText}>Skip (dev build)</Text>
          </Pressable>
        )}
      </View>
    </View>
  );
}

type Props = {
  device: string | null;
  profile: Profile | null;
  onProfile: (next: Profile) => void;
};

/** The journal's Account section. Only ever seen signed in (or skipped past in
 *  a dev build): which sign-ins are attached, the other one, and sign out -
 *  which lands back on SignInScreen. */
export default function SignIn({ device, profile, onProfile }: Props) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const appleAvailable = useAppleAvailable();
  const providers = profile?.providers ?? [];
  // Two presses, as Submit's delete: this app never uses a system dialog.
  const [confirmingDelete, setConfirmingDelete] = useState(false);

  const remove = async () => {
    if (!device) return;
    if (!confirmingDelete) {
      setConfirmingDelete(true);
      return;
    }
    setBusy(true);
    try {
      await deleteAccount(device);
      onProfile(await fetchProfile(device));
    } catch {
      setError("Couldn't delete the account. Try again.");
    } finally {
      setBusy(false);
    }
  };

  const leave = async () => {
    if (!device) return;
    setBusy(true);
    try {
      onProfile(await signOut(device));
    } catch {
      setError("Couldn't sign out. Try again.");
    } finally {
      setBusy(false);
    }
  };

  return (
    <View style={styles.wrap}>
      <Text style={styles.note}>
        {providers.length > 0
          ? `Signed in with ${providers.map((p) => PROVIDER_NAME[p]).join(' and ')}. Everything you unlock or leave follows you to a new phone.`
          : 'Not signed in: this dev build skipped the sign-in screen.'}
      </Text>
      {/* The other provider stays on offer: Apple and Google on one account
          is the normal case here, not an edge one. */}
      {appleAvailable &&
        GOOGLE_CONFIGURED &&
        providers.includes('google') &&
        !providers.includes('apple') && (
          <LinkApple device={device} onProfile={onProfile} onError={setError} onBusy={setBusy} />
        )}
      <Pressable style={dim(styles.action)} onPress={leave} accessibilityRole="button">
        <Text style={styles.actionText}>Sign out</Text>
      </Pressable>
      {confirmingDelete && (
        <Text style={styles.note}>
          Your memories, photos, notes and sign-ins are deleted for good. A
          subscription is cancelled in the App Store or Google Play, not here.
        </Text>
      )}
      <Pressable style={dim(styles.action)} onPress={remove} accessibilityRole="button">
        <Text style={styles.deleteText}>
          {confirmingDelete ? 'Delete for good' : 'Delete account'}
        </Text>
      </Pressable>
      {busy && <ActivityIndicator size="small" color={color.inkFaint} />}
      {error && <Text style={styles.error}>{error}</Text>}
    </View>
  );
}

const styles = StyleSheet.create({
  screen: { flex: 1, backgroundColor: color.paper, paddingHorizontal: 32 },
  hero: { flex: 1, alignItems: 'center', justifyContent: 'center', gap: 20 },
  title: { ...font.display, fontSize: 34, color: color.ink, marginTop: 8 },
  tagline: {
    ...font.prose,
    fontSize: 17,
    lineHeight: 26,
    color: color.inkSoft,
    textAlign: 'center',
    maxWidth: 280,
  },
  actions: { gap: 12, alignItems: 'stretch' },
  google: { ...button.outline, height: 52, paddingVertical: 0 },
  googleText: { ...buttonText, color: color.ink },
  skip: { alignSelf: 'center', paddingVertical: 10, paddingHorizontal: 16 },
  skipText: { ...label },
  wrap: { gap: 12 },
  note: { ...font.prose, fontSize: 15, lineHeight: 24, color: color.inkFaint },
  // Apple's button draws itself; it only takes a frame.
  apple: { height: 52, alignSelf: 'stretch' },
  action: { ...button.outline, alignSelf: 'flex-start' },
  actionText: { ...buttonText, color: color.ink },
  deleteText: { ...buttonText, color: color.ember },
  error: { ...font.ui, fontSize: 13, color: color.ember, textAlign: 'center' },
});
