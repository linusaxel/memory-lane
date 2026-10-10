import * as Haptics from 'expo-haptics';

export type HapticKind =
  'selection' | 'soft' | 'light' | 'medium' | 'heavy' | 'rigid' | 'success' | 'warning';

/** A haptic that fires once when hold progress p (0–1) crosses `at`. */
export type HoldHaptic = { at: number; kind: HapticKind };

/** Runs on the JS thread; call it from worklets with scheduleOnRN(fireHaptic, kind). */
export function fireHaptic(kind: HapticKind): void {
  play(kind).catch(() => {});
}

function play(kind: HapticKind): Promise<void> {
  switch (kind) {
    case 'selection':
      return Haptics.selectionAsync();
    case 'soft':
      return Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Soft);
    case 'light':
      return Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Light);
    case 'medium':
      return Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Medium);
    case 'heavy':
      return Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Heavy);
    case 'rigid':
      return Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Rigid);
    case 'success':
      return Haptics.notificationAsync(Haptics.NotificationFeedbackType.Success);
    case 'warning':
      return Haptics.notificationAsync(Haptics.NotificationFeedbackType.Warning);
  }
}
