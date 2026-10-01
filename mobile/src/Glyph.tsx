/** An SF Symbol at a point size, in a theme colour. Every glyph in the app but
 *  the pin, which stays one drawn shape (UI.md, Markers). `bounce` plays the
 *  symbol's bounce each time its value changes. */

import { Host, Image, useNativeState } from '@expo/ui/swift-ui';
import { font, symbolEffect } from '@expo/ui/swift-ui/modifiers';
import { useEffect, type ComponentProps } from 'react';
import type { ColorValue } from 'react-native';

type Props = {
  name: NonNullable<ComponentProps<typeof Image>['systemName']>;
  size: number;
  color: ColorValue;
  weight?: 'regular' | 'medium' | 'semibold' | 'bold';
  bounce?: number | string | boolean;
};

export default function Glyph({ name, size, color, weight = 'regular', bounce = 0 }: Props) {
  const trigger = useNativeState(bounce);
  useEffect(() => {
    trigger.value = bounce;
  }, [bounce, trigger]);
  return (
    <Host matchContents>
      <Image
        systemName={name}
        color={color}
        modifiers={[font({ size, weight }), symbolEffect({ effect: 'bounce' }, { value: trigger })]}
      />
    </Host>
  );
}
