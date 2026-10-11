/** A screen opened on launch, instead of by a finger.
 *
 * Only under `__DEV__` — Metro strips the branch from a release bundle, so this
 * cannot reach a shipped app. The sibling of `devLocation.ts`, and it exists for
 * the same reason: to remove a manual step from looking at the app.
 *
 * What it buys is larger than it looks. There is no UI automation for the iOS
 * Simulator here — `idb` is not installed and `osascript` has no assistive
 * access — so `mobile/UI.md` has always said that anything past the first
 * screen needs a human hand. Every change to the sheet was therefore verified
 * by `tsc` and by nothing else. This makes the sheet reachable from a script:
 *
 *     EXPO_PUBLIC_DEV_OPEN_MEMORY=265 npx expo start --dev-client
 *     xcrun simctl io booted screenshot /tmp/sheet.png
 *
 * Or with no restart, by writing `screen=paywall` into `dev-screen` in the app's
 * documents, which `devWatch` polls: `scripts/shoot.sh` walks every screen so.
 * Not a deep link: `simctl openurl` asks "Open in Memory Lane?" every time.
 */

import { File, Paths } from 'expo-file-system';

/** Every screen a launch or the dev-screen file can land on. In `scripts/shoot.sh`'s
 *  order: `walk` and after build on the walk `preview` planned. */
export const SCREENS = [
  'signin',
  'onboarding',
  'onboarding-2',
  'onboarding-3',
  'onboarding-4',
  'onboarding-location',
  'map',
  'memory',
  'preview',
  'preview-stops',
  'customize',
  'walked-out',
  'end',
  'walk',
  'lock',
  'end-confirm',
  'done',
  'journal',
  'journal-walk',
  'journal-cards',
  'journal-unlocked',
  'journal-hearted',
  'journal-mine',
  'journal-memory',
  'past',
  'submit',
  'settings',
  'profile',
  'paywall',
  'crash',
] as const;

export type DevScreen = (typeof SCREENS)[number];

/** `EXPO_PUBLIC_DEV_OPEN_SCREEN=submit`. The submit sheet in particular had no
 *  other way to be seen: it is three taps in, and there are no taps. */
export function devOpenScreen(): DevScreen | null {
  if (!__DEV__) return null;

  return asScreen(process.env.EXPO_PUBLIC_DEV_OPEN_SCREEN);
}

function asScreen(raw: string | null | undefined): DevScreen | null {
  raw = raw?.trim();
  if (!raw) return null;
  if (!(SCREENS as readonly string[]).includes(raw)) {
    console.warn(`Dev screen is not one of ${SCREENS.join(', ')}: ${raw}`);
    return null;
  }
  return raw as DevScreen;
}

/** Calls `open` each time `dev-screen` changes, with what it now says:
 *  `screen=memory&memory=265&n=<anything new>`. What was there at launch is
 *  stale and ignored. Returns the stop. */
export function devWatch(open: (screen: DevScreen, memory: number | null) => void): () => void {
  if (!__DEV__) return () => {};
  const file = new File(Paths.document, 'dev-screen');
  const read = () => (file.exists ? file.textSync().trim() : '');
  let last = read();
  const timer = setInterval(() => {
    const now = read();
    if (now === last) return;
    last = now;
    // Not URLSearchParams: React Native's has no get().
    const query = Object.fromEntries(now.split('&').map((pair) => pair.split('=')));
    const screen = asScreen(query.screen);
    const memory = Number(query.memory);
    if (screen) open(screen, Number.isInteger(memory) && memory > 0 ? memory : null);
  }, 250);
  return () => clearInterval(timer);
}

/** `EXPO_PUBLIC_DEV_OPEN_MEMORY=265`. Baked in when Metro starts, so changing
 *  it needs a dev-server restart. */
export function devOpenMemory(): number | null {
  if (!__DEV__) return null;

  const raw = process.env.EXPO_PUBLIC_DEV_OPEN_MEMORY;
  if (!raw) return null;

  const id = Number(raw.trim());
  if (!Number.isInteger(id)) {
    console.warn(`EXPO_PUBLIC_DEV_OPEN_MEMORY is not a memory id: ${raw}`);
    return null;
  }
  return id;
}
