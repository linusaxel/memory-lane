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
 * Pair it with `python -m pipeline.seed_dev`, which prints the id of every
 * state the sheet can render.
 */

/** Every screen a launch can land on: the map, the journal over it, or the
 *  submit modal over that. */
const SCREENS = ['walk', 'journal', 'submit'] as const;

export type DevScreen = (typeof SCREENS)[number];

/** `EXPO_PUBLIC_DEV_OPEN_SCREEN=submit`. The submit sheet in particular had no
 *  other way to be seen: it is three taps in, and there are no taps. */
export function devOpenScreen(): DevScreen | null {
  if (!__DEV__) return null;

  const raw = process.env.EXPO_PUBLIC_DEV_OPEN_SCREEN?.trim();
  if (!raw) return null;

  if (!(SCREENS as readonly string[]).includes(raw)) {
    console.warn(`EXPO_PUBLIC_DEV_OPEN_SCREEN is not one of ${SCREENS.join(', ')}: ${raw}`);
    return null;
  }
  return raw as DevScreen;
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
