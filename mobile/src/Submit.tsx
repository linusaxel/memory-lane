/** The only screen in the app that writes, or edits, or deletes - spec in
 *  "Writing", UI.md. Doubles as the editor for a memory you already filed:
 *  `editing` prefills every field from it and Post becomes Save. */

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
import DateTimePicker, { DateTimePickerAndroid } from '@react-native-community/datetimepicker';
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
  AUDIO,
  SUBMISSION_TAGS,
  deleteMemory,
  mediaUrl,
  submitMemory,
  updateMemory,
  uploadMedia,
  type Coordinates,
  type Draft,
  type LocatedMemory,
  type MediaItem,
} from './api.ts';
import { duration } from './format.ts';
import { button, buttonText, color, dim, font, input, label } from './theme.ts';

const MAX_SUMMARY = 2000;
const MAX_PHOTOS = 4;
/** Long enough for a story, short enough that nobody uploads a podcast. */
const MAX_RECORDING_SECONDS = 180;

type Props = {
  visible: boolean;
  /** Where the person is. Null means the form cannot open - see the header.
   *  Ignored while editing: the pin does not move after it is filed. */
  position: Coordinates | null;
  device: string | null;
  onClose: () => void;
  onPosted: (memory: LocatedMemory) => void;
  /** Set to open this screen as an editor for a memory already filed, instead
   *  of a blank submission. Only ever a memory this account owns. */
  editing?: LocatedMemory | null;
  onSaved?: (memory: LocatedMemory) => void;
  onDeleted?: (id: number) => void;
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
  onClose,
  onPosted,
  editing,
  onSaved,
  onDeleted,
}: Props) {
  const isEditing = !!editing;
  // The title is the place row's name - docs/10, "The title is the place name".
  const [placeName, setPlaceName] = useState('');
  const [summary, setSummary] = useState('');
  const [tags, setTags] = useState<string[]>([]);
  const [day, setDay] = useState(() => new Date());
  const [attachments, setAttachments] = useState<Attachment[]>([]);
  const [posting, setPosting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  // Two-step rather than a native Alert: this app never uses a system dialog,
  // and a second, differently-worded press is enough friction for something
  // reversible only by refiling the memory from scratch.
  const [confirmingDelete, setConfirmingDelete] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const confirmTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

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
      if (confirmTimer.current) clearTimeout(confirmTimer.current);
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
    setDay(new Date());
    setAttachments([]);
    setError(null);
    setConfirmingDelete(false);
    if (confirmTimer.current) clearTimeout(confirmTimer.current);
  }, [visible]);

  // Prefills from the memory being edited.
  useEffect(() => {
    if (!visible || !editing) return;
    setPlaceName(editing.place.name);
    setSummary(editing.summary);
    setTags(editing.tags);
    setDay(editing.happened_at ? localDay(editing.happened_at) : new Date());
    setAttachments(
      editing.media.map((item) => ({
        uri: mediaUrl(item),
        kind: item.kind,
        seconds: item.duration_seconds ?? undefined,
        item,
      })),
    );
    // Keyed on the id, not the object: App.tsx hands this a fresh reference
    // on every render, and re-running on that would fight anything typed.
  }, [visible, editing?.id]);

  const photos = attachments.filter((a) => a.kind === 'photo');
  const sound = attachments.find((a) => a.kind === 'audio');
  const uploading = attachments.some((a) => !a.item && !a.failed);
  const named = placeName.trim().length > 0;
  const told = summary.trim().length > 0;
  const ready =
    (isEditing || !!position) && !!device && named && told && !uploading && !posting;

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
    if (!device || (!isEditing && !position)) return;
    setPosting(true);
    setError(null);

    const editDraft: Draft = {
      place_name: placeName.trim(),
      summary: summary.trim(),
      tags,
      happened_at: isoDay(day),
      happened_precision: 'day',
      media_ids: attachments.flatMap((a) => (a.item ? [a.item.id] : [])),
    };

    try {
      if (editing) {
        const memory = await updateMemory(device, editing.id, editDraft);
        Haptics.notificationAsync(Haptics.NotificationFeedbackType.Success).catch(() => {});
        onSaved?.(memory);
      } else {
        const memory = await submitMemory(device, position!, editDraft);
        Haptics.notificationAsync(Haptics.NotificationFeedbackType.Success).catch(() => {});
        onPosted(memory);
      }
      onClose();
    } catch {
      if (!mounted.current) return;
      setError(
        isEditing
          ? 'Could not save that. Try again in a moment.'
          : 'Could not post that. Try again in a moment.',
      );
    } finally {
      if (mounted.current) setPosting(false);
    }
  };

  const pressDelete = () => {
    if (!confirmingDelete) {
      setConfirmingDelete(true);
      confirmTimer.current = setTimeout(() => setConfirmingDelete(false), 3000);
      return;
    }
    if (confirmTimer.current) clearTimeout(confirmTimer.current);
    deleteThis();
  };

  const deleteThis = async () => {
    if (!device || !editing) return;
    setDeleting(true);
    setError(null);
    try {
      await deleteMemory(device, editing.id);
      Haptics.notificationAsync(Haptics.NotificationFeedbackType.Success).catch(() => {});
      onDeleted?.(editing.id);
      onClose();
    } catch {
      if (mounted.current) setError('Could not delete that. Try again in a moment.');
    } finally {
      if (mounted.current) {
        setDeleting(false);
        setConfirmingDelete(false);
      }
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
          <Text style={styles.barTitle}>{isEditing ? 'Edit memory' : 'Add a memory'}</Text>
          <Pressable style={dim()} onPress={post} disabled={!ready} accessibilityRole="button" hitSlop={10}>
            <Text style={[styles.barAction, styles.post, !ready && styles.disabled]}>
              {posting ? (isEditing ? 'Saving…' : 'Posting…') : isEditing ? 'Save' : 'Post'}
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

        <ScrollView contentContainerStyle={styles.body} keyboardShouldPersistTaps="handled">
          <Field label="Title">
            <TextInput
              style={styles.input}
              value={placeName}
              onChangeText={setPlaceName}
              placeholder="The night the ferry horn went off"
              placeholderTextColor={color.inkFaint}
              maxLength={200}
              returnKeyType="next"
            />
          </Field>

          <Field label="Description">
            <TextInput
              style={[styles.input, styles.prose]}
              value={summary}
              onChangeText={setSummary}
              placeholder="We sat here until it got light and nobody wanted to say so."
              placeholderTextColor={color.inkFaint}
              multiline
              maxLength={MAX_SUMMARY}
              textAlignVertical="top"
            />
            {/* Only near the limit: a count from the first letter reads as a nag. */}
            {summary.length > MAX_SUMMARY - 200 && (
              <Text style={styles.counter}>{`${summary.length} / ${MAX_SUMMARY}`}</Text>
            )}
          </Field>

          <Field label="When">
            <View style={styles.row}>
              {Platform.OS === 'ios' ? (
                <DateTimePicker
                  value={day}
                  mode="date"
                  display="compact"
                  maximumDate={new Date()}
                  onValueChange={(_, picked) => setDay(picked)}
                />
              ) : (
                // Android's picker is a dialog, not an inline control.
                <Secondary
                  label={isoDay(day)}
                  onPress={() =>
                    DateTimePickerAndroid.open({
                      value: day,
                      mode: 'date',
                      maximumDate: new Date(),
                      onValueChange: (_, picked) => setDay(picked),
                    })
                  }
                />
              )}
            </View>
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

          {AUDIO && (
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
          )}

          {error && <Text style={styles.error}>{error}</Text>}

          {isEditing && (
            <Pressable
              style={dim(styles.delete)}
              onPress={pressDelete}
              disabled={deleting}
              accessibilityRole="button"
            >
              <Text style={styles.deleteText}>
                {deleting
                  ? 'Deleting…'
                  : confirmingDelete
                    ? 'Tap again to delete'
                    : 'Delete this memory'}
              </Text>
            </Pressable>
          )}
        </ScrollView>
      </KeyboardAvoidingView>
    </Modal>
  );
}

/** YYYY-MM-DD in the phone's own zone. toISOString() is UTC, which files
 *  anything after midnight in Copenhagen under yesterday. */
function isoDay(d: Date): string {
  const pad = (n: number) => String(n).padStart(2, '0');
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;
}

/** The inverse, at local midnight: `new Date('1998-07-12')` is UTC midnight,
 *  which is 11 July anywhere west of Greenwich. */
function localDay(iso: string): Date {
  const [y, m, d] = iso.split('-').map(Number);
  return new Date(y, m - 1, d);
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
export function Chip({ label: text, on, onPress }: { label: string; on: boolean; onPress: () => void }) {
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
  body: { padding: 20, paddingBottom: 56, gap: 26 },

  field: { gap: 10 },
  fieldLabel: { ...label, color: color.inkSoft },
  input: {
    ...input,
  },
  prose: { minHeight: 130, lineHeight: 26 },
  counter: { ...label, fontSize: 9, textAlign: 'right' },

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

  secondary: button.outline,
  secondaryText: { ...buttonText, color: color.ink },

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
    backgroundColor: color.scrim,
    borderRadius: 4,
  },
  thumbError: { ...label, fontSize: 9, color: color.seal, textAlign: 'center' },

  dot: { width: 10, height: 10, borderRadius: 5, backgroundColor: color.seal },
  recorded: { fontFamily: font.monoMedium, fontSize: 14, color: color.ink },

  error: { fontFamily: font.mono, fontSize: 13, color: color.seal, textAlign: 'center' },

  // Same shape as `secondary`, in the app's one red - the accent everywhere
  // else means "openable"; here, like Settings' saveFailed line, it is the
  // other thing this app says in red.
  delete: { ...button.outline, borderColor: color.seal, alignSelf: 'center', marginTop: 12 },
  deleteText: { ...buttonText, color: color.seal },
});
