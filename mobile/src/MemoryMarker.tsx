/** What a coordinate looks like on the map, in its five states - see "The ink
 *  ladder" in mobile/UI.md, and docs/08-ux-flows.md F4 for why layers are
 *  stacked by shape rather than chosen from a filter. */

import type { ReactNode } from 'react';
import { type ColorValue, StyleSheet, Text, View } from 'react-native';
import { Callout, Marker } from 'react-native-maps';

import type { MemoryGroup } from './cluster.ts';
import { groupLabel, layerOf } from './cluster.ts';
import Padlock from './Padlock.tsx';
import TagGlyph from './tagGlyph.tsx';
import { color, font } from './theme.ts';
import type { Reach } from './reach.ts';

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
};

export default function MemoryMarker({
  group,
  reach,
  onPress,
  routePosition = null,
  routeSize = 0,
}: Props) {
  const count = group.memories.length;
  const card = layerOf(group) === 'stranger';
  // The dominant tag: whatever the group's first memory carries first. Only a
  // handful of tags have art (see tagGlyph.tsx); the rest render nothing.
  const tag = group.memories[0]?.tags[0] ?? null;

  return (
    <Marker
      // The reach and the route position are part of the key on purpose.
      // tracksViewChanges is off for the frame cost, so the marker only
      // repaints when React gives it a new identity - which is exactly when
      // its state changed.
      key={`${group.key}:${reach}:${card ? 'card' : 'round'}:${routePosition ?? ''}`}
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
        routePosition ? `Stop ${routePosition} of ${routeSize}.` : null,
        `${groupLabel(group)}. ${STATE_LABEL[reach]}.`,
        tag ? `Tagged ${tag}.` : null,
      ]
        .filter(Boolean)
        .join(' ')}
      tracksViewChanges={false}
      onPress={onPress}
    >
      <Pin reach={reach} count={count} card={card} routePosition={routePosition} tag={tag} />
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

type PinProps = {
  reach: Reach;
  count: number;
  card: boolean;
  routePosition: number | null;
  tag: string | null;
};

// A pin's one badge slot, across every branch, shows at most one of: today's
// route position (most urgent - it is why you opened the app), how many
// memories are stacked here, the padlock saying something is shut, or the
// dominant tag's glyph - in that order. `stamped` is the one branch with no
// padlock to compete with a glyph, so it is the only branch that needs all
// four options weighed; the gated branches below decide padlock-vs-glyph
// inline, since a padlock always wins there.
// ponytail: a route candidate is one memory's id, so a *stack* that happens to
// contain one shows the route number for the whole stack. Rare (it needs a
// stack AND one of its members picked for today's route) and harmless - the
// sheet still pages through every memory underneath correctly.
function stampedMark(routePosition: number | null, count: number, tag: string | null) {
  if (routePosition) return { kind: 'text' as const, value: String(routePosition) };
  if (count > 1) return { kind: 'text' as const, value: String(count) };
  if (tag) return { kind: 'tag' as const, value: tag };
  return null;
}

function Pin({ reach, count, card, routePosition, tag }: PinProps) {
  // In reach: a ring, not a disc. The pin you can open is by definition the pin
  // you are standing on, so the blue location dot lands dead centre - a disc
  // disappears underneath it, count and all. It also echoes the hold ring in
  // the sheet, so the map and the control are visibly the same object.
  if (reach === 'unlockable') {
    return (
      <View style={[styles.wrap, styles.halo]}>
        <View style={[styles.ring, card && styles.ringCard]} />
        {card && <View style={styles.fold} />}
        <Tag background={color.sealDeep}>
          {routePosition || count > 1 ? (
            <Text style={styles.count} maxFontSizeMultiplier={MARKER_FONT_SCALE}>
              {routePosition || count}
            </Text>
          ) : (
            <Padlock size={10} color={color.paper} />
          )}
        </Tag>
      </View>
    );
  }

  // Nothing to earn here. The smallest mark on the map, because a coordinate
  // with nothing behind a gate is context rather than an invitation. Never a
  // route stop - route candidates are always gated - so the only thing that
  // can fill its one free slot is a tag glyph.
  if (reach === 'plain') {
    if (count > 1) {
      return (
        <View style={styles.wrap}>
          <View style={[styles.badge, styles.inked, card && styles.square]}>
            <Text style={styles.count} maxFontSizeMultiplier={MARKER_FONT_SCALE}>
              {count}
            </Text>
          </View>
        </View>
      );
    }
    return (
      <View style={[styles.wrap, styles.wrapDot]}>
        <View style={[styles.dot, card && styles.dotSquare]} />
        {tag && (
          <Tag background={color.paper}>
            <TagGlyph tag={tag} size={11} color={color.inkFaint} />
          </Tag>
        )}
      </View>
    );
  }

  // Earned. The impression is the whole point: it says you stood here, and it
  // stays said. A ring inside the disc, because the ring is the thing you held
  // to open it - the pin keeps a small copy. Nothing else looks like this.
  if (reach === 'stamped') {
    const mark = stampedMark(routePosition, count, tag);
    return (
      <View style={styles.wrap}>
        <View style={[styles.disc, styles.inked, card && styles.discCard]}>
          <View style={[styles.impression, card && styles.impressionCard]} />
        </View>
        {card && <View style={styles.fold} />}
        {mark?.kind === 'text' && (
          <Tag background={color.ink}>
            <Text style={styles.count} maxFontSizeMultiplier={MARKER_FONT_SCALE}>
              {mark.value}
            </Text>
          </Tag>
        )}
        {mark?.kind === 'tag' && (
          <Tag background={color.paper}>
            <TagGlyph tag={mark.value} size={10} color={color.ink} />
          </Tag>
        )}
      </View>
    );
  }

  // Locked, near or far. Same disc, two weights: faded is out of reach, and an
  // ink outline on paper is close enough to be worth the walk. Ink and not
  // seal, because seal means openable now and a red pin you cannot open is an
  // invitation that refuses you - see F11. The padlock still wins over a tag
  // glyph here: there is only one face, and "this is shut" outranks "this is
  // about food".
  const warm = reach === 'warm';
  return (
    <View style={styles.wrap}>
      <View style={[styles.disc, warm ? styles.warm : styles.distant, card && styles.discCard]}>
        {routePosition || count > 1 ? (
          <Text
            style={[styles.count, warm && styles.countWarm]}
            maxFontSizeMultiplier={MARKER_FONT_SCALE}
          >
            {routePosition || count}
          </Text>
        ) : (
          <Padlock size={DISC * 0.34} color={warm ? color.ink : color.paper} />
        )}
      </View>
      {card && <View style={styles.fold} />}
    </View>
  );
}

/** What will not fit in the face goes to the corner, because the middle is
 *  where the blue location dot lands. A reachable pin always carries one: on a
 *  group of one it holds the padlock, which is the only thing on that pin
 *  saying there is something shut behind it. */
function Tag({ background, children }: { background: ColorValue; children: ReactNode }) {
  return <View style={[styles.tag, { backgroundColor: background }]}>{children}</View>;
}

const DOT = 18;
const DISC = 28;
const RING = 44;
/** Big enough to read as a turned page at 28px, small enough to leave a face. */
const FOLD = 9;

/** The count sits in fixed, non-clipping circles as small as 20px - there is
 *  no room in there for the OS's largest accessibility text sizes, which can
 *  scale a font past 3x. 1.3 keeps the count within the accessibility-props
 *  floor research recommends (below ~1.2 meaningfully hurts low-vision
 *  readers) while still bounding the overflow to something the pin survives,
 *  rather than the unbounded default. */
const MARKER_FONT_SCALE = 1.3;

const styles = StyleSheet.create({
  // The padding is the tap target, not decoration: a 28px disc is 28px of
  // hittable pin, and Apple's floor is 44. The wrap brings it to 46, which also
  // makes the stacked pins downtown separable by thumb rather than by luck.
  wrap: { alignItems: 'center', justifyContent: 'center', padding: 9 },
  // The dot is smaller, so it needs more around it to clear the same floor.
  wrapDot: { padding: 14 },
  // A soft glow so the pin is findable before you can read its shape.
  halo: { borderRadius: 40, backgroundColor: color.halo },

  dot: {
    width: DOT,
    height: DOT,
    borderRadius: DOT / 2,
    borderWidth: 2,
    borderColor: color.paper,
    backgroundColor: color.ink,
  },
  // No fold at this size - it would eat the face. The corners carry it alone.
  dotSquare: { borderRadius: 2 },

  badge: {
    minWidth: 26,
    height: 26,
    paddingHorizontal: 6,
    borderRadius: 13,
    borderWidth: 2,
    borderColor: color.paper,
    alignItems: 'center',
    justifyContent: 'center',
  },
  square: { borderRadius: 3 },

  disc: {
    width: DISC,
    height: DISC,
    borderRadius: DISC / 2,
    borderWidth: 2,
    borderColor: color.paper,
    alignItems: 'center',
    justifyContent: 'center',
  },
  discCard: { borderRadius: 3 },

  inked: { backgroundColor: color.ink },
  distant: { backgroundColor: color.faded },
  warm: { backgroundColor: color.paper, borderColor: color.ink },
  /** The mark the stamp leaves. Paper on ink is the same pair as the count, so
   *  it carries the contrast the rest of the pin already proved. Only a stamped
   *  pin has one. */
  impression: {
    width: 14,
    height: 14,
    borderRadius: 7,
    borderWidth: 2,
    borderColor: color.paper,
  },
  impressionCard: { borderRadius: 2 },

  ring: {
    width: RING,
    height: RING,
    borderRadius: RING / 2,
    borderWidth: 5,
    borderColor: color.seal,
    backgroundColor: color.paper,
  },
  ringCard: { borderRadius: 4 },

  /** A turned-down corner, drawn with the border triangle trick rather than
   *  the SVG that tag glyphs now use elsewhere on this pin - a shape this
   *  simple needs no library. Opaque on purpose: a real notch needs clipping,
   *  and a transparent wedge over a street map reads as a rendering fault. */
  fold: {
    position: 'absolute',
    top: 9,
    right: 9,
    width: 0,
    height: 0,
    borderTopWidth: FOLD,
    borderTopColor: color.paper,
    borderLeftWidth: FOLD,
    borderLeftColor: 'transparent',
  },

  tag: {
    position: 'absolute',
    top: 0,
    right: 0,
    minWidth: 20,
    height: 20,
    paddingHorizontal: 5,
    borderRadius: 10,
    borderWidth: 2,
    borderColor: color.paper,
    alignItems: 'center',
    justifyContent: 'center',
  },
  count: { color: color.paper, fontFamily: font.monoBold, fontSize: 11 },
  // On the one face that is paper rather than ink.
  countWarm: { color: color.ink },
});
