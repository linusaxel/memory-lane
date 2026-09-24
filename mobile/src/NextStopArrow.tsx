/** The way to the next stop, on the edge of the screen, while that stop is off
 *  it. Walk pins the camera on the person, so the map cannot be dragged to go
 *  and look; this says which way instead. Hex, not theme tokens, for the same
 *  reason as RouteLine: an Svg fill takes a real colour. */

import { useState } from 'react';
import { StyleSheet, View } from 'react-native';
import Svg, { Path } from 'react-native-svg';

import type { Coordinates } from './api.ts';
import { edgeArrow, type Region } from './region.ts';

const SIZE = 34;
const MARGIN = SIZE / 2 + 8;
// The edges it rides are the map's less what sits on them: "+ Add" at the top
// (App.tsx styles.add, top 64), the pill and the Maps attribution at the
// bottom, which rule 7 says nothing covers.
const INSET = { top: 110 + MARGIN, right: MARGIN, bottom: 90 + MARGIN, left: MARGIN };

type Props = { region: Region; target: Coordinates; dark: boolean };

export default function NextStopArrow({ region, target, dark }: Props) {
  const [size, setSize] = useState<{ width: number; height: number } | null>(null);
  const arrow = size && edgeArrow(region, target, size.width, size.height, INSET);

  return (
    <View
      style={StyleSheet.absoluteFill}
      pointerEvents="none"
      onLayout={(e) => setSize(e.nativeEvent.layout)}
    >
      {arrow && (
        <View
          accessible={false}
          style={[
            styles.arrow,
            {
              left: arrow.x - SIZE / 2,
              top: arrow.y - SIZE / 2,
              transform: [{ rotate: `${arrow.angle}deg` }],
            },
          ]}
        >
          <Svg width={SIZE} height={SIZE} viewBox="0 0 34 34">
            {/* Pointing up; the transform turns it. The paper edge is the
                route line's casing, so it reads on any street. */}
            <Path
              d="M17 3 L30 29 L17 22 L4 29 Z"
              fill={dark ? '#5AA2FF' : '#1A64D6'}
              stroke={dark ? '#1B4F99' : '#FFFFFF'}
              strokeWidth={2.5}
              strokeLinejoin="round"
            />
          </Svg>
        </View>
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  arrow: { position: 'absolute', width: SIZE, height: SIZE },
});
