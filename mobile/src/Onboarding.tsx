/** Four pages on what the app is, then the location primer: once, right after
 *  sign-in, over the map (docs/10, "Four pages, then the map"). The pictures
 *  are the design handoff's own, rasterised (mobile/assets/onboarding). The
 *  last page picks your Collector (docs/10, "The Collector"); Skip leaves the
 *  Wayfinder.
 *  "Turn on location" is a press with a reason, so the system prompt is never
 *  the first thing anyone sees (UI.md, location). */

import { useState } from 'react';
import { Image, Pressable, StyleSheet, Text, View, useColorScheme } from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';

import Button from './Button.tsx';
import CollectorLook from './CollectorLook.tsx';
import { CLASSES, type ClassId } from './collector.ts';
import type { Permission } from './types.ts';
import { color, dim, font, screenTitle } from './theme.ts';

const ART = {
  welcome: [
    require('../assets/onboarding/welcome-light.jpg'),
    require('../assets/onboarding/welcome-dark.jpg'),
  ],
  spot: [
    require('../assets/onboarding/spot-light.jpg'),
    require('../assets/onboarding/spot-dark.jpg'),
  ],
  daily: [
    require('../assets/onboarding/daily-light.jpg'),
    require('../assets/onboarding/daily-dark.jpg'),
  ],
  location: [
    require('../assets/onboarding/location-light.jpg'),
    require('../assets/onboarding/location-dark.jpg'),
  ],
};

type Props = {
  radiusMeters: number;
  permission: Permission;
  /** Asks for location; true once there is a fix. */
  onLocation: () => Promise<boolean>;
  onDone: () => void;
  /** The page a dev link opens on: 4 is the location primer. */
  devPage?: number;
  picked: ClassId;
  onPick: (id: ClassId) => void;
};

export default function Onboarding({
  radiusMeters,
  permission,
  onLocation,
  onDone,
  devPage,
  picked,
  onPick,
}: Props) {
  const insets = useSafeAreaInsets();
  const dark = useColorScheme() === 'dark' ? 1 : 0;
  const [page, setPage] = useState(devPage ?? 0);
  const [asking, setAsking] = useState(false);

  const pages = [
    {
      art: ART.welcome,
      title: 'The corner you pass has a story',
      body: 'Memory Lane plans walks past a few of them, about one a kilometre.',
    },
    {
      art: ART.spot,
      title: 'They only unlock on the spot',
      body: `Walk to within ${Math.round(radiusMeters)} m and slide to unlock. No reading from the sofa.`,
    },
    {
      art: ART.daily,
      title: 'A free walk every week',
      body: 'Pick how far. Loop home or end somewhere new.',
    },
    {
      art: null,
      title: 'Pick your Collector',
      body: 'It grows with every memory you open. Change it any time in your journal.',
    },
  ];
  // Someone who already said yes is not asked again.
  const primer = page === pages.length;
  const last = page === pages.length - 1;
  const next = () => (last && permission === 'granted' ? onDone() : setPage(page + 1));
  const shown = primer
    ? {
        art: ART.location,
        title: "Know when you're standing on one",
        body: "Location tells Memory Lane when you've reached a memory. It's never stored.",
      }
    : pages[page];

  return (
    <View style={[styles.screen, { paddingTop: insets.top, paddingBottom: insets.bottom + 16 }]}>
      <View style={styles.skipRow}>
        {!primer && <Button kind="text" label="Skip" onPress={() => setPage(pages.length)} />}
      </View>
      {shown.art ? (
        <View style={styles.art}>
          <Image
            source={shown.art[dark]}
            style={styles.fill}
            accessibilityIgnoresInvertColors
            accessible={false}
          />
        </View>
      ) : (
        <View style={[styles.art, styles.pick]} accessibilityRole="radiogroup">
          {CLASSES.map((c) => (
            <Pressable
              key={c.id}
              style={dim([styles.choice, c.id === picked && styles.chosen])}
              onPress={() => onPick(c.id)}
              accessibilityRole="radio"
              accessibilityState={{ selected: c.id === picked }}
              accessibilityLabel={c.name}
            >
              <CollectorLook id={c.id} stage={3} size={128} />
              <Text style={styles.name}>{c.name}</Text>
            </Pressable>
          ))}
        </View>
      )}
      <View style={styles.words}>
        <Text style={styles.title} accessibilityRole="header">
          {shown.title}
        </Text>
        <Text style={styles.body}>{shown.body}</Text>
      </View>
      <View style={styles.foot}>
        {primer ? (
          <>
            <Button
              kind="go"
              label="Turn on location"
              glyph="location"
              busy={asking}
              onPress={async () => {
                setAsking(true);
                await onLocation().catch(() => false);
                setAsking(false);
                onDone();
              }}
            />
            <Button kind="text" label="Not now" onPress={onDone} place={styles.notNow} />
          </>
        ) : (
          <>
            <View
              style={styles.dots}
              accessible
              accessibilityLabel={`Page ${page + 1} of ${pages.length}`}
            >
              {pages.map((_, i) => (
                <View key={i} style={[styles.dot, i === page && styles.dotOn]} />
              ))}
            </View>
            <Button kind="go" label={last ? 'Start' : 'Next'} onPress={next} />
          </>
        )}
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  screen: {
    position: 'absolute',
    top: 0,
    left: 0,
    right: 0,
    bottom: 0,
    backgroundColor: color.paper,
    paddingHorizontal: 16,
  },
  skipRow: { height: 52, alignItems: 'flex-end', justifyContent: 'center' },
  art: {
    width: '100%',
    aspectRatio: 358 / 368,
    borderRadius: 32,
    borderWidth: 1,
    borderColor: color.goldLine,
    overflow: 'hidden',
  },
  fill: { width: '100%', height: '100%' },
  pick: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    padding: 8,
    gap: 8,
    backgroundColor: color.paperRaised,
  },
  choice: {
    width: '48%',
    height: '49%',
    flexGrow: 1,
    alignItems: 'center',
    justifyContent: 'center',
    gap: 4,
    borderRadius: 24,
    borderWidth: 2,
    borderColor: 'transparent',
  },
  chosen: { borderColor: color.gold, backgroundColor: color.paper },
  name: { ...font.uiBold, fontSize: 15, color: color.ink },
  words: { marginTop: 28, paddingHorizontal: 16, gap: 12, alignItems: 'center' },
  title: { ...screenTitle, textAlign: 'center' },
  body: { ...font.prose, fontSize: 17, lineHeight: 25, color: color.inkSoft, textAlign: 'center' },
  foot: { flex: 1, justifyContent: 'flex-end', gap: 24, paddingHorizontal: 8 },
  dots: { flexDirection: 'row', justifyContent: 'center', gap: 8 },
  dot: { width: 8, height: 8, borderRadius: 4, backgroundColor: color.rule },
  dotOn: { width: 24, backgroundColor: color.gold },
  notNow: { alignSelf: 'center', marginTop: -8 },
});
