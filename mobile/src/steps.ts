/** Steps walked, read from the phone's own Core Motion history, which counts
 *  with the app closed and keeps seven days (docs/10, "Steps open a memory").
 *  iOS only: on Android the Pedometer has no history. */
import { Pedometer } from 'expo-sensors';
import { Platform } from 'react-native';

import { creditSteps, type Profile } from './api.ts';

const WEEK_MS = 7 * 24 * 60 * 60 * 1000;

/** Credit what was walked since the profile's watermark, and return the
 *  profile after. Null when there is nothing to count: not iOS, no account
 *  yet, a subscriber, or no motion permission. */
export async function syncSteps(device: string, profile: Profile): Promise<Profile | null> {
  const since = profile.steps_counted_until;
  if (Platform.OS !== 'ios' || !since || profile.subscribed) return null;
  if (!(await Pedometer.isAvailableAsync())) return null;
  if (!(await Pedometer.requestPermissionsAsync()).granted) return null;
  // Microseconds past the millisecond don't parse everywhere.
  const from = Math.max(new Date(`${since.slice(0, 23)}Z`).getTime(), Date.now() - WEEK_MS);
  const { steps } = await Pedometer.getStepCountAsync(new Date(from), new Date());
  return creditSteps(device, since, steps);
}
