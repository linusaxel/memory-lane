/** How many opens, hearts and notes each memory you filed had the last time you
 *  looked, so the Filed list can say which ones got more since. No server
 *  state and no push: a baseline on this phone, like hearted.ts, and losing
 *  it costs nothing but one "new" too many. */

import AsyncStorage from '@react-native-async-storage/async-storage';

import type { Memory } from './api.ts';

const KEY = 'memorylane.seen.v1';

export type Seen = Record<number, number>;

export const attention = (m: Memory) => (m.opened_by ?? 0) + m.heart_count + m.note_count;

export async function loadSeen(): Promise<Seen> {
  try {
    const raw = await AsyncStorage.getItem(KEY);
    return raw ? (JSON.parse(raw) as Seen) : {};
  } catch {
    return {};
  }
}

export async function saveSeen(current: Seen, memories: Memory[]): Promise<void> {
  const next = { ...current };
  for (const m of memories) next[m.id] = attention(m);
  try {
    await AsyncStorage.setItem(KEY, JSON.stringify(next));
  } catch {
    // Shown as new again next time. Harmless.
  }
}

/** Did anything you filed get read, a heart or a note since you last looked? The
 *  map's Journal button says so. */
export async function anyNew(memories: Memory[]): Promise<boolean> {
  const seen = await loadSeen();
  return memories.some((m) => attention(m) > (seen[m.id] ?? 0));
}

const COUNTED = 'memorylane.counted.v1';

/** The journal header's numbers as last shown, so the next look rolls them up
 *  from there (UI.md). Lost, it costs one look without the roll. */
export type Counted = { memories: number; places: number; steps: number };

export async function loadCounted(): Promise<Counted | null> {
  try {
    const raw = await AsyncStorage.getItem(COUNTED);
    return raw ? (JSON.parse(raw) as Counted) : null;
  } catch {
    return null;
  }
}

export function saveCounted(counted: Counted): void {
  AsyncStorage.setItem(COUNTED, JSON.stringify(counted)).catch(() => {});
}

const UNLOCKS = 'memorylane.unlocks.v1';

/** The unlocked memories the journal has already shown, so one it hasn't
 *  pulses once (UI.md). null before the first look: nothing pulses then, like
 *  the count-up. Lost, it costs one look without the pulse. */
export async function loadUnlocksShown(): Promise<Set<number> | null> {
  try {
    const raw = await AsyncStorage.getItem(UNLOCKS);
    return raw ? new Set(JSON.parse(raw) as number[]) : null;
  } catch {
    return null;
  }
}

export function saveUnlocksShown(ids: number[]): void {
  AsyncStorage.setItem(UNLOCKS, JSON.stringify(ids)).catch(() => {});
}
