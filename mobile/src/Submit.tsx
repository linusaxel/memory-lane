/** The only screen in the app that writes.
 *
 * Everything else here shows somebody else's anecdote from a podcast. This is
 * the person standing in the street saying what happened to them, which is the
 * half of the product a transcript corpus can never supply.
 *
 * Three decisions worth knowing before changing it:
 *
 * **It files where you are, and nowhere else.** One coordinate, taken from the
 * GPS, used as both "where you are" and "where this goes". There is no map
 * picker, and that is not a missing feature: a memory you can pin from your
 * sofa is a pin, and the whole product is built on the difference.
 *
 * With no position it cannot be posted - `ready` requires one - but it does
 * open while the GPS is still warming up, and says so. It refuses to open
 * only when location was denied, where the primer explains the refusal
 * properly. The distinction is whose time is being wasted: somebody who has
 * said no should not type a memory they will not be allowed to file, and
 * somebody waiting three seconds for a fix should not meet a button that
 * does nothing.
 *
 * **Attachments upload while you type.** A photo goes up the moment it is
 * picked rather than on Post, so the wait is spent composing instead of
 * staring at a spinner, and a failed upload costs the text nothing.
 *
 * **Tags are a closed list.** The server drops anything not on it, so offering
 * a free-text field would silently eat what somebody typed.
 */

import { useEffect, useRef, useState } from 'react';
import {
  ActivityIndicator,
  Animated,
  Image,
  KeyboardAvoidingView,
  Modal,
  Platform,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  View,
} from 'react-native';
import * as Haptics from 'expo-haptics';
import * as ImagePicker from 'expo-image-picker';
import {
  RecordingPresets,
  requestRecordingPermissionsAsync,
  setAudioModeAsync,
  useAudioRecorder,
  useAudioRecorderState,
} from 'expo-audio';

import {
  SUBMISSION_TAGS,
  mediaUrl,
  submitMemory,
  uploadMedia,
  type Coordinates,
  type Draft,
  type LocatedMemory,
  type MediaItem,
} from './api.ts';
import { duration, sealOpensAt } from './format.ts';
import { color, dim, font, input, label } from './theme.ts';

/** Matches the server's own floor. Ten characters is not a quality bar, it is a
 *  fat-finger bar, and the button has to agree with the API about it. */
const MIN_SUMMARY = 10;
const MAX_PHOTOS = 4;
/** Long enough for a story, short enough that nobody uploads a podcast. */
const MAX_RECORDING_SECONDS = 180;

type Props = {
  visible: boolean;
  /** Where the person is. Null means the form cannot open - see the header. */
  position: Coordinates | null;
  device: string | null;
  /** Remembered between submissions so nobody retypes their name every time. */
  displayName: string;
  onDisplayName: (next: string) => void;
  onClose: () => void;
  onPosted: (memory: LocatedMemory) => void;
};

/** An attachment on its way up, or up. `id` arrives when the server has it. */
type Attachment = {
  /** Local uri, so a photo shows before the upload finishes. */
  uri: string;
  kind: 'photo' | 'audio';
  seconds?: number;
  item?: MediaItem;
  failed?: boolean;
};

export default function Submit({
  visible,
  position,
  device,
  displayName,
  onDisplayName,
  onClose,
  onPosted,
}: Props) {
  const [placeName, setPlaceName] = useState('');
  const [summary, setSummary] = useState('');
  const [tags, setTags] = useState<string[]>([]);
  const [year, setYear] = useState('');
  const [when, setWhen] = useState<'today' | 'earlier'>('today');
  const [sealYear, setSealYear] = useState('');
  const [seal, setSeal] = useState<'now' | 'later'>('now');
  const [attachments, setAttachments] = useState<Attachment[]>([]);
  const [posting, setPosting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const recorder = useAudioRecorder(RecordingPresets.HIGH_QUALITY);
  const recording = useAudioRecorderState(recorder);
  const mounted = useRef(true);
  // `recorder.stop()` is async and durationMillis keeps ticking while it is in
  // flight, so the cap effect below can fire twice on one recording. Without
  // this the same uri uploads twice and there are two audio attachments where
  // the rest of this screen assumes one.
  const stopping = useRef(false);

  useEffect(() => {
    mounted.current = true;
    return () => {
      mounted.current = false;
    };
  }, []);

  // Everything resets on close. A half-written memory kept across openings
  // would eventually be posted somewhere it did not happen, because the
  // coordinate is taken fresh and the words would not be.
  useEffect(() => {
    if (visible) return;
    setPlaceName('');
    setSummary('');
    setTags([]);
    setYear('');
    setWhen('today');
    setSealYear('');
    setSeal('now');
    setAttachments([]);
    setError(null);
  }, [visible]);

  const photos = attachments.filter((a) => a.kind === 'photo');
  const sound = attachments.find((a) => a.kind === 'audio');
  const uploading = attachments.some((a) => !a.item && !a.failed);
  const named = placeName.trim().length > 0;
  const told = summary.trim().length >= MIN_SUMMARY;
  // The one answer, used by the button and by the draft, so they cannot
  // disagree about whether this memory is sealed - which is how "Nobody until"
  // with an empty year used to post something anybody could read.
  const opensAt = seal === 'later' ? sealOpensAt(sealYear) : null;
  const willSeal = seal !== 'later' || opensAt !== null;
  const ready =
    !!position && !!device && named && told && willSeal && !uploading && !posting;

  /** One line, and only ever the next thing to do. A list of everything
   *  outstanding is a list somebody has to read; this is an instruction. */
  const hint = !position
    ? 'Waiting for your location'
    : !told
      ? 'Say what happened here'
      : !named
      ? 'Name the place'
      : !willSeal
        ? 'A seal needs a year still to come'
        : uploading
          ? 'Finishing an upload'
          : posting
            ? 'Filing it…'
            : 'Ready to file';

  const progress = useRef(new Animated.Value(0)).current;
  useEffect(() => {
    Animated.spring(progress, {
      toValue: (told ? 0.5 : 0) + (named ? 0.5 : 0),
      speed: 12,
      bounciness: 6,
      useNativeDriver: true,
    }).start();
  }, [named, told, progress]);

  // scaleX and not width: width cannot go on the native driver, and this sits
  // directly above a text field, which is the worst place in the app to hand
  // work back to the JS thread.
  const filling = { transform: [{ scaleX: progress }] };

  /** Adds the attachment optimistically, then swaps in the server's copy. The
   *  uri is the identity throughout - ids do not exist yet at insert time. */
  const attach = async (draft: Attachment, mime: string) => {
    if (!device) return;
    setAttachments((current) => [...current, draft]);
    try {
      const item = await uploadMedia(device, draft.uri, mime, draft.seconds);
      if (!mounted.current) return;
      setAttachments((current) =>
        current.map((a) => (a.uri === draft.uri ? { ...a, item } : a)),
      );
    } catch {
      if (!mounted.current) return;
      setAttachments((current) =>
        current.map((a) => (a.uri === draft.uri ? { ...a, failed: true } : a)),
      );
    }
  };

  const addPhoto = async (fromCamera: boolean) => {
    setError(null);
    const permission = fromCamera
      ? await ImagePicker.requestCameraPermissionsAsync()
      : await ImagePicker.requestMediaLibraryPermissionsAsync();
    if (!permission.granted) {
      setError(fromCamera ? 'No camera access.' : 'No access to your photos.');
      return;
    }

    const options: ImagePicker.ImagePickerOptions = {
      mediaTypes: ['images'],
      // Re-encoded rather than sent as-is: a modern phone photo is 5-8 MB and
      // this is a thumbnail on a map card, not a print.
      quality: 0.7,
    };
    const result = fromCamera
      ? await ImagePicker.launchCameraAsync(options)
      : await ImagePicker.launchImageLibraryAsync(options);
    const picked = result.canceled ? null : result.assets[0];
    if (!picked) return;

    // quality: 0.7 re-encodes to JPEG, so the asset's own mimeType (HEIC on
    // iOS) describes the original and not what is about to be sent.
    await attach({ uri: picked.uri, kind: 'photo' }, 'image/jpeg');
  };

  const startRecording = async () => {
    setError(null);
    const permission = await requestRecordingPermissionsAsync();
    if (!permission.granted) {
      setError('No microphone access.');
      return;
    }
    // Without this iOS records at earpiece volume and routes playback to the
    // receiver, which sounds like a broken recording rather than a quiet one.
    await setAudioModeAsync({ allowsRecording: true, playsInSilentMode: true });
    await recorder.prepareToRecordAsync();
    Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Light).catch(() => {});
    recorder.record();
  };

  const stopRecording = async () => {
    if (stopping.current) return;
    stopping.current = true;
    try {
      await recorder.stop();
      await setAudioModeAsync({ allowsRecording: false });
      const uri = recorder.uri;
      if (!uri) return;
      await attach({ uri, kind: 'audio', seconds: recording.durationMillis / 1000 }, 'audio/m4a');
    } finally {
      // finally, not the happy path: a recorder that hands back no uri would
      // otherwise leave the flag set and the Record button dead for the session.
      stopping.current = false;
    }
  };

  // Stopping at the cap rather than refusing afterwards: a recording thrown
  // away at three minutes is three minutes of somebody's story gone.
  useEffect(() => {
    if (recording.isRecording && recording.durationMillis / 1000 >= MAX_RECORDING_SECONDS) {
      stopRecording();
    }
    // stopRecording is deliberately not a dependency: it is rebuilt every
    // render, and the re-entry that used to allow is handled by `stopping`.
  }, [recording.isRecording, recording.durationMillis]);

  const post = async () => {
    if (!position || !device) return;
    setPosting(true);
    setError(null);

    const trimmedYear = year.trim();
    const draft: Draft = {
      place_name: placeName.trim(),
      summary: summary.trim(),
      tags,
      happened_at:
        when === 'today'
          ? new Date().toISOString().slice(0, 10)
          : /^\d{4}$/.test(trimmedYear)
            ? `${trimmedYear}-01-01`
            : null,
      happened_precision: when === 'today' ? 'day' : /^\d{4}$/.test(trimmedYear) ? 'year' : null,
      // 1 January of the year, like happened_at: a seal is a promise about a
      // year, and asking somebody to pick a day for 2041 is a picker nobody
      // needs. A year already past is simply not a seal - the server treats a
      // date that has come as no date at all.
      opens_at: opensAt,
      media_ids: attachments.flatMap((a) => (a.item ? [a.item.id] : [])),
      display_name: displayName.trim() || null,
    };

    try {
      const memory = await submitMemory(device, position, draft);
      Haptics.notificationAsync(Haptics.NotificationFeedbackType.Success).catch(() => {});
      onPosted(memory);
      onClose();
    } catch {
      if (mounted.current) setError('Could not post that. Try again in a moment.');
    } finally {
      if (mounted.current) setPosting(false);
    }
  };

  return (
    <Modal
      visible={visible}
      animationType="slide"
      presentationStyle="pageSheet"
      onRequestClose={onClose}
    >
      <KeyboardAvoidingView
        style={styles.sheet}
        behavior={Platform.OS === 'ios' ? 'padding' : undefined}
      >
        <View style={styles.bar}>
          <Pressable style={dim()} onPress={onClose} accessibilityRole="button" hitSlop={10}>
            <Text style={styles.barAction}>Cancel</Text>
          </Pressable>
          <Text style={styles.barTitle}>Add a memory</Text>
          <Pressable style={dim()} onPress={post} disabled={!ready} accessibilityRole="button" hitSlop={10}>
            <Text style={[styles.barAction, styles.post, !ready && styles.disabled]}>
              {posting ? 'Posting…' : 'Post'}
            </Text>
          </Pressable>
        </View>

        {/* The rule under the header, doing a second job rather than gaining a
            neighbour: it fills as the two required fields land and turns seal
            when the thing can be posted. Same promise the unlock ring makes,
            and it costs a line rather than adding one. */}
        <View style={styles.track}>
          <Animated.View style={[styles.fill, ready && styles.fillReady, filling]} />
        </View>
        {/* What is still missing, said once, close enough to the greyed-out
            Post to be read as the reason for it. */}
        <Text style={[styles.hint, ready && styles.hintReady]}>{hint}</Text>

        <ScrollView contentContainerStyle={styles.body} keyboardShouldPersistTaps="handled">
          {/* Not decoration. It is the one thing that makes this different from
              posting anywhere else, and it has to be visible while typing. */}
          <View style={styles.here}>
            <Text style={styles.hereLabel}>Filed at</Text>
            <Text style={styles.hereValue}>
              {position
                ? `${position.lat.toFixed(5)}, ${position.lng.toFixed(5)}`
                : 'Waiting for your location'}
            </Text>
            <Text style={styles.hereNote}>
              A memory goes where you are standing. Other people will have to come here to read
              it.
            </Text>
          </View>

          <Field label="What happened?">
            <TextInput
              style={[styles.input, styles.prose]}
              value={summary}
              onChangeText={setSummary}
              placeholder="We sat here until it got light and nobody wanted to say so."
              placeholderTextColor={color.inkFaint}
              multiline
              maxLength={2000}
              textAlignVertical="top"
            />
            <Text style={styles.counter}>
              {summary.trim().length < MIN_SUMMARY
                ? `${MIN_SUMMARY - summary.trim().length} more characters`
                : `${summary.length} / 2000`}
            </Text>
          </Field>

          <Field label="What is this place called?">
            <TextInput
              style={styles.input}
              value={placeName}
              onChangeText={setPlaceName}
              placeholder="The bench by the harbour"
              placeholderTextColor={color.inkFaint}
              maxLength={200}
              returnKeyType="next"
            />
          </Field>

          <Field label="When">
            <View style={styles.row}>
              <Chip label="Today" on={when === 'today'} onPress={() => setWhen('today')} />
              <Chip label="Earlier" on={when === 'earlier'} onPress={() => setWhen('earlier')} />
              {when === 'earlier' && (
                <TextInput
                  style={[styles.input, styles.year]}
                  value={year}
                  onChangeText={(next) => setYear(next.replace(/[^0-9]/g, '').slice(0, 4))}
                  placeholder="1998"
                  placeholderTextColor={color.inkFaint}
                  keyboardType="number-pad"
                  accessibilityLabel="Year it happened"
                />
              )}
            </View>
            {/* ponytail: a year, not a date. A full picker is another
                dependency for a field most submissions leave on Today. */}
          </Field>

          <Field label="Who can read it">
            <View style={styles.row}>
              <Chip label="Anyone here" on={seal === 'now'} onPress={() => setSeal('now')} />
              <Chip label="Nobody until" on={seal === 'later'} onPress={() => setSeal('later')} />
              {seal === 'later' && (
                <TextInput
                  style={[styles.input, styles.year]}
                  value={sealYear}
                  onChangeText={(next) => setSealYear(next.replace(/[^0-9]/g, '').slice(0, 4))}
                  placeholder="2041"
                  placeholderTextColor={color.inkFaint}
                  keyboardType="number-pad"
                  accessibilityLabel="Year this memory opens"
                />
              )}
            </View>
            {/* Including you. A time capsule that its author can read is a
                draft, and the gate is deliberately checked before the one that
                opens a memory for the person who filed it. */}
          </Field>

          <Field label="Tags">
            <View style={styles.row}>
              {SUBMISSION_TAGS.map((tag) => (
                <Chip
                  key={tag}
                  label={tag}
                  on={tags.includes(tag)}
                  onPress={() =>
                    setTags((current) =>
                      current.includes(tag)
                        ? current.filter((t) => t !== tag)
                        : current.length < 8
                          ? [...current, tag]
                          : current,
                    )
                  }
                />
              ))}
            </View>
          </Field>

          <Field label="Photos">
            <View style={styles.row}>
              {photos.map((photo) => (
                <Pressable
                  key={photo.uri}
                  style={dim()}
                  onPress={() =>
                    setAttachments((current) => current.filter((a) => a.uri !== photo.uri))
                  }
                  accessibilityRole="button"
                  accessibilityLabel="Remove this photo"
                >
                  <Image
                    source={{ uri: photo.item ? mediaUrl(photo.item) : photo.uri }}
                    style={[styles.thumb, photo.failed && styles.thumbFailed]}
                  />
                  {!photo.item && !photo.failed && (
                    <View style={styles.thumbBusy}>
                      <ActivityIndicator size="small" color={color.paper} />
                    </View>
                  )}
                  {photo.failed && <Text style={styles.thumbError}>failed</Text>}
                </Pressable>
              ))}
              {photos.length < MAX_PHOTOS && (
                <>
                  <Secondary label="Camera" onPress={() => addPhoto(true)} />
                  <Secondary label="Library" onPress={() => addPhoto(false)} />
                </>
              )}
            </View>
          </Field>

          <Field label="Say it out loud">
            {sound ? (
              <View style={styles.row}>
                <Text style={styles.recorded}>
                  {sound.failed ? 'Upload failed' : `Recorded · ${duration(sound.seconds ?? 0)}`}
                </Text>
                <Secondary
                  label="Remove"
                  onPress={() =>
                    setAttachments((current) => current.filter((a) => a.kind !== 'audio'))
                  }
                />
              </View>
            ) : recording.isRecording ? (
              <View style={styles.row}>
                {/* The one red dot in the app that is not the seal doing its
                    usual job - recording is the other thing worth noticing. */}
                <View style={styles.dot} />
                <Text style={styles.recorded}>{duration(recording.durationMillis / 1000)}</Text>
                <Secondary label="Stop" onPress={stopRecording} />
              </View>
            ) : (
              <Secondary label="Record" onPress={startRecording} />
            )}
          </Field>

          <Field label="Signed">
            <TextInput
              style={styles.input}
              value={displayName}
              onChangeText={onDisplayName}
              placeholder="Anonymous"
              placeholderTextColor={color.inkFaint}
              maxLength={60}
              autoCapitalize="words"
            />
          </Field>

          {error && <Text style={styles.error}>{error}</Text>}
        </ScrollView>
      </KeyboardAvoidingView>
    </Modal>
  );
}

function Field({ label: name, children }: { label: string; children: React.ReactNode }) {
  return (
    <View style={styles.field}>
      <Text style={styles.fieldLabel}>{name}</Text>
      {children}
    </View>
  );
}

/** A chip that answers being touched.
 *
 *  Twenty-odd of these carry every choice on this screen except the two text
 *  fields, and a control that only changes colour reads as a label somebody
 *  recoloured. The tick is `selectionAsync`, the same one the map uses when a
 *  pin opens: this is picking, not confirming, and it must not borrow the
 *  weight of the unlock. */
function Chip({ label: text, on, onPress }: { label: string; on: boolean; onPress: () => void }) {
  const pop = useRef(new Animated.Value(1)).current;
  const first = useRef(true);

  useEffect(() => {
    // Not on mount, or every chip on the screen flinches when the sheet opens.
    if (first.current) {
      first.current = false;
      return;
    }
    pop.setValue(on ? 0.88 : 1.06);
    Animated.spring(pop, { toValue: 1, speed: 20, bounciness: 12, useNativeDriver: true }).start();
  }, [on, pop]);

  return (
    <Pressable
      onPress={() => {
        Haptics.selectionAsync().catch(() => {});
        onPress();
      }}
      accessibilityRole="button"
      accessibilityState={{ selected: on }}
      style={dim()}
    >
      <Animated.View style={[styles.chip, on && styles.chipOn, { transform: [{ scale: pop }] }]}>
        <Text style={[styles.chipText, on && styles.chipTextOn]}>{text}</Text>
      </Animated.View>
    </Pressable>
  );
}

function Secondary({ label: text, onPress }: { label: string; onPress: () => void }) {
  return (
    <Pressable
      onPress={() => {
        Haptics.selectionAsync().catch(() => {});
        onPress();
      }}
      accessibilityRole="button"
      style={dim(styles.secondary)}
    >
      <Text style={styles.secondaryText}>{text}</Text>
    </Pressable>
  );
}

const THUMB = 76;

const styles = StyleSheet.create({
  sheet: { flex: 1, backgroundColor: color.paper },
  bar: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingHorizontal: 20,
    paddingTop: 18,
    paddingBottom: 14,
  },
  barTitle: { fontFamily: font.displaySemi, fontSize: 17, color: color.ink },
  barAction: { ...label, color: color.inkFaint },
  post: { color: color.seal },
  disabled: { opacity: 0.35 },

  // Full bleed, because it replaces the header's bottom rule rather than
  // sitting under it.
  track: { height: 2, backgroundColor: color.rule, overflow: 'hidden' },
  fill: {
    height: 2,
    backgroundColor: color.inkFaint,
    // Grows from the left rather than from the middle, which is what scaleX
    // does by default and reads as a bar sliding open.
    transformOrigin: 'left',
  },
  fillReady: { backgroundColor: color.seal },
  hint: { ...label, fontSize: 9, color: color.inkFaint, paddingHorizontal: 20, paddingTop: 12 },
  hintReady: { color: color.seal },
  body: { padding: 20, paddingBottom: 56, gap: 26 },

  here: {
    borderWidth: 1,
    borderColor: color.rule,
    borderRadius: 4,
    padding: 14,
    gap: 6,
    backgroundColor: color.paperRaised,
  },
  hereLabel: { ...label, fontSize: 9 },
  hereValue: { fontFamily: font.monoMedium, fontSize: 14, color: color.ink },
  hereNote: { fontFamily: font.prose, fontSize: 14, lineHeight: 21, color: color.inkSoft },

  field: { gap: 10 },
  fieldLabel: { ...label, color: color.inkSoft },
  input: {
    ...input,
  },
  prose: { minHeight: 130, lineHeight: 26 },
  counter: { ...label, fontSize: 9, textAlign: 'right' },
  year: { width: 96, fontFamily: font.mono, fontSize: 15 },

  row: { flexDirection: 'row', flexWrap: 'wrap', alignItems: 'center', gap: 8 },
  chip: {
    borderWidth: 1,
    borderColor: color.rule,
    borderRadius: 3,
    paddingHorizontal: 12,
    // 40 tall with the label's line box, and the row gap keeps neighbours
    // from stealing the edges of the target.
    paddingVertical: 11,
  },
  chipOn: { backgroundColor: color.ink, borderColor: color.ink },
  chipText: { ...label, fontSize: 10, color: color.inkSoft },
  chipTextOn: { color: color.paper },

  secondary: {
    borderWidth: 1,
    borderColor: color.ink,
    borderRadius: 4,
    paddingHorizontal: 16,
    paddingVertical: 12,
  },
  secondaryText: { ...label, fontSize: 10, color: color.ink },

  thumb: { width: THUMB, height: THUMB, borderRadius: 4, backgroundColor: color.rule },
  thumbFailed: { opacity: 0.4 },
  thumbBusy: {
    position: 'absolute',
    top: 0,
    left: 0,
    right: 0,
    bottom: 0,
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: 'rgba(0,0,0,0.35)',
    borderRadius: 4,
  },
  thumbError: { ...label, fontSize: 9, color: color.seal, textAlign: 'center' },

  dot: { width: 10, height: 10, borderRadius: 5, backgroundColor: color.seal },
  recorded: { fontFamily: font.monoMedium, fontSize: 14, color: color.ink },

  error: { fontFamily: font.mono, fontSize: 13, color: color.seal, textAlign: 'center' },
});
