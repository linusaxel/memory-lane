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
  deleteMemory,
  mediaUrl,
  submitMemory,
  updateMemory,
  uploadMedia,
  wasRefused,
  type Coordinates,
  type Draft,
  type LocatedMemory,
  type MediaItem,
} from './api.ts';
import Avatar from './Avatar.tsx';
import CloseButton from './CloseButton.tsx';
import { duration, happened } from './format.ts';
import { button, buttonTextSmall, color, dim, label, radius, story, sunk } from './theme.ts';

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
  /** Who it will be signed by, shown where the open sheet shows it. */
  author: { name: string; avatar_url?: string | null };
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
  author,
}: Props) {
  const isEditing = !!editing;
  // The title is the place row's name - docs/10, "The title is the place name".
  const [placeName, setPlaceName] = useState('');
  const [summary, setSummary] = useState('');
  const [day, setDay] = useState(() => new Date());
  const [pickingDay, setPickingDay] = useState(false);
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
    setDay(new Date());
    setPickingDay(false);
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
  const when = happened(isoDay(day), 'day');
  const pickDay = () =>
    Platform.OS === 'ios'
      ? setPickingDay((open) => !open)
      : // Android's picker is a dialog, not an inline control.
        DateTimePickerAndroid.open({
          value: day,
          mode: 'date',
          maximumDate: new Date(),
          onValueChange: (_, picked) => setDay(picked),
        });

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
    } catch (e) {
      if (!mounted.current) return;
      setAttachments((current) =>
        current.map((a) => (a.uri === draft.uri ? { ...a, failed: true } : a)),
      );
      // The statuses api/media.py and api/write.py refuse an upload with.
      const status = String(e).match(/API (\d+)/)?.[1];
      setError(
        status === '413'
          ? "That one's too big to attach."
          : status === '415'
            ? "That kind of file can't be attached."
            : status === '429'
              ? "That's all the uploads for today."
              : "That didn't upload. Try again in a moment.",
      );
    }
  };

  const addPhoto = async (fromCamera: boolean) => {
    setError(null);
    const permission = fromCamera
      ? await ImagePicker.requestCameraPermissionsAsync()
      : await ImagePicker.requestMediaLibraryPermissionsAsync();
    if (!permission.granted) {
      setError(fromCamera ? 'Allow camera access in Settings to take a photo.' : 'Allow photo access in Settings to add one.');
      return;
    }

    const options: ImagePicker.ImagePickerOptions = {
      mediaTypes: ['images'],
      // Re-encoded rather than sent as-is: a modern phone photo is 5-8 MB and
      // this is a thumbnail on a map card, not a print.
      quality: 0.7,
      // A HEIC is handed back as-is, and uncompressed, unless the picker is
      // asked for the compatible representation: then it is a JPEG and
      // `quality` applies. iOS only; Android returns JPEG already.
      preferredAssetRepresentationMode: ImagePicker.UIImagePickerPreferredAssetRepresentationMode.Compatible,
    };
    const result = fromCamera
      ? await ImagePicker.launchCameraAsync(options)
      : await ImagePicker.launchImageLibraryAsync(options);
    const picked = result.canceled ? null : result.assets[0];
    if (!picked) return;

    // The picker keeps a PNG a PNG, so the type is what it says it wrote.
    await attach({ uri: picked.uri, kind: 'photo' }, picked.mimeType ?? 'image/jpeg');
  };

  const startRecording = async () => {
    setError(null);
    const permission = await requestRecordingPermissionsAsync();
    if (!permission.granted) {
      setError('Allow microphone access in Settings to record.');
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
    } catch (e) {
      if (!mounted.current) return;
      setError(
        wasRefused(e)
          ? "That can't be posted here. Take out anything hateful, sexual or threatening, or anyone's contact details."
          : isEditing
            ? "That didn't save. Try again in a moment."
            : "That didn't post. Try again in a moment.",
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
      if (mounted.current) setError("That didn't delete. Try again in a moment.");
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
        {/* The open sheet with nothing in it yet: the same title, byline and
            story type, in the same places, so what you write is what people
            standing here will read (docs/10, "Reading and writing are one
            page"). Cancel and Post are the only chrome. */}
        <View style={styles.bar}>
          <CloseButton onPress={onClose} label="Cancel" />
          <Pressable
            style={dim([styles.post, !ready && styles.disabled])}
            onPress={post}
            disabled={!ready}
            hitSlop={4}
            accessibilityRole="button"
            accessibilityLabel={isEditing ? 'Save' : 'Post'}
          >
            <Text style={styles.postText}>
              {posting ? (isEditing ? 'Saving…' : 'Posting…') : isEditing ? 'Save' : 'Post'}
            </Text>
          </Pressable>
        </View>

        <ScrollView contentContainerStyle={styles.body} keyboardShouldPersistTaps="handled">
          <TextInput
            style={[styles.slot, styles.title]}
            value={placeName}
            onChangeText={setPlaceName}
            placeholder="The night the ferry horn went off"
            placeholderTextColor={color.inkFaint}
            accessibilityLabel="Title"
            testID="title"
            maxLength={200}
            multiline
            submitBehavior="blurAndSubmit"
            returnKeyType="next"
          />

          <View style={styles.byline}>
            <Avatar url={author.avatar_url ?? null} name={author.name} size={20} />
            <Text style={styles.meta}>
              <Text style={styles.metaInk}>{author.name}</Text>
              {' · '}
              <Text
                style={styles.metaInk}
                accessibilityRole="button"
                accessibilityLabel={`When, ${when?.within} ${when?.year}`}
                onPress={pickDay}
              >
                {when?.within} {when?.year} ▾
              </Text>
              {!isEditing && ' · here'}
            </Text>
          </View>
          {pickingDay && (
            <DateTimePicker
              value={day}
              mode="date"
              display="inline"
              maximumDate={new Date()}
              onValueChange={(_, picked) => {
                setDay(picked);
                setPickingDay(false);
              }}
            />
          )}

          <TextInput
            style={[styles.slot, styles.story]}
            value={summary}
            onChangeText={setSummary}
            placeholder="We sat here until it got light and nobody wanted to say so. #nightlife"
            placeholderTextColor={color.inkFaint}
            accessibilityLabel="Description"
            testID="story"
            multiline
            maxLength={MAX_SUMMARY}
            textAlignVertical="top"
          />
          {/* Only near the limit: a count from the first letter reads as a nag. */}
          {summary.length > MAX_SUMMARY - 200 && (
            <Text style={styles.meta}>{`${summary.length} / ${MAX_SUMMARY}`}</Text>
          )}

          {/* Where the open sheet shows them, at the size it shows them. */}
          {photos.map((photo) => (
            <View key={photo.uri} style={styles.part}>
              <View>
                <Image
                  testID={photo.item ? 'photo' : 'photo-uploading'}
                  source={{ uri: photo.item ? mediaUrl(photo.item) : photo.uri }}
                  style={[styles.photo, photo.failed && styles.photoFailed]}
                />
                {!photo.item && !photo.failed && (
                  <View style={styles.photoBusy}>
                    <ActivityIndicator size="small" color={color.paper} />
                  </View>
                )}
              </View>
              <View style={styles.row}>
                {photo.failed && <Text style={styles.error}>Upload failed</Text>}
                <Action
                  label="Remove photo"
                  onPress={() =>
                    setAttachments((current) => current.filter((a) => a.uri !== photo.uri))
                  }
                />
              </View>
            </View>
          ))}
          {photos.length < MAX_PHOTOS && (
            <View style={styles.row}>
              <Action label="Take photo" onPress={() => addPhoto(true)} />
              <Action label="Choose photo" onPress={() => addPhoto(false)} />
            </View>
          )}

          {AUDIO && (
            <View style={styles.row}>
              {sound ? (
                <>
                  <Text style={styles.meta}>
                    {sound.failed ? 'Upload failed' : `Recorded · ${duration(sound.seconds ?? 0)}`}
                  </Text>
                  <Action
                    label="Remove"
                    onPress={() =>
                      setAttachments((current) => current.filter((a) => a.kind !== 'audio'))
                    }
                  />
                </>
              ) : recording.isRecording ? (
                <>
                  {/* The one red dot in the app that is not the seal doing its
                      usual job - recording is the other thing worth noticing. */}
                  <View style={styles.dot} />
                  <Text style={styles.meta}>{duration(recording.durationMillis / 1000)}</Text>
                  <Action label="Stop" onPress={stopRecording} />
                </>
              ) : (
                <Action label="Say it out loud" onPress={startRecording} />
              )}
            </View>
          )}

          {error && <Text style={styles.error}>{error}</Text>}

          {isEditing && (
            <Pressable
              style={dim(styles.delete)}
              onPress={pressDelete}
              disabled={deleting}
              hitSlop={12}
              accessibilityRole="button"
            >
              <Text style={styles.error}>
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
    >
      {({ pressed }) => (
        <Animated.View
          style={[styles.chip, on && styles.chipOn, pressed && sunk(styles.chip), { transform: [{ scale: pop }] }]}
        >
          <Text style={[styles.chipText, on && styles.chipTextOn]}>{text}</Text>
        </Animated.View>
      )}
    </Pressable>
  );
}

/** A text action, as a note's Rewrite and Remove are on the open sheet. */
function Action({ label: text, onPress }: { label: string; onPress: () => void }) {
  return (
    <Pressable
      onPress={() => {
        Haptics.selectionAsync().catch(() => {});
        onPress();
      }}
      accessibilityRole="button"
      hitSlop={12}
      style={dim()}
    >
      <Text style={styles.action}>{text}</Text>
    </Pressable>
  );
}

const styles = StyleSheet.create({
  sheet: { flex: 1, backgroundColor: color.paper },
  bar: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingHorizontal: 20,
    paddingTop: 18,
    paddingBottom: 8,
  },
  post: { ...button.solid, ...button.small },
  postText: { ...buttonTextSmall, color: color.paper },
  disabled: { opacity: 0.35 },

  // MemorySheet's reading column: 24 in, 8 inside a part, 24 between parts.
  body: { paddingHorizontal: 24, paddingTop: 16, paddingBottom: 56 },
  // A field with no box: the cursor and the placeholder say it is editable.
  slot: { padding: 0, margin: 0 },
  title: story.title,
  story: { ...story.body, minHeight: 130, marginTop: 24 },
  byline: { flexDirection: 'row', alignItems: 'center', gap: 8, marginTop: 8 },
  meta: { ...story.meta, flexShrink: 1 },
  metaInk: { color: color.ink },
  part: { gap: 8, marginTop: 24 },
  row: { flexDirection: 'row', flexWrap: 'wrap', alignItems: 'center', gap: 16, marginTop: 24 },
  action: { ...story.meta, color: color.inkSoft },

  chip: {
    borderWidth: 1,
    borderColor: color.rule,
    borderRadius: radius.pill,
    paddingHorizontal: 14,
    // 40 tall with the label's line box, and the row gap keeps neighbours
    // from stealing the edges of the target.
    paddingTop: 11,
    paddingBottom: 9,
    borderBottomWidth: 3,
  },
  chipOn: { backgroundColor: color.ember, borderColor: color.ember, borderBottomColor: color.emberDeep },
  chipText: { ...label, fontSize: 12, color: color.inkSoft },
  chipTextOn: { color: color.paper },

  // MemoryMedia's photo, so a photo here is the size it will be read at.
  photo: { width: '100%', aspectRatio: 4 / 3, borderRadius: radius.field, backgroundColor: color.rule },
  photoFailed: { opacity: 0.4 },
  photoBusy: {
    position: 'absolute',
    top: 0,
    left: 0,
    right: 0,
    bottom: 0,
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: color.scrim,
    borderRadius: radius.field,
  },

  dot: { width: 10, height: 10, borderRadius: 5, backgroundColor: color.ember },
  error: { ...story.meta, color: color.ember },
  delete: { marginTop: 40, alignSelf: 'flex-start' },
});
