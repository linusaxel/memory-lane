/** Settings: a sheet of its own, opened from the cog in the journal's header.
 *
 * Grouped one-line rows, like iOS's own: the account, how it looks, location,
 * notifications, and the answer to "why can I not read this". Every app with a
 * proximity gate needs somewhere to answer that, and a sheet you only see once
 * you are already frustrated is too late. Who you are (the photo, the name,
 * the numbers) is the journal's header, not here.
 */

import { useEffect, useRef, useState, type ComponentProps } from 'react';
import {
  Image,
  Modal,
  Pressable,
  ScrollView,
  StyleSheet,
  Switch,
  Text,
  View,
  type ColorValue,
} from 'react-native';

import { API_BASE, type Profile } from './api.ts';
import { type Look, look, setLook } from './appearance.ts';
import Glyph from './Glyph.tsx';
import { manage } from './purchases.ts';
import { openLink } from './link.ts';
import CloseButton from './CloseButton.tsx';
import SignIn from './SignIn.tsx';
import { locketOf } from './lockets.ts';
import type { Permission } from './types.ts';
import Button from './Button.tsx';
import { useDevScreen } from './devOpen.ts';
import { Panel, Ribbon } from './Game.tsx';
import { color, dim, font, label, metal, screenTitle } from './theme.ts';

type Props = {
  visible: boolean;
  onClose: () => void;
  /** Close this and open the paywall: one sheet at a time. */
  onSubscribe: () => void;
  device: string | null;
  profile: Profile | null;
  onProfile: (next: Profile) => void;
  radiusMeters: number;
  permission: Permission;
  onRequestLocation: () => void;
  /** Off until chosen. Turning it on asks for background location, which is
   *  the one permission this screen has to explain before the OS prompt does. */
  notifyNearby: boolean;
  onNotifyNearby: (next: boolean) => void;
};

export default function Settings({
  visible,
  onClose,
  device,
  profile,
  onProfile,
  radiusMeters,
  permission,
  onRequestLocation,
  notifyNearby,
  onNotifyNearby,
  onSubscribe,
}: Props) {
  const granted = permission === 'granted';
  const [chosen, choose] = useState<Look>(look);
  // scripts/shoot.sh, under __DEV__ only: the foot of the page, once the sheet is up.
  const scroll = useRef<ScrollView>(null);
  const [devLower, setDevLower] = useState(false);
  useDevScreen(({ screen }) => setDevLower(screen === 'settings-lower'));
  useEffect(() => {
    if (!visible) return;
    const timer = setTimeout(
      () =>
        devLower
          ? scroll.current?.scrollToEnd({ animated: false })
          : scroll.current?.scrollTo({ y: 0, animated: false }),
      600,
    );
    return () => clearTimeout(timer);
  }, [devLower, visible]);

  return (
    <Modal
      visible={visible}
      animationType="slide"
      presentationStyle="pageSheet"
      onRequestClose={onClose}
    >
      <ScrollView ref={scroll} style={styles.screen} contentContainerStyle={styles.body}>
        <View style={styles.top}>
          <View>
            <Ribbon label="Camp" />
            <Text style={styles.title}>Settings</Text>
          </View>
          <CloseButton onPress={onClose} label="Close settings" />
        </View>

        <Group title="Account">
          <View style={styles.padded}>
            {profile?.subscribed && (
              <Text style={styles.note}>
                {profile.subscribed_until
                  ? `Plus until ${new Date(`${profile.subscribed_until}Z`).toLocaleDateString()}.`
                  : 'Plus.'}
              </Text>
            )}
            <SignIn
              device={device}
              profile={profile}
              onProfile={onProfile}
              beside={
                profile?.subscribed ? (
                  <Button
                    kind="quiet"
                    label="Manage"
                    accessibilityLabel="Manage subscription"
                    onPress={() => manage().catch(() => {})}
                    place={styles.half}
                  />
                ) : (
                  profile?.user_id && (
                    <Button
                      kind="foil"
                      label="Get Plus"
                      onPress={onSubscribe}
                      place={styles.half}
                    />
                  )
                )
              }
            />
          </View>
        </Group>

        <Group title="Appearance">
          <View style={styles.segments}>
            {(
              [
                ['unspecified', 'System'],
                ['light', 'Light'],
                ['dark', 'Dark'],
              ] as const
            ).map(([value, name]) => (
              <Pressable
                key={value}
                style={dim([styles.segment, chosen === value && styles.segmentOn])}
                onPress={() => {
                  choose(value);
                  setLook(value);
                }}
                accessibilityRole="tab"
                accessibilityState={{ selected: chosen === value }}
              >
                <Text style={[styles.segmentText, chosen === value && styles.segmentTextOn]}>
                  {name}
                </Text>
              </Pressable>
            ))}
          </View>
        </Group>

        <Group
          title="Location"
          footer={
            granted
              ? "Used to tell when you're close to a memory, and never stored."
              : "You'll need it to unlock anything."
          }
        >
          <Row
            label="Location"
            icon="location.fill"
            tone={color.seal}
            value={granted ? 'On' : 'Off'}
            onPress={onRequestLocation}
            accessibilityLabel={granted ? 'Manage in Settings' : 'Turn on location'}
          />
        </Group>

        <Group
          title="Notifications"
          footer="Needs location in the background, only to check whether you're near a memory. Your position is never stored."
        >
          <Row label="A memory is nearby" icon="bell.fill" tone={color.plum}>
            <Switch
              trackColor={{ true: metal.mid }}
              testID="notify-nearby"
              value={notifyNearby}
              onValueChange={onNotifyNearby}
              accessibilityLabel="Notify me when a memory is nearby"
            />
          </Row>
        </Group>

        <Group title="How it works">
          <View style={[styles.padded, styles.how]}>
            <Image source={locketOf().pin} style={styles.locket} />
            <Text style={styles.howText}>
              A memory unlocks only on a walk, within {Math.round(radiusMeters)} m of it. Each one
              you open is a locket, and your Collector grows with them and with the memories you
              leave.
            </Text>
          </View>
        </Group>

        <Group title="About">
          <Row
            label="Privacy policy"
            icon="hand.raised.fill"
            tone={color.gold}
            link
            onPress={() => openLink(`${API_BASE}/privacy`)}
          />
          <Row
            label="Contact us"
            icon="envelope.fill"
            tone={color.gold}
            link
            onPress={() => openLink(`${API_BASE}/privacy#contact`)}
          />
          <Row
            label="Places © OpenStreetMap"
            icon="map.fill"
            tone={color.inkSoft}
            link
            onPress={() => openLink('https://www.openstreetmap.org/copyright')}
          />
        </Group>
      </ScrollView>
    </Modal>
  );
}

/** A panel with a foil tab naming it, its rows, and an optional line under it. */
function Group({
  title,
  footer,
  children,
}: {
  title: string;
  footer?: string;
  children: React.ReactNode;
}) {
  return (
    <View style={styles.group}>
      <Panel title={title} style={styles.card}>
        {children}
      </Panel>
      {footer && <Text style={styles.footer}>{footer}</Text>}
    </View>
  );
}

/** One line: a coloured badge, a label, then a value and a chevron, an arrow
 *  out, or a control. */
function Row({
  label: text,
  icon,
  tone,
  value,
  link,
  onPress,
  accessibilityLabel,
  children,
}: {
  label: string;
  icon?: ComponentProps<typeof Glyph>['name'];
  /** The badge's colour: a theme colour that says what kind of row it is. */
  tone?: ColorValue;
  value?: string;
  link?: boolean;
  onPress?: () => unknown;
  accessibilityLabel?: string;
  children?: React.ReactNode;
}) {
  const badge = icon && (
    <View style={[styles.badge, { backgroundColor: tone }]}>
      <Glyph name={icon} size={15} weight="semibold" color={color.paper} />
    </View>
  );
  // A control row stays a View: a Pressable around it would hide the
  // control's own label from VoiceOver.
  if (!onPress)
    return (
      <View style={styles.row}>
        {badge}
        <Text style={styles.rowText}>{text}</Text>
        {children}
      </View>
    );
  return (
    <Pressable
      style={dim(styles.row)}
      onPress={() => Promise.resolve(onPress()).catch(() => {})}
      accessibilityRole={link ? 'link' : 'button'}
      accessibilityLabel={accessibilityLabel}
    >
      {badge}
      <Text style={styles.rowText}>{text}</Text>
      {value && <Text style={styles.value}>{value}</Text>}
      <Glyph
        name={link ? 'arrow.up.right' : 'chevron.right'}
        size={13}
        weight="semibold"
        color={color.inkFaint}
      />
    </Pressable>
  );
}

const styles = StyleSheet.create({
  screen: { flex: 1, backgroundColor: color.paper },
  body: { paddingHorizontal: 20, paddingTop: 28, paddingBottom: 72 },
  // The journal's title bar, so the two sheets read as one app.
  top: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingHorizontal: 4,
  },
  title: screenTitle,
  group: { marginTop: 28, gap: 8 },
  // The rows bring their own padding; the panel only clears its tab.
  card: { padding: 0, paddingTop: 10, marginTop: 0 },
  badge: {
    width: 30,
    height: 30,
    borderRadius: 9,
    alignItems: 'center',
    justifyContent: 'center',
  },
  footer: {
    ...font.prose,
    fontSize: 13,
    lineHeight: 19,
    color: color.inkFaint,
    marginHorizontal: 16,
  },
  padded: { padding: 16, gap: 10 },
  row: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 10,
    minHeight: 50,
    paddingHorizontal: 16,
    borderTopWidth: StyleSheet.hairlineWidth,
    borderTopColor: color.rule,
    marginTop: -StyleSheet.hairlineWidth,
  },
  rowText: { flex: 1, ...font.uiMedium, fontSize: 16, color: color.ink },
  value: { ...font.ui, fontSize: 16, color: color.inkSoft },
  note: { ...font.prose, fontSize: 15, lineHeight: 22, color: color.inkSoft },
  half: { flex: 1 },
  segments: { flexDirection: 'row', padding: 4, gap: 4 },
  segment: {
    flex: 1,
    alignItems: 'center',
    paddingVertical: 10,
    borderRadius: 12,
    borderWidth: 1,
    borderColor: 'transparent',
  },
  segmentOn: { backgroundColor: color.velvetGround, borderColor: color.edge },
  segmentText: { ...label, color: color.inkSoft },
  segmentTextOn: { ...font.uiBold, color: color.onVelvet },
  how: { flexDirection: 'row', alignItems: 'center', gap: 12 },
  locket: { width: 32, height: 32 },
  howText: { flex: 1, ...font.prose, fontSize: 15, lineHeight: 22, color: color.inkSoft },
});
