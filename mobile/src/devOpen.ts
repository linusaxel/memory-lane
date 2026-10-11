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

import { useEffect, useRef } from 'react';
import { LogBox } from 'react-native';
import { File, Paths } from 'expo-file-system';

import { API_BASE } from './api.ts';

/** Every screen a launch or the dev-screen file can land on, in
 *  `scripts/shoot.sh`'s order: what comes after `preview` builds on the walk it
 *  planned. `offline-` ones fail every request to the API, as no signal does.
 *  The `memory-` ones the script hands a memory id that has what they show. */
export const SCREENS = [
  'signin',
  'onboarding',
  'onboarding-2',
  'onboarding-3',
  'onboarding-4',
  'onboarding-location',
  'map',
  'offline-map',
  'memory',
  'memory-far',
  'memory-group',
  'memory-open',
  'memory-quote',
  'memory-wiki',
  'memory-notes',
  'notes-typing',
  'notes-error',
  'memory-report',
  'memory-block',
  'memory-mine',
  'seal-first',
  'preview',
  'preview-stops',
  'plan-mystery',
  'plan-new-nearby',
  'plan-empty-at',
  'plan-fallback',
  'plan-no-walk',
  'plan-finding',
  'plan-one-way',
  'plan-ends-here',
  'plan-unreachable',
  'customize',
  'customize-set',
  'preview-customized',
  'offline-plan',
  'walked-out',
  'end',
  'walk',
  'walk-mystery',
  'walk-no-location',
  'lock',
  'end-confirm',
  'offline-end',
  'done',
  'done-ask',
  'journal',
  'journal-walk',
  'journal-cards',
  'journal-unlocked',
  'journal-hearted',
  'journal-mine',
  'journal-memory',
  'past',
  'submit',
  'submit-filled',
  'submit-styling',
  'submit-date',
  'submit-discard',
  'submit-error',
  'submit-seal',
  'submit-editor',
  'submit-delete',
  'settings',
  'settings-lower',
  'settings-delete',
  'profile',
  'profile-error',
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

type Asked = { screen: DevScreen; memory: number | null };
type Listener = (asked: Asked) => void;

const listeners = new Set<Listener>();
let asked: Asked | null = null;
let offline = false;
let watching = false;

/** Polls `dev-screen` and tells every `useDevScreen` what it now says:
 *  `screen=memory-quote&memory=265&n=<anything new>`. What was there at launch
 *  is stale and ignored. */
function watch() {
  if (watching) return;
  watching = true;
  const file = new File(Paths.document, 'dev-screen');
  const read = () => (file.exists ? file.textSync().trim() : '');
  let last = read();
  // The offline- screens: every request to the API fails as it would with no signal.
  const online = global.fetch;
  global.fetch = (input, init) =>
    offline && String(input instanceof Request ? input.url : input).startsWith(API_BASE)
      ? Promise.reject(new TypeError('Network request failed'))
      : online(input, init);
  setInterval(() => {
    const now = read();
    if (now === last) return;
    last = now;
    // Not URLSearchParams: React Native's has no get().
    const query = Object.fromEntries(now.split('&').map((pair) => pair.split('=')));
    const screen = asScreen(query.screen);
    if (!screen) return;
    const memory = Number(query.memory);
    asked = { screen, memory: Number.isInteger(memory) && memory > 0 ? memory : null };
    // A screenshot wants the screen, not the warning toast an offline- one leaves.
    LogBox.ignoreAllLogs();
    offline = screen.startsWith('offline-');
    listeners.forEach((listener) => listener(asked!));
  }, 250);
}

/** Runs `on` each time a screen is asked for, and once on mount with the last
 *  one: a sheet mounts after the screen that opened it was asked for. Each
 *  component sets what it owns: App.tsx which sheet is open, Submit its step. */
export function useDevScreen(on: Listener) {
  const latest = useRef(on);
  latest.current = on;
  useEffect(() => {
    if (!__DEV__) return;
    const listener: Listener = (next) => latest.current(next);
    asked ??= devAtLaunch();
    if (asked) listener(asked);
    listeners.add(listener);
    watch();
    return () => {
      listeners.delete(listener);
    };
  }, []);
}

function devAtLaunch(): Asked | null {
  const screen = devOpenScreen();
  return screen && { screen, memory: null };
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
