/** Google and Apple, and nothing else.
 *
 * No passwords: nothing for us to store, reset or leak, and no reset-email flow
 * to build. Apple is not a preference either - App Store review requires Sign
 * in with Apple as soon as any other third-party sign-in exists on iOS.
 *
 * What signing in buys is one thing, and the copy here says only that thing: a
 * collection that survives a new phone. It is not a gate. Everything in the app
 * works signed out, because a proximity app that asks who you are before it
 * shows you anything has the order wrong.
 *
 * Both flows end the same way - a provider-signed ID token goes to the server,
 * which decides whether it is real and which account it belongs to. The app
 * never sees a session token, because none is issued.
 *
 * **Neither button works in Expo Go.** Apple needs the entitlement and Google
 * needs the app's own URL scheme, so both want a development build. The Google
 * button hides itself when no client id is configured rather than opening a
 * browser that will fail; Apple's hides itself off iOS and on anything that
 * reports the API unavailable.
 */

import { useEffect, useState } from 'react';
import { ActivityIndicator, Platform, Pressable, StyleSheet, Text, View } from 'react-native';
import * as AppleAuthentication from 'expo-apple-authentication';
import * as Google from 'expo-auth-session/providers/google';
import * as WebBrowser from 'expo-web-browser';

import { signIn, signOut, type Profile } from './api.ts';
import { color, dim, font, label } from './theme.ts';

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

type ButtonProps = {
  device: string | null;
  onProfile: (next: Profile) => void;
  onError: (message: string | null) => void;
  onBusy: (busy: boolean) => void;
};

/**
 * Its own component because the hook throws outright with no client id -
 * "Client Id property `iosClientId` must be defined" - and a hook cannot be
 * called conditionally. Hiding the button was not enough; the whole thing has
 * to not be rendered, which is what GOOGLE_CONFIGURED decides below.
 */
function GoogleButton({ device, onProfile, onError, onBusy }: ButtonProps) {
  const [, response, prompt] = Google.useIdTokenAuthRequest(GOOGLE);

  // The flow finishes in a browser and comes back through `response` rather
  // than by resolving the prompt, so the exchange has to live in an effect.
  useEffect(() => {
    if (response?.type !== 'success' || !device) return;
    const idToken = response.params?.id_token;
    if (!idToken) {
      onError('Google did not return a sign-in token.');
      return;
    }
    onBusy(true);
    signIn('google', device, idToken)
      .then(onProfile)
      .catch(() => onError('Could not finish signing in.'))
      .finally(() => onBusy(false));
  }, [response, device, onProfile, onError, onBusy]);

  return (
    <Pressable
      style={dim(styles.action)}
      accessibilityRole="button"
      onPress={() => {
        onError(null);
        prompt().catch(() => onError('Could not open Google sign-in.'));
      }}
    >
      <Text style={styles.actionText}>Continue with Google</Text>
    </Pressable>
  );
}

type Props = {
  device: string | null;
  profile: Profile | null;
  onProfile: (next: Profile) => void;
};

export default function SignIn({ device, profile, onProfile }: Props) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [appleAvailable, setAppleAvailable] = useState(false);

  useEffect(() => {
    // iOS-only, and false on a simulator without an iCloud account signed in,
    // so it is asked rather than inferred from the platform.
    if (Platform.OS !== 'ios') return;
    AppleAuthentication.isAvailableAsync().then(setAppleAvailable).catch(() => {});
  }, []);

  const withApple = async () => {
    if (!device) return;
    setError(null);
    try {
      const credential = await AppleAuthentication.signInAsync({
        requestedScopes: [
          AppleAuthentication.AppleAuthenticationScope.FULL_NAME,
          AppleAuthentication.AppleAuthenticationScope.EMAIL,
        ],
      });
      if (!credential.identityToken) {
        setError('Apple did not return a sign-in token.');
        return;
      }
      // Apple hands the name over on the first authorization and never again,
      // so it travels now or it is lost. The server only uses it to fill a
      // blank - a name somebody chose is never overwritten.
      const name = [credential.fullName?.givenName, credential.fullName?.familyName]
        .filter(Boolean)
        .join(' ');
      setBusy(true);
      onProfile(await signIn('apple', device, credential.identityToken, name || null));
    } catch (e) {
      // Cancelling is not an error and must not leave a message behind.
      if ((e as { code?: string })?.code !== 'ERR_REQUEST_CANCELED') {
        setError('Could not finish signing in.');
      }
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
      setError('Could not sign out.');
    } finally {
      setBusy(false);
    }
  };

  const providers = profile?.providers ?? [];

  if (providers.length > 0) {
    return (
      <View style={styles.wrap}>
        <Text style={styles.note}>
          Signed in with {providers.map((p) => PROVIDER_NAME[p]).join(' and ')}. Your collection
          and anything you file follow you to a new phone.
        </Text>
        {/* The other provider stays on offer: Apple and Google on one account
            is the normal case here, not an edge one. */}
        {appleAvailable && !providers.includes('apple') && (
          <AppleAuthentication.AppleAuthenticationButton
            buttonType={AppleAuthentication.AppleAuthenticationButtonType.SIGN_IN}
            buttonStyle={AppleAuthentication.AppleAuthenticationButtonStyle.BLACK}
            cornerRadius={4}
            style={styles.apple}
            onPress={withApple}
          />
        )}
        <Pressable style={dim(styles.action)} onPress={leave} accessibilityRole="button">
          <Text style={styles.actionText}>Sign out</Text>
        </Pressable>
        {busy && <ActivityIndicator size="small" color={color.inkFaint} />}
        {error && <Text style={styles.error}>{error}</Text>}
      </View>
    );
  }

  return (
    <View style={styles.wrap}>
      <Text style={styles.note}>
        Not required for anything. It exists so a new phone does not start empty — everything you
        unlocked and everything you filed comes with you.
      </Text>

      {appleAvailable && (
        // Apple's own control, because their guidelines require their styling
        // wherever it appears.
        <AppleAuthentication.AppleAuthenticationButton
          buttonType={AppleAuthentication.AppleAuthenticationButtonType.SIGN_IN}
          buttonStyle={AppleAuthentication.AppleAuthenticationButtonStyle.BLACK}
          cornerRadius={4}
          style={styles.apple}
          onPress={withApple}
        />
      )}

      {GOOGLE_CONFIGURED && (
        <GoogleButton
          device={device}
          onProfile={onProfile}
          onError={setError}
          onBusy={setBusy}
        />
      )}

      {!appleAvailable && !GOOGLE_CONFIGURED && (
        <Text style={styles.note}>Sign-in is not available in this build.</Text>
      )}

      {busy && <ActivityIndicator size="small" color={color.inkFaint} />}
      {error && <Text style={styles.error}>{error}</Text>}
    </View>
  );
}

const styles = StyleSheet.create({
  wrap: { gap: 12 },
  note: { fontFamily: font.prose, fontSize: 15, lineHeight: 24, color: color.inkFaint },
  // Apple's button draws itself; it only takes a frame.
  apple: { height: 46, alignSelf: 'stretch' },
  action: {
    alignSelf: 'flex-start',
    borderWidth: 1,
    borderColor: color.ink,
    paddingVertical: 12,
    paddingHorizontal: 22,
    borderRadius: 4,
  },
  actionText: { ...label, color: color.ink },
  error: { fontFamily: font.mono, fontSize: 13, color: color.seal },
});
