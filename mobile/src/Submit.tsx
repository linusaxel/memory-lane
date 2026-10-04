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
  type TextStyle,
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
import Flourish from './Flourish.tsx';
import { duration, happened } from './format.ts';
import { hashtagParts } from './hashtags.ts';
import { LOCKET_DEFAULT, LOCKETS, locketOf, type LocketId } from './lockets.ts';
import { blocks, inline, plain, serialize, type Block, type Place, type Size } from './story.ts';
import StoryBody from './StoryBody.tsx';
import { button, buttonTextSmall, color, dim, font, label, radius, story, sunk } from './theme.ts';

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
  /** The author's level: which lockets they can pick. */
  level: number;
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

/** One block of the story being written (story.ts). A photo is known by its
 *  attachment's uri until Post, because the id arrives with the upload. */
type Item = { key: string } & (
  | { kind: 'p' | 'h' | 'quote'; text: string }
  | { kind: 'divider' }
  | { kind: 'photo'; uri: string; size: Size; place: Place; caption: string }
);
type TextItem = Extract<Item, { kind: 'p' | 'h' | 'quote' }>;

let keys = 0;
const key = () => String(++keys);
const empty = (): Item => ({ key: key(), kind: 'p', text: '' });

/** The written blocks as items, a photo's id swapped for its attachment uri. */
function toItems(story: Block[], uriOf: (id: number) => string | undefined): Item[] {
  return story.flatMap((b): Item[] => {
    if (b.kind !== 'photo') return [{ key: key(), ...b }];
    const uri = uriOf(b.id);
    return uri
      ? [{ key: key(), kind: 'photo', uri, size: b.size, place: b.place, caption: b.caption }]
      : [];
  });
}

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
  level,
}: Props) {
  const isEditing = !!editing;
  // The title is the place row's name - docs/10, "The title is the place name".
  const [placeName, setPlaceName] = useState('');
  const [locket, setLocket] = useState<LocketId>(LOCKET_DEFAULT);
  const [items, setItems] = useState<Item[]>(() => [empty()]);
  // The block the toolbar acts on: the text being typed in, or a tapped photo.
  const [current, setCurrent] = useState<string | null>(null);
  const [selection, setSelection] = useState({ start: 0, end: 0 });
  // Set for one render after B or I, to put the caret between the marks.
  const [caret, setCaret] = useState<{ key: string; at: number } | null>(null);
  const [previewing, setPreviewing] = useState(false);
  const inputs = useRef(new Map<string, TextInput>());
  const scroll = useRef<ScrollView>(null);
  // A block added at the end is scrolled to once it has a height.
  const toEnd = useRef(false);
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
    setLocket(LOCKET_DEFAULT);
    setItems([empty()]);
    setCurrent(null);
    setPreviewing(false);
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
    setLocket(locketOf(editing.locket).id);
    setDay(editing.happened_at ? localDay(editing.happened_at) : new Date());
    const filed = editing.media.map((item) => ({
      uri: mediaUrl(item),
      kind: item.kind,
      seconds: item.duration_seconds ?? undefined,
      item,
    }));
    setAttachments(filed);
    // A photo the text does not place (anything filed before it could) goes
    // at the end, full width, where it was read before.
    const written = toItems(
      blocks(editing.summary),
      (id) => filed.find((a) => a.item.id === id)?.uri,
    );
    const unplaced = filed.filter(
      (a) => a.kind === 'photo' && !written.some((i) => i.kind === 'photo' && i.uri === a.uri),
    );
    setItems([
      ...(written.length ? written : [empty()]),
      ...unplaced.map((a): Item => ({
        key: key(),
        kind: 'photo',
        uri: a.uri,
        size: 'l',
        place: 'center',
        caption: '',
      })),
    ]);
    // Keyed on the id, not the object: App.tsx hands this a fresh reference
    // on every render, and re-running on that would fight anything typed.
  }, [visible, editing?.id]);

  const photos = attachments.filter((a) => a.kind === 'photo');
  const sound = attachments.find((a) => a.kind === 'audio');
  const uploading = attachments.some((a) => !a.item && !a.failed);
  const summary = serialize(
    items.flatMap((i): Block[] => {
      if (i.kind !== 'photo') return [i];
      const id = attachments.find((a) => a.uri === i.uri)?.item?.id;
      return id ? [{ kind: 'photo', id, size: i.size, place: i.place, caption: i.caption }] : [];
    }),
  );
  const named = placeName.trim().length > 0;
  const told = plain(summary).trim().length > 0;
  const ready =
    (isEditing || !!position) &&
    !!device &&
    named &&
    told &&
    summary.length <= MAX_SUMMARY &&
    !uploading &&
    !posting;
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
      setAttachments((current) => current.map((a) => (a.uri === draft.uri ? { ...a, item } : a)));
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
      setError(
        fromCamera
          ? 'Allow camera access in Settings to take a photo.'
          : 'Allow photo access in Settings to add one.',
      );
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
      preferredAssetRepresentationMode:
        ImagePicker.UIImagePickerPreferredAssetRepresentationMode.Compatible,
    };
    const result = fromCamera
      ? await ImagePicker.launchCameraAsync(options)
      : await ImagePicker.launchImageLibraryAsync(options);
    const picked = result.canceled ? null : result.assets[0];
    if (!picked) return;

    // Where the writer is, at the size it will be read at until they say.
    insert({ key: key(), kind: 'photo', uri: picked.uri, size: 'l', place: 'center', caption: '' });
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

  // The editor (UI.md, "Writing"): markdown typed or tapped, a block at a time.
  const focus = (k: string) => setTimeout(() => inputs.current.get(k)?.focus(), 0);
  const patch = (k: string, change: Partial<Item>) =>
    setItems((list) => list.map((i) => (i.key === k ? ({ ...i, ...change } as Item) : i)));

  /** New blocks after the current one, or at the end. The story always ends
   *  in text, so there is somewhere to keep writing after a photo. */
  const insert = (...added: Item[]) => {
    setItems((list) => {
      const i = list.findIndex((it) => it.key === current);
      const where = i < 0 ? list.length : i + 1;
      toEnd.current = where >= list.length - 1;
      const next = [...list.slice(0, where), ...added, ...list.slice(where)];
      return isText(next[next.length - 1]) ? next : [...next, empty()];
    });
    setCurrent(added[0].key);
  };

  /** A blank line ends a block and what follows is blocks of its own, so a
   *  pasted story lays itself out. A paragraph that starts with `## ` or `> `
   *  becomes a heading or a quote, and `---` a divider. */
  const write = (item: TextItem, text: string) => {
    let head = text;
    let tail: string | null = null;
    const blank = text.match(/\n[ \t]*\n/);
    if (blank) {
      head = text.slice(0, blank.index);
      tail = text.slice(blank.index! + blank[0].length);
    } else if (item.kind === 'h' && text.includes('\n')) {
      // A heading is one line; Return starts the paragraph under it.
      head = text.slice(0, text.indexOf('\n'));
      tail = text.slice(text.indexOf('\n') + 1);
    }
    let next: Item = { ...item, text: head };
    if (item.kind === 'p' && head.startsWith('## '))
      next = { key: item.key, kind: 'h', text: head.slice(3) };
    else if (item.kind === 'p' && head.startsWith('> '))
      next = { key: item.key, kind: 'quote', text: head.slice(2) };
    else if (item.kind === 'p' && /^-{3,}$/.test(head)) {
      next = { key: item.key, kind: 'divider' };
      tail ??= '';
    }
    if (tail === null) {
      setItems((list) => list.map((i) => (i.key === item.key ? next : i)));
      return;
    }
    const after = toItems(blocks(tail), () => undefined);
    const added = after.length && isText(after[after.length - 1]) ? after : [...after, empty()];
    setItems((list) => list.flatMap((i) => (i.key === item.key ? [next, ...added] : [i])));
    const last = added[added.length - 1];
    setCurrent(last.key);
    focus(last.key);
  };

  /** Backspace in an empty block: a heading or quote turns back into a
   *  paragraph, and an empty paragraph goes, the caret to the text before. */
  const back = (item: TextItem) => {
    if (item.text !== '') return;
    if (item.kind !== 'p') return patch(item.key, { kind: 'p' });
    const i = items.findIndex((it) => it.key === item.key);
    const before = items.slice(0, i).reverse().find(isText);
    if (!before) return;
    setItems((list) => list.filter((it) => it.key !== item.key));
    setCurrent(before.key);
    focus(before.key);
  };

  /** **, or *, around what is selected, or a pair to type into. */
  const mark = (m: string) => {
    const item = items.find((i) => i.key === current);
    if (!item || !isText(item)) return;
    const { start, end } = selection;
    const text =
      item.text.slice(0, start) + m + item.text.slice(start, end) + m + item.text.slice(end);
    patch(item.key, { text });
    setCaret({ key: item.key, at: end + m.length * (start === end ? 1 : 2) });
  };

  /** Heading and Quote turn the block being written, or start one. */
  const turn = (kind: 'h' | 'quote') => {
    const item = items.find((i) => i.key === current);
    if (item && isText(item)) return patch(item.key, { kind: item.kind === kind ? 'p' : kind });
    const added: Item = { key: key(), kind, text: '' };
    insert(added);
    focus(added.key);
  };

  const divider = () => {
    const after = empty();
    insert({ key: key(), kind: 'divider' }, after);
    setCurrent(after.key);
    focus(after.key);
  };

  const move = (by: -1 | 1) => {
    const i = items.findIndex((it) => it.key === current);
    const j = i + by;
    if (i < 0 || j < 0 || j >= items.length) return;
    const next = [...items];
    [next[i], next[j]] = [next[j], next[i]];
    setItems(next);
  };

  const remove = (item: Item) => {
    if (item.kind === 'photo') setAttachments((list) => list.filter((a) => a.uri !== item.uri));
    setItems((list) => {
      const next = list.filter((i) => i.key !== item.key);
      return next.some(isText) ? next : [...next, empty()];
    });
    setCurrent(null);
  };

  // The marks, the blocks, and a look at how it will read.
  // Text, like every action on this screen.
  const tools = (
    <View style={styles.toolbar}>
      {!previewing && (
        <>
          <Action
            label="B"
            spoken="Bold"
            testID="toolbar-bold"
            style={styles.bold}
            onPress={() => mark('**')}
          />
          <Action
            label="I"
            spoken="Italic"
            testID="toolbar-italic"
            style={styles.italic}
            onPress={() => mark('*')}
          />
          <Action label="Heading" testID="toolbar-heading" onPress={() => turn('h')} />
          <Action label="Quote" testID="toolbar-quote" onPress={() => turn('quote')} />
          <Action label="Divider" testID="toolbar-divider" onPress={divider} />
          {photos.length < MAX_PHOTOS && (
            <>
              <Action label="Photo" spoken="Choose photo" onPress={() => addPhoto(false)} />
              <Action label="Camera" spoken="Take photo" onPress={() => addPhoto(true)} />
            </>
          )}
          <Action label="↑" spoken="Move up" testID="block-up" onPress={() => move(-1)} />
          <Action label="↓" spoken="Move down" testID="block-down" onPress={() => move(1)} />
        </>
      )}
      <Action
        label={previewing ? 'Back to writing' : 'Preview'}
        testID="preview"
        onPress={() => setPreviewing((p) => !p)}
      />
    </View>
  );

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
      locket,
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
        {/* Under the bar, not over the keyboard: up here nothing covers it,
            a software keyboard or a hardware one's suggestion strip. */}
        {tools}

        <ScrollView
          ref={scroll}
          style={styles.scroll}
          contentContainerStyle={styles.body}
          keyboardShouldPersistTaps="handled"
          onContentSizeChange={() => {
            if (!toEnd.current) return;
            toEnd.current = false;
            scroll.current?.scrollToEnd();
          }}
        >
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

          {/* The locket its pin is drawn as. One not yet earned says the
              level it opens at (docs/10, "Lockets"). */}
          <ScrollView
            horizontal
            showsHorizontalScrollIndicator={false}
            contentContainerStyle={styles.lockets}
          >
            {LOCKETS.map((l) => {
              const earned = l.level <= level;
              return (
                <Pressable
                  key={l.id}
                  onPress={() => setLocket(l.id)}
                  disabled={!earned}
                  accessibilityRole="radio"
                  accessibilityLabel={earned ? l.name : `${l.name}, level ${l.level}`}
                  accessibilityState={{ selected: locket === l.id, disabled: !earned }}
                  testID={`locket-${l.id}`}
                  style={[styles.locket, locket === l.id && styles.locketOn]}
                >
                  <Image
                    source={l.opened}
                    style={[styles.locketImage, !earned && styles.disabled]}
                  />
                  {!earned && <Text style={styles.locketLevel}>Level {l.level}</Text>}
                </Pressable>
              );
            })}
          </ScrollView>

          {/* The story, a block at a time: what is typed here is what
              StoryBody sets on the open sheet, and Preview shows it so. */}
          <View style={styles.blocks}>
            {previewing ? (
              <StoryBody
                summary={summary}
                media={attachments.flatMap((a) => (a.item ? [a.item] : []))}
              />
            ) : (
              items.map((item, n) => {
                const on = item.key === current;
                if (item.kind === 'divider') {
                  return (
                    <View key={item.key}>
                      <Pressable
                        onPress={() => setCurrent(item.key)}
                        accessibilityRole="button"
                        accessibilityLabel="Divider"
                        style={[styles.divider, on && styles.dividerOn]}
                      >
                        <Flourish />
                      </Pressable>
                      {on && (
                        <View style={styles.row}>
                          <Action label="Remove divider" onPress={() => remove(item)} />
                        </View>
                      )}
                    </View>
                  );
                }
                if (item.kind === 'photo') {
                  const upload = attachments.find((a) => a.uri === item.uri);
                  return (
                    <View key={item.key} style={styles.part}>
                      <View style={[styles[item.place], { width: WIDTH[item.size] }]}>
                        <Pressable
                          onPress={() => setCurrent(item.key)}
                          accessibilityRole="button"
                          accessibilityLabel="Photo"
                          testID={upload?.item ? 'photo' : 'photo-uploading'}
                        >
                          <Image
                            source={{ uri: upload?.item ? mediaUrl(upload.item) : item.uri }}
                            style={[
                              styles.photo,
                              upload?.failed && styles.photoFailed,
                              on && styles.photoOn,
                            ]}
                          />
                          {!upload?.item && !upload?.failed && (
                            <View style={styles.photoBusy}>
                              <ActivityIndicator size="small" color={color.paper} />
                            </View>
                          )}
                        </Pressable>
                        <TextInput
                          style={[styles.slot, styles.caption]}
                          value={item.caption}
                          onChangeText={(caption) =>
                            patch(item.key, { caption: caption.replace(/\n/g, ' ') })
                          }
                          onFocus={() => setCurrent(item.key)}
                          placeholder="Caption"
                          placeholderTextColor={color.inkFaint}
                          accessibilityLabel="Caption"
                          testID="caption"
                          maxLength={140}
                        />
                      </View>
                      {upload?.failed && <Text style={styles.error}>Upload failed</Text>}
                      {on && (
                        <View style={styles.row}>
                          {(['s', 'm', 'l'] as const).map((size) => (
                            <Chip
                              key={size}
                              label={size.toUpperCase()}
                              on={item.size === size}
                              testID={`photo-size-${size}`}
                              onPress={() => patch(item.key, { size })}
                            />
                          ))}
                          {(['left', 'center', 'right'] as const).map((place) => (
                            <Chip
                              key={place}
                              label={place[0].toUpperCase() + place.slice(1)}
                              on={item.place === place}
                              testID={`photo-${place}`}
                              onPress={() => patch(item.key, { place })}
                            />
                          ))}
                          <Action label="Remove photo" onPress={() => remove(item)} />
                        </View>
                      )}
                    </View>
                  );
                }
                const first = items.findIndex(isText) === n;
                return (
                  <TextInput
                    key={item.key}
                    ref={(input) => {
                      if (input) inputs.current.set(item.key, input);
                      else inputs.current.delete(item.key);
                    }}
                    style={[
                      styles.slot,
                      styles[item.kind],
                      first && items.length === 1 && styles.alone,
                    ]}
                    onChangeText={(text) => write(item, text)}
                    onKeyPress={(e) => e.nativeEvent.key === 'Backspace' && back(item)}
                    onFocus={() => setCurrent(item.key)}
                    onSelectionChange={(e) => {
                      setSelection(e.nativeEvent.selection);
                      if (caret) setCaret(null);
                    }}
                    selection={
                      caret?.key === item.key ? { start: caret.at, end: caret.at } : undefined
                    }
                    placeholder={
                      first
                        ? 'We sat here until it got light and nobody wanted to say so. #nightlife'
                        : item.kind === 'h'
                          ? 'Heading'
                          : item.kind === 'quote'
                            ? 'What somebody said'
                            : undefined
                    }
                    placeholderTextColor={color.inkFaint}
                    accessibilityLabel={
                      item.kind === 'h'
                        ? 'Heading'
                        : item.kind === 'quote'
                          ? 'Quote'
                          : 'Description'
                    }
                    testID={first ? 'story' : `block-${item.kind}`}
                    multiline
                    scrollEnabled={false}
                    textAlignVertical="top"
                  >
                    {/* The marks stay where they were typed, faint, and what
                        they mark is set as it will read. */}
                    {inline(item.text, true).map((run, i) => (
                      <Text
                        key={i}
                        style={[
                          run.mark && styles.mark,
                          run.bold && styles.bold,
                          run.italic && styles.italic,
                        ]}
                      >
                        {run.mark
                          ? run.text
                          : hashtagParts(run.text).map((part, j) =>
                              part.tag ? (
                                <Text key={j} style={styles.hashtag}>
                                  {part.text}
                                </Text>
                              ) : (
                                part.text
                              ),
                            )}
                      </Text>
                    ))}
                  </TextInput>
                );
              })
            )}
          </View>
          {/* Only near the limit: a count from the first letter reads as a nag. */}
          {summary.length > MAX_SUMMARY - 200 && (
            <Text style={styles.meta}>{`${summary.length} / ${MAX_SUMMARY}`}</Text>
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
export function Chip({
  label: text,
  on,
  testID,
  onPress,
}: {
  label: string;
  on: boolean;
  testID?: string;
  onPress: () => void;
}) {
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
      testID={testID}
    >
      {({ pressed }) => (
        <Animated.View
          style={[
            styles.chip,
            on && styles.chipOn,
            pressed && sunk(styles.chip),
            { transform: [{ scale: pop }] },
          ]}
        >
          <Text style={[styles.chipText, on && styles.chipTextOn]}>{text}</Text>
        </Animated.View>
      )}
    </Pressable>
  );
}

/** A text action, as a note's Rewrite and Remove are on the open sheet. */
function Action({
  label: text,
  spoken,
  testID,
  style,
  onPress,
}: {
  label: string;
  spoken?: string;
  testID?: string;
  style?: TextStyle;
  onPress: () => void;
}) {
  return (
    <Pressable
      onPress={() => {
        Haptics.selectionAsync().catch(() => {});
        onPress();
      }}
      accessibilityRole="button"
      accessibilityLabel={spoken}
      testID={testID}
      hitSlop={12}
      style={dim()}
    >
      <Text style={[styles.action, style]}>{text}</Text>
    </Pressable>
  );
}

function isText(item: Item | undefined): item is TextItem {
  return item?.kind === 'p' || item?.kind === 'h' || item?.kind === 'quote';
}

const WIDTH = { s: '33.3%', m: '50%', l: '100%' } as const;

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
  // Ends at the toolbar, so nothing scrolls in under it.
  scroll: { flex: 1 },
  blocks: { gap: 16, marginTop: 24 },
  p: story.body,
  h: { ...story.body, ...font.display },
  quote: { ...story.body, paddingLeft: 12, borderLeftWidth: 3, borderLeftColor: color.rule },
  alone: { minHeight: 130 },
  mark: { color: color.inkFaint },
  bold: { ...font.display },
  italic: { fontStyle: 'italic' },
  hashtag: { ...font.displaySemi },
  divider: { paddingVertical: 4, borderRadius: radius.field },
  dividerOn: { backgroundColor: color.rule },
  caption: { ...story.meta, color: color.inkSoft, marginTop: 6 },
  left: { alignSelf: 'flex-start' },
  center: { alignSelf: 'center' },
  right: { alignSelf: 'flex-end' },
  photoOn: { borderWidth: 2, borderColor: color.gold },
  toolbar: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    alignItems: 'center',
    gap: 18,
    paddingHorizontal: 24,
    paddingVertical: 10,
    borderBottomWidth: 1,
    borderBottomColor: color.rule,
    backgroundColor: color.paper,
  },
  byline: { flexDirection: 'row', alignItems: 'center', gap: 8, marginTop: 8 },
  lockets: { gap: 8, paddingVertical: 12 },
  // A circle, the selection a ring in gold: the pin is what is being chosen.
  locket: {
    width: 64,
    height: 64,
    borderRadius: 32,
    borderWidth: 2,
    borderColor: 'transparent',
    alignItems: 'center',
    justifyContent: 'center',
  },
  locketOn: { borderColor: color.gold },
  locketImage: { width: 48, height: 48 },
  locketLevel: { ...label, fontSize: 10, position: 'absolute', bottom: 0 },
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
  chipOn: {
    backgroundColor: color.gold,
    borderColor: color.gold,
    borderBottomColor: color.goldDeep,
  },
  chipText: { ...label, fontSize: 12, color: color.inkSoft },
  chipTextOn: { color: color.paper },

  // MemoryMedia's photo, so a photo here is the size it will be read at.
  photo: {
    width: '100%',
    aspectRatio: 4 / 3,
    borderRadius: radius.field,
    backgroundColor: color.rule,
  },
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

  dot: { width: 10, height: 10, borderRadius: 5, backgroundColor: color.gold },
  error: { ...story.meta, color: color.gold },
  delete: { marginTop: 40, alignSelf: 'flex-start' },
});
