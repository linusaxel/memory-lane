/** What a coordinate looks like on the map: one pin, lit when it can be opened
 *  from here - see "One pin" in mobile/UI.md. */

import { Animated, StyleSheet, Text, View } from 'react-native';
import { Callout, Marker } from 'react-native-maps';

import type { MemoryGroup } from './cluster.ts';
import { groupLabel } from './cluster.ts';
import { color, font } from './theme.ts';
import type { Reach } from './reach.ts';
import { useHop } from './useBreath.ts';

const STATE_LABEL: Record<Reach, string> = {
  plain: 'Open',
  stamped: 'Unlocked, in your collection',
  warm: 'Locked, a short walk away',
  locked: 'Locked, too far to open',
  unlockable: 'Locked, within reach',
};

type Props = {
  group: MemoryGroup;
  reach: Reach;
  onPress: () => void;
  /** 1-based position in today's route, or null when this pin is not one of
   *  today's stops. Route candidates are always gated, so this never applies
   *  to a `plain` group. */
  routePosition?: number | null;
  routeSize?: number;
  /** Whether this pin lights up. The caller decides: on a route day only the
   *  route's stops do, so an off-route memory stays quiet even in reach. */
  lit: boolean;
  /** The next stop on today's walk: it hops in `route` blue until it is in
   *  reach, when `lit` takes over and it turns seal. */
  next?: boolean;
  /** A locked pin past a short walk: drawn soft, so the near ones lead. */
  far?: boolean;
};

export default function MemoryMarker({
  group,
  reach,
  onPress,
  routePosition = null,
  routeSize = 0,
  lit,
  next = false,
  far = false,
}: Props) {
  const count = group.memories.length;

  return (
    <Marker
      // The reach and the route position are part of the key on purpose.
      // tracksViewChanges is off for the frame cost, so the marker only
      // repaints when React gives it a new identity - which is exactly when
      // its state changed.
      key={`${group.key}:${reach}:${lit}:${next}:${far}:${routePosition ?? ''}`}
      coordinate={{ latitude: group.lat, longitude: group.lng }}
      // Put the middle of the pin on the point it names. iOS centres a custom
      // view already; Android defaults to bottom-centre whatever you draw, so
      // without this every pin hangs its own height above its coordinate.
      anchor={{ x: 0.5, y: 0.5 }}
      // `title` and nothing else, because on iOS it is the only one of these
      // that anybody hears. A Marker's accessibility comes from its
      // MKAnnotation: `accessibilityLabel` is dropped on the floor (set it
      // alone and VoiceOver announces MapKit's default, "Map pin") and
      // `subtitle` never reaches the label either. Colour is what says
      // whether a pin can be opened and colour is not available to everyone,
      // so the state has to ride along with the name.
      title={[
        next && !lit ? 'Next stop.' : null,
        routePosition ? `Stop ${routePosition} of ${routeSize}.` : null,
        `${groupLabel(group)}. ${STATE_LABEL[reach]}.`,
      ]
        .filter(Boolean)
        .join(' ')}
      tracksViewChanges={false}
      onPress={onPress}
    >
      <Pin
        lit={lit}
        next={next && !lit}
        open={reach === 'plain' || reach === 'stamped'}
        far={far}
        badge={routePosition || (count > 1 ? count : null)}
      />
      {/* An empty tooltip callout, which is how you say "no callout" while
          keeping a title. Setting `title` makes MapKit offer its own bubble:
          system font on a white rounded rect, at odds with everything in
          theme.ts, truncated to "…" by the state we just put in there, and -
          because the sheet is what a tap actually opens - still sitting on the
          map after the sheet is dismissed. `tooltip` replaces the bubble
          chrome with nothing and this view supplies no content, so the
          annotation keeps its label and draws nothing. */}
      <Callout tooltip>
        <View />
      </Callout>
    </Marker>
  );
}

type PinProps = { lit: boolean; next: boolean; open: boolean; far: boolean; badge: number | null };

/** One pin for everything. It lights up only when it can be opened from where
 *  you stand, and turns inside out, paper with an ember eye, once you have
 *  opened it; every other state lives in the title and the sheet. The paper
 *  centre is the point: the pin you can open is the pin you are standing on,
 *  so the blue location dot lands in the hole instead of under a disc. */
function Pin({ lit, next, open, far, badge }: PinProps) {
  const hop = useHop(next);
  return (
    <Animated.View style={[styles.wrap, lit && styles.halo, far && styles.far, hop]}>
      <View style={[styles.pin, open && styles.pinOpen, lit && styles.pinLit, next && styles.pinNext]}>
        <View style={[styles.eye, open && styles.eyeOpen, (lit || next) && styles.eyeLit, lit && styles.onSeal]} />
      </View>
      {badge !== null && (
        <View
          style={[
            styles.tag,
            lit ? styles.tagLit : null,
          ]}
        >
          <Text style={[styles.count, lit && styles.countLit]} maxFontSizeMultiplier={MARKER_FONT_SCALE}>
            {badge}
          </Text>
        </View>
      )}
    </Animated.View>
  );
}

const PIN = 24;
const LIT = 32;

/** The count sits in fixed, non-clipping circles as small as 20px - there is
 *  no room in there for the OS's largest accessibility text sizes, which can
 *  scale a font past 3x. 1.3 keeps the count within the accessibility-props
 *  floor research recommends (below ~1.2 meaningfully hurts low-vision
 *  readers) while still bounding the overflow to something the pin survives,
 *  rather than the unbounded default. */
const MARKER_FONT_SCALE = 1.3;

const styles = StyleSheet.create({
  // The padding is the tap target, not decoration: Apple's floor is 44. The
  // wrap brings both sizes to 46, which also makes the stacked pins downtown
  // separable by thumb rather than by luck.
  wrap: { alignItems: 'center', justifyContent: 'center', width: 46, height: 46 },
  // A soft glow so the lit pin is findable before you can read it.
  halo: { borderRadius: 23, backgroundColor: color.halo },
  far: { opacity: 0.45 },

  pin: {
    width: PIN,
    height: PIN,
    borderRadius: PIN / 2,
    borderWidth: 2,
    borderColor: color.paper,
    backgroundColor: color.ember,
    alignItems: 'center',
    justifyContent: 'center',
  },
  // Gold is too light for a paper edge, so a lit pin draws in sealInk.
  pinLit: { width: LIT, height: LIT, borderRadius: LIT / 2, backgroundColor: color.seal, borderColor: color.sealInk },
  pinNext: { width: LIT, height: LIT, borderRadius: LIT / 2 },
  pinOpen: { backgroundColor: color.paper, borderColor: color.ember },
  eye: { width: 8, height: 8, borderRadius: 4, backgroundColor: color.paper },
  eyeLit: { width: 12, height: 12, borderRadius: 6 },
  eyeOpen: { backgroundColor: color.ember },
  onSeal: { backgroundColor: color.sealInk },

  tag: {
    position: 'absolute',
    top: 0,
    right: 0,
    minWidth: 20,
    height: 20,
    paddingHorizontal: 4,
    borderRadius: 10,
    borderWidth: 2,
    borderColor: color.paper,
    backgroundColor: color.ember,
    alignItems: 'center',
    justifyContent: 'center',
  },
  tagLit: { backgroundColor: color.seal, borderColor: color.sealInk },
  countLit: { color: color.sealInk },
  count: { color: color.paper, ...font.uiBold, fontSize: 12 },
});
