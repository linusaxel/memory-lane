/** System, Light or Dark, chosen in the account menu and kept on this phone.
 *  `Appearance.setColorScheme` overrides the window, so `DynamicColorIOS`,
 *  `useColorScheme()`, the map and the native menus all follow it. */

import AsyncStorage from '@react-native-async-storage/async-storage';
import { Appearance } from 'react-native';

const KEY = 'memorylane.appearance.v1';

export type Look = 'unspecified' | 'light' | 'dark';

let current: Look = 'unspecified';

export const look = () => current;

export async function loadLook(): Promise<void> {
  try {
    const saved = await AsyncStorage.getItem(KEY);
    if (saved === 'light' || saved === 'dark') setLook(saved);
  } catch {
    // Follows the system. Harmless.
  }
}

export function setLook(next: Look) {
  current = next;
  Appearance.setColorScheme(next);
  AsyncStorage.setItem(KEY, next).catch(() => {});
}
