/** The Collector's art, and what this phone keeps of it (collector.ts has the
 *  rules). Decorative, so a look says nothing to VoiceOver: its words do. */

import AsyncStorage from '@react-native-async-storage/async-storage';
import { Image, type ImageSourcePropType, type ImageStyle, type StyleProp } from 'react-native';

import type { ClassId } from './collector.ts';
import { color } from './theme.ts';

/** Each class's eight looks. Placeholders until the art lands: every stage is
 *  the sheet's front view, so the real art only swaps files. */
export const LOOKS: Record<ClassId, ImageSourcePropType[]> = {
  wayfinder: [
    require('../assets/collector/wayfinder-1.png'),
    require('../assets/collector/wayfinder-2.png'),
    require('../assets/collector/wayfinder-3.png'),
    require('../assets/collector/wayfinder-4.png'),
    require('../assets/collector/wayfinder-5.png'),
    require('../assets/collector/wayfinder-6.png'),
    require('../assets/collector/wayfinder-7.png'),
    require('../assets/collector/wayfinder-8.png'),
  ],
  pilgrim: [
    require('../assets/collector/pilgrim-1.png'),
    require('../assets/collector/pilgrim-2.png'),
    require('../assets/collector/pilgrim-3.png'),
    require('../assets/collector/pilgrim-4.png'),
    require('../assets/collector/pilgrim-5.png'),
    require('../assets/collector/pilgrim-6.png'),
    require('../assets/collector/pilgrim-7.png'),
    require('../assets/collector/pilgrim-8.png'),
  ],
  skywatcher: [
    require('../assets/collector/skywatcher-1.png'),
    require('../assets/collector/skywatcher-2.png'),
    require('../assets/collector/skywatcher-3.png'),
    require('../assets/collector/skywatcher-4.png'),
    require('../assets/collector/skywatcher-5.png'),
    require('../assets/collector/skywatcher-6.png'),
    require('../assets/collector/skywatcher-7.png'),
    require('../assets/collector/skywatcher-8.png'),
  ],
  chronicler: [
    require('../assets/collector/chronicler-1.png'),
    require('../assets/collector/chronicler-2.png'),
    require('../assets/collector/chronicler-3.png'),
    require('../assets/collector/chronicler-4.png'),
    require('../assets/collector/chronicler-5.png'),
    require('../assets/collector/chronicler-6.png'),
    require('../assets/collector/chronicler-7.png'),
    require('../assets/collector/chronicler-8.png'),
  ],
};

type Props = {
  id: ClassId;
  stage: number;
  size: number;
  /** A stage not reached yet: a dark silhouette, what is ahead without how it looks. */
  ahead?: boolean;
  place?: StyleProp<ImageStyle>;
};

export default function CollectorLook({ id, stage, size, ahead, place }: Props) {
  return (
    <Image
      source={LOOKS[id][stage]}
      style={[{ width: size, height: size }, ahead && { tintColor: color.inkFaint }, place]}
      resizeMode="contain"
      accessible={false}
    />
  );
}

const KEY = 'memorylane.collector.v1';

/** What this phone keeps: the class picked, and the highest stage reached.
 *  No stage yet means the Collector has not met this account's lockets. */
export type Collector = { class?: ClassId; stage?: number };

export async function loadCollector(): Promise<Collector> {
  try {
    const raw = await AsyncStorage.getItem(KEY);
    return raw ? (JSON.parse(raw) as Collector) : {};
  } catch {
    return {};
  }
}

export function saveCollector(collector: Collector): void {
  AsyncStorage.setItem(KEY, JSON.stringify(collector)).catch(() => {});
}
