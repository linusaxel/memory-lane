/** The only screen in the app that writes, or edits, or deletes - spec in
 *  "Writing", UI.md. Doubles as the editor for a memory you already filed:
 *  `editing` prefills every field from it and Next becomes Save. */

import { useEffect, useRef, useState, type ComponentProps } from 'react';
import {
  ActivityIndicator,
  Animated,
  Dimensions,
  Easing,
  Image,
  Keyboard,
  Modal,
  Platform,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  View,
  type TextStyle,
  type ViewStyle,
} from 'react-native';
import DateTimePicker, { DateTimePickerAndroid } from '@react-native-community/datetimepicker';
import * as Haptics from 'expo-haptics';
import * as ImagePicker from 'expo-image-picker';
import * as Location from 'expo-location';
import { CameraView, useCameraPermissions } from 'expo-camera';
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
import Button from './Button.tsx';
import CloseButton from './CloseButton.tsx';
import DiamondRule from './DiamondRule.tsx';
import Glyph from './Glyph.tsx';
import { duration, happened } from './format.ts';
import { hashtagParts } from './hashtags.ts';
import { LOCKET_DEFAULT, LOCKETS, locketOf, type LocketId } from './lockets.ts';
import { useDevScreen } from './devOpen.ts';
import { metersBetween } from './region.ts';
import { blocks, inline, plain, serialize, type Block, type Place, type Size } from './story.ts';
import Svg, { Circle, Defs, RadialGradient, Stop } from 'react-native-svg';
import { color, dim, font, label, lift, metal, radius, screenTitle, story, sunk } from './theme.ts';

const MAX_SUMMARY = 2000;
const MAX_PHOTOS = 4;
/** Long enough for a story, short enough that nobody uploads a podcast. */
const MAX_RECORDING_SECONDS = 180;
/** Where the bar sits with the keyboard down, over the home indicator. */
const DOCK = 34;
/** The bar's height and a little air: the page ends above it. */
const BAR = 72;
/** The chosen locket on the seal, and the glow it sits in. */
const SEAL = 168;
const SEAL_GLOW = 300;

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
  /** How near a reader has to stand, for the seal's last line. */
  radiusMeters: number;
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
 *  attachment's uri until the seal, because the id arrives with the upload. */
type Item = { key: string } & (
  | { kind: 'p' | 'h' | 'quote'; text: string }
  | { kind: 'divider' }
  | { kind: 'photo'; uri: string; size: Size; place: Place; caption: string }
  // The viewfinder, where its photo will go (docs/10, "The camera is a block").
  | { kind: 'camera' }
);
type TextItem = Extract<Item, { kind: 'p' | 'h' | 'quote' }>;

let keys = 0;
const key = () => String(++keys);
/** What `submit-filled` and after write, every kind of block once. */
const DEV_STORY = `We sat here the summer the lakes froze late, and **nobody** believed us.

## The night of the skates

> You could hear the ice sing all the way to Fredens Bro.

---

Our grandmother told it every *winter* after.`;

const empty = (): Item => ({ key: key(), kind: 'p', text: '' });

/** The written blocks as items, a photo's id swapped for its attachment uri. */
/** A draft swiped away, for the next open at the same spot. A page sheet
 *  cannot refuse a swipe (RN's Modal has no isModalInPresentation), so this
 *  keeps the words instead of asking. Only while the app lives. */
type Kept = {
  at: Coordinates;
  placeName: string;
  locket: LocketId;
  items: Item[];
  day: Date;
  attachments: Attachment[];
};
let kept: Kept | null = null;

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
  radiusMeters,
}: Props) {
  const isEditing = !!editing;
  // The title is the place row's name - docs/10, "The title is the place name".
  const [placeName, setPlaceName] = useState('');
  const [locket, setLocket] = useState<LocketId>(LOCKET_DEFAULT);
  const [items, setItems] = useState<Item[]>(() => [empty()]);
  // The block the bar acts on: the text being typed in, or a tapped photo.
  const [current, setCurrent] = useState<string | null>(null);
  const [selection, setSelection] = useState({ start: 0, end: 0 });
  // Set for one render after B or I, to put the caret between the marks.
  const [caret, setCaret] = useState<{ key: string; at: number } | null>(null);
  // Aa: the bar shows the marks instead of Photo and Camera.
  const [styling, setStyling] = useState(false);
  // Next opens the seal: the locket is chosen once the story is written.
  const [sealing, setSealing] = useState(false);
  const [discarding, setDiscarding] = useState(false);
  // The street it is filed on, for the byline; "here" until it is known.
  const [here, setHere] = useState<string | null>(null);
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
  // Set by a discard or a post: the close that follows keeps nothing.
  const done = useRef(false);

  // scripts/shoot.sh, under __DEV__ only: each step of the sheet without typing.
  useDevScreen(({ screen }) => {
    if (!screen.startsWith('submit')) {
      done.current = true;
      return;
    }
    const filled = screen !== 'submit' && screen !== 'submit-editor' && screen !== 'submit-delete';
    if (filled) {
      setPlaceName('The bench by the lakes');
      setItems(toItems(blocks(DEV_STORY), () => undefined));
    }
    setStyling(screen === 'submit-styling');
    setPickingDay(screen === 'submit-date');
    setDiscarding(screen === 'submit-discard');
    setSealing(screen === 'submit-seal');
    setConfirmingDelete(screen === 'submit-delete');
    setError(screen === 'submit-error' ? "That didn't post. Try again in a moment." : null);
  });

  const camera = useRef<CameraView>(null);
  const [, requestCamera] = useCameraPermissions();
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

  // The bar rides the keyboard. A page sheet ends at the screen's foot, so
  // what the keyboard covers is the screen below its top edge; the sheet's own
  // frame reads as starting at 0 (why KeyboardAvoidingView missed).
  const lifted = useRef(new Animated.Value(DOCK)).current;
  const [typing, setTyping] = useState(false);
  useEffect(() => {
    const to = (bottom: number, ms: number) =>
      Animated.timing(lifted, {
        toValue: bottom,
        duration: ms,
        easing: Easing.bezier(0.2, 0.8, 0.2, 1),
        useNativeDriver: false,
      }).start();
    const show = Keyboard.addListener('keyboardWillChangeFrame', (e) => {
      const over = Dimensions.get('window').height - e.endCoordinates.screenY;
      setTyping(over > 0);
      to(over > 0 ? over + 8 : DOCK, e.duration);
    });
    const hide = Keyboard.addListener('keyboardWillHide', (e) => {
      setTyping(false);
      to(DOCK, e.duration);
    });
    return () => {
      show.remove();
      hide.remove();
    };
  }, [lifted]);

  // The seal comes up over the page.
  const rise = useRef(new Animated.Value(0)).current;
  useEffect(() => {
    if (!sealing) return;
    rise.setValue(0);
    Animated.timing(rise, {
      toValue: 1,
      duration: 260,
      easing: Easing.out(Easing.cubic),
      useNativeDriver: true,
    }).start();
  }, [sealing, rise]);

  // Everything resets on close. A draft swiped away is kept, but it comes back
  // only at the spot it was written: kept further, it would eventually be
  // posted somewhere it did not happen, because the coordinate is taken fresh
  // and the words would not be. A photo still uploading is not kept.
  useEffect(() => {
    if (visible) {
      done.current = false;
      if (isEditing || !kept || !position) return;
      const there =
        metersBetween(kept.at.lat, kept.at.lng, position.lat, position.lng) <= radiusMeters;
      if (there) {
        setPlaceName(kept.placeName);
        setLocket(kept.locket);
        setItems(kept.items);
        setDay(kept.day);
        setAttachments(kept.attachments);
      }
      kept = null;
      return;
    }
    if (dirty && !done.current && position) {
      const up = attachments.filter((a) => a.item);
      const left = items.filter(
        (i) => i.kind !== 'camera' && (i.kind !== 'photo' || up.some((a) => a.uri === i.uri)),
      );
      kept = {
        at: position,
        placeName,
        locket,
        items: left.length ? left : [empty()],
        day,
        attachments: up,
      };
    }
    setPlaceName('');
    setLocket(LOCKET_DEFAULT);
    setItems([empty()]);
    setCurrent(null);
    setStyling(false);
    setSealing(false);
    setDiscarding(false);
    setHere(null);
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

  // Display only: Apple's geocoder, on the phone. The title is still theirs.
  const lat = position?.lat;
  const lng = position?.lng;
  useEffect(() => {
    if (!visible || isEditing || lat == null || lng == null) return;
    Location.reverseGeocodeAsync({ latitude: lat, longitude: lng })
      .then(([found]) => mounted.current && setHere(found?.street ?? found?.name ?? null))
      .catch(() => {});
  }, [visible, isEditing, lat, lng]);

  const photos = attachments.filter((a) => a.kind === 'photo');
  const sound = attachments.find((a) => a.kind === 'audio');
  const uploading = attachments.some((a) => !a.item && !a.failed);
  const framing = items.some((i) => i.kind === 'camera');
  const summary = serialize(
    items.flatMap((i): Block[] => {
      if (i.kind === 'camera') return [];
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
    !framing &&
    !posting;
  const when = happened(isoDay(day), 'day');
  const today = isoDay(day) === isoDay(new Date());
  const dirty = !isEditing && (named || told || attachments.length > 0);
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

  const addPhoto = async () => {
    setError(null);
    const permission = await ImagePicker.requestMediaLibraryPermissionsAsync();
    if (!permission.granted) {
      setError('Allow photo access in Settings to add one.');
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
    const result = await ImagePicker.launchImageLibraryAsync(options);
    const picked = result.canceled ? null : result.assets[0];
    if (!picked) return;

    // Where the writer is, at the size it will be read at until they say.
    insert({ key: key(), kind: 'photo', uri: picked.uri, size: 'l', place: 'center', caption: '' });
    // The picker keeps a PNG a PNG, so the type is what it says it wrote.
    await attach({ uri: picked.uri, kind: 'photo' }, picked.mimeType ?? 'image/jpeg');
  };

  const openCamera = async () => {
    setError(null);
    const permission = await requestCamera();
    if (!permission.granted) {
      setError('Allow camera access in Settings to take a photo.');
      return;
    }
    insert({ key: key(), kind: 'camera' });
  };

  /** The viewfinder becomes its photo, in the same place under the same key. */
  const takePhoto = async (k: string) => {
    // Re-encoded for the same reason as the library's: a thumbnail, not a print.
    const shot = await camera.current?.takePictureAsync({ quality: 0.7 }).catch(() => null);
    if (!shot) return setError("That didn't take. Try again.");
    Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Light).catch(() => {});
    setItems((list) =>
      list.map((i): Item =>
        i.key === k
          ? { key: k, kind: 'photo', uri: shot.uri, size: 'l', place: 'center', caption: '' }
          : i,
      ),
    );
    await attach({ uri: shot.uri, kind: 'photo' }, 'image/jpeg');
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

  // One bar for every field, over the keyboard (docs/10, "Writing is a calm
  // page"): Aa for the marks, Photo, Camera. Docked at the foot while the
  // keyboard is down.
  const tools = () => (
    <View style={styles.capsule}>
      {styling ? (
        <>
          <Tool icon="bold" spoken="Bold" testID="toolbar-bold" onPress={() => mark('**')} />
          <Tool icon="italic" spoken="Italic" testID="toolbar-italic" onPress={() => mark('*')} />
          <Tool
            icon="h.square"
            spoken="Heading"
            testID="toolbar-heading"
            onPress={() => turn('h')}
          />
          <Tool
            icon="text.quote"
            spoken="Quote"
            testID="toolbar-quote"
            onPress={() => turn('quote')}
          />
          <Tool icon="minus" spoken="Divider" testID="toolbar-divider" onPress={divider} />
          <Tool icon="xmark" spoken="Done styling" onPress={() => setStyling(false)} />
        </>
      ) : (
        <>
          <Tool
            icon="textformat"
            spoken="Style"
            testID="toolbar-style"
            onPress={() => setStyling(true)}
          />
          {photos.length < MAX_PHOTOS && !framing && (
            <>
              <Tool icon="photo" spoken="Choose photo" testID="toolbar-photo" onPress={addPhoto} />
              <Tool
                icon="camera"
                spoken="Take photo"
                testID="toolbar-camera"
                onPress={openCamera}
              />
            </>
          )}
          {typing && (
            <Tool
              icon="keyboard.chevron.compact.down"
              spoken="Hide keyboard"
              onPress={Keyboard.dismiss}
            />
          )}
        </>
      )}
    </View>
  );

  /** ↑ and ↓ for a tapped photo or divider: text moves by cut and paste. */
  const moves = (
    <>
      <Action label="↑" spoken="Move up" testID="block-up" onPress={() => move(-1)} />
      <Action label="↓" spoken="Move down" testID="block-down" onPress={() => move(1)} />
    </>
  );

  const close = () => {
    if (discarding) done.current = true;
    if (!dirty || discarding) return onClose();
    setDiscarding(true);
    confirmTimer.current = setTimeout(() => setDiscarding(false), 3000);
  };

  const step = (n: 0 | 1) => (
    <View style={styles.steps} accessible accessibilityLabel={`Step ${n + 1} of 2`}>
      {[0, 1].map((i) => (
        <View key={i} style={[styles.step, i === n && styles.stepOn]} />
      ))}
    </View>
  );
  const top = (n: 0 | 1) => (
    <View style={styles.bar}>
      {discarding ? (
        <Pressable onPress={close} hitSlop={12} accessibilityRole="button">
          <Text style={styles.error}>Tap again to discard</Text>
        </Pressable>
      ) : (
        <CloseButton onPress={close} label="Cancel" />
      )}
      <Text style={styles.barTitle} accessibilityRole="header">
        {isEditing ? 'Edit your memory' : 'Leave a memory here'}
      </Text>
      {step(n)}
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
      done.current = true;
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
      <View style={styles.sheet}>
        {/* The open sheet with nothing in it yet: the same title, byline and
            story type, in the same places, so what you write is what people
            standing here will read (docs/10, "Reading and writing are one
            page"). Cancel above and Next below are the only chrome. */}
        {top(0)}

        <Animated.ScrollView
          ref={scroll}
          style={[styles.scroll, { marginBottom: Animated.add(lifted, BAR) }]}
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
            placeholder="Give it a name"
            placeholderTextColor={color.inkFaint}
            accessibilityLabel="Title"
            testID="title"
            maxLength={200}
            multiline
            submitBehavior="blurAndSubmit"
            returnKeyType="next"
          />

          <View style={styles.byline}>
            <View style={[styles.tag, styles.tagAuthor]}>
              <Avatar url={author.avatar_url ?? null} name={author.name} size={28} />
              <Text style={styles.tagText}>{author.name}</Text>
            </View>
            <Pressable
              style={dim(styles.tag)}
              onPress={pickDay}
              accessibilityRole="button"
              accessibilityLabel={`When, ${today ? 'today' : `${when?.within} ${when?.year}`}`}
            >
              <Text style={styles.tagText}>{today ? 'When' : `${when?.within} ${when?.year}`}</Text>
              <Glyph name="chevron.down" size={12} weight="semibold" color={color.ink} />
            </Pressable>
            {!isEditing && (
              <View style={styles.tag}>
                <Glyph name="mappin" size={14} weight="medium" color={color.gold} />
                <Text style={[styles.tagText, styles.tagPlace]} numberOfLines={1}>
                  {here ?? 'Here'}
                </Text>
              </View>
            )}
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

          <DiamondRule place={styles.rule} />

          {/* The story, a block at a time: what is typed here is what
              StoryBody sets on the open sheet. */}
          <View style={styles.blocks}>
            {items.map((item, n) => {
              const on = item.key === current;
              if (item.kind === 'divider') {
                return (
                  <View key={item.key}>
                    <Pressable
                      onPress={() => setCurrent(item.key)}
                      accessibilityRole="button"
                      accessibilityLabel="Divider"
                      testID="divider"
                      style={[styles.divider, on && styles.dividerOn]}
                    >
                      <DiamondRule />
                    </Pressable>
                    {on && (
                      <View style={styles.row}>
                        {moves}
                        <Action label="Remove divider" onPress={() => remove(item)} />
                      </View>
                    )}
                  </View>
                );
              }
              if (item.kind === 'camera') {
                return (
                  <View key={item.key} style={styles.part}>
                    <CameraView
                      ref={camera}
                      style={styles.photo}
                      onMountError={() => {
                        remove(item);
                        setError('No camera on this phone.');
                      }}
                    />
                    <View style={styles.row}>
                      <Action
                        label="Take"
                        spoken="Take photo"
                        testID="camera-take"
                        onPress={() => takePhoto(item.key)}
                      />
                      <Action
                        label="Cancel"
                        spoken="Put the camera away"
                        onPress={() => remove(item)}
                      />
                    </View>
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
                        {moves}
                        <Action label="Remove photo" onPress={() => remove(item)} />
                      </View>
                    )}
                  </View>
                );
              }
              const first = items.findIndex(isText) === n;
              const field = (
                <TextInput
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
                      ? 'What happened here? Add a #tag if you like.'
                      : item.kind === 'h'
                        ? 'Heading'
                        : item.kind === 'quote'
                          ? 'What somebody said'
                          : undefined
                  }
                  placeholderTextColor={color.inkFaint}
                  accessibilityLabel={
                    item.kind === 'h' ? 'Heading' : item.kind === 'quote' ? 'Quote' : 'Description'
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
              // A `>` block reads as PullQuote sets it on the open sheet. One
              // wrapper for every kind, so turning a block keeps its focus.
              return (
                <View key={item.key} style={item.kind === 'quote' && styles.quoteBox}>
                  {item.kind === 'quote' && (
                    <Text style={styles.quoteMark} accessibilityElementsHidden>
                      “
                    </Text>
                  )}
                  {field}
                </View>
              );
            })}
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
        </Animated.ScrollView>
        <Animated.View style={[styles.dock, { bottom: lifted }]}>
          {tools()}
          {/* With Aa open, Next is the chevron alone: six marks need the room. */}
          <Button
            kind="go"
            label={styling ? '' : isEditing ? 'Save' : 'Next'}
            accessibilityLabel={isEditing ? 'Save' : 'Next'}
            trailing="chevron.right"
            place={[styles.next, styling && styles.nextSmall, !ready && styles.disabled]}
            onPress={() => {
              Keyboard.dismiss();
              setSealing(true);
            }}
            disabled={!ready}
          />
        </Animated.View>

        {/* The seal: the locket its pin is drawn as, chosen once the story is
            there (docs/10, "Writing is a calm page"). */}
        {sealing && (
          <Animated.View
            style={[
              styles.seal,
              {
                opacity: rise,
                transform: [
                  { translateY: rise.interpolate({ inputRange: [0, 1], outputRange: [40, 0] }) },
                ],
              },
            ]}
          >
            {top(1)}
            <ScrollView contentContainerStyle={styles.sealBody}>
              <Text style={styles.sealTitle} accessibilityRole="header">
                Seal it with
              </Text>
              <View style={styles.chosen}>
                <Svg width={SEAL_GLOW} height={SEAL_GLOW} style={styles.sealGlow}>
                  <Defs>
                    <RadialGradient id="seal">
                      <Stop offset="0" stopColor={metal.mid} stopOpacity={0.35} />
                      <Stop offset="1" stopColor={metal.mid} stopOpacity={0} />
                    </RadialGradient>
                  </Defs>
                  <Circle
                    cx={SEAL_GLOW / 2}
                    cy={SEAL_GLOW / 2}
                    r={SEAL_GLOW / 2}
                    fill="url(#seal)"
                  />
                </Svg>
                {SPARKLES.map((at, i) => (
                  <View key={i} style={[styles.sparkle, at]}>
                    <Glyph name="sparkle" size={at.size} color={color.gold} />
                  </View>
                ))}
                <Image source={locketOf(locket).pin} style={styles.chosenImage} />
              </View>
              <Text style={styles.sealName} numberOfLines={2}>
                {placeName.trim()}
              </Text>
              <Text style={styles.sealMeta}>
                {isEditing
                  ? `left by ${author.name}`
                  : `${here ?? 'Here'} · left by ${author.name}`}
              </Text>
              <Text style={styles.sealLabel}>Your lockets</Text>
              <View style={styles.lockets}>
                {LOCKETS.map((l) => {
                  const on = locket === l.id;
                  return (
                    <Pressable
                      key={l.id}
                      onPress={() => {
                        Haptics.selectionAsync().catch(() => {});
                        setLocket(l.id);
                      }}
                      accessibilityRole="radio"
                      accessibilityLabel={l.name}
                      accessibilityState={{ selected: on }}
                      testID={`locket-${l.id}`}
                      style={[styles.locket, on && styles.locketOn]}
                    >
                      <Image source={l.pin} style={styles.locketImage} />
                      <View style={[styles.locketDot, on && styles.locketDotOn]} />
                    </Pressable>
                  );
                })}
              </View>
              <Text style={styles.sealNote}>
                {`It opens for anyone who walks within ${Math.round(radiusMeters)} m of this spot.`}
              </Text>
              {error && <Text style={styles.error}>{error}</Text>}
            </ScrollView>
            <View style={styles.sealFoot}>
              <Button
                kind="text"
                label="Back"
                glyph="chevron.left"
                onPress={() => setSealing(false)}
                disabled={posting}
              />
              <Button
                kind="foil"
                label={
                  posting
                    ? isEditing
                      ? 'Saving…'
                      : 'Sealing…'
                    : isEditing
                      ? 'Save'
                      : 'Seal it here'
                }
                place={[styles.sealButton, posting && styles.disabled]}
                onPress={post}
                disabled={posting}
                testID="seal"
              />
            </View>
          </Animated.View>
        )}
      </View>
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
  style,
  onPress,
}: {
  label: string;
  on: boolean;
  testID?: string;
  style?: ViewStyle;
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
      style={style}
    >
      {({ pressed }) => (
        <Animated.View
          style={[
            styles.chip,
            on && styles.chipOn,
            pressed && sunk,
            { transform: [{ scale: pop }] },
          ]}
        >
          {/* Selected by more than its colour. */}
          {on && <Glyph name="checkmark" size={11} weight="bold" color={color.paper} />}
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

/** A glyph in the bar over the keyboard, 44pt to the finger. */
function Tool({
  icon,
  spoken,
  testID,
  onPress,
}: {
  icon: ComponentProps<typeof Glyph>['name'];
  spoken: string;
  testID?: string;
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
      style={dim(styles.tool)}
    >
      <Glyph name={icon} size={19} weight="medium" color={color.inkSoft} />
    </Pressable>
  );
}

function isText(item: Item | undefined): item is TextItem {
  return item?.kind === 'p' || item?.kind === 'h' || item?.kind === 'quote';
}

const WIDTH = { s: '33.3%', m: '50%', l: '100%' } as const;

/** Where the seal's four sparkles sit round the chosen locket. */
const SPARKLES = [
  { top: 40, left: 46, size: 20 },
  { top: 24, right: 60, size: 14 },
  { bottom: 30, left: 60, size: 12 },
  { bottom: 30, right: 54, size: 18 },
];

const styles = StyleSheet.create({
  sheet: { flex: 1, backgroundColor: color.paper },
  bar: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    gap: 12,
    paddingHorizontal: 20,
    paddingTop: 18,
    paddingBottom: 8,
  },
  barTitle: { ...font.uiBold, fontSize: 17, color: color.ink, flexShrink: 1 },
  steps: { flexDirection: 'row', gap: 6, width: 40, justifyContent: 'flex-end' },
  step: { width: 6, height: 6, borderRadius: 3, backgroundColor: color.rule },
  stepOn: { width: 20, backgroundColor: color.gold },
  next: { paddingHorizontal: 28 },
  nextSmall: { width: 60, paddingHorizontal: 0 },
  disabled: { opacity: 0.35 },

  // MemorySheet's reading column: 24 in, 8 inside a part, 24 between parts.
  body: { paddingHorizontal: 24, paddingTop: 16, paddingBottom: 24 },
  // A field with no box: the cursor and the placeholder say it is editable.
  slot: { padding: 0, margin: 0 },
  title: story.title,
  scroll: { flex: 1 },
  blocks: { gap: 16, marginTop: 24 },
  p: story.body,
  h: { ...story.body, ...font.storyBold },
  quoteBox: { alignItems: 'center', gap: 8, paddingHorizontal: 8, marginVertical: 8 },
  quoteMark: { ...font.title, fontSize: 64, lineHeight: 64, height: 44, color: color.gold },
  quote: {
    ...font.storyItalic,
    fontSize: 21,
    lineHeight: 30,
    color: color.ink,
    textAlign: 'center',
    alignSelf: 'stretch',
  },
  rule: { marginTop: 24 },
  alone: { minHeight: 130 },
  mark: { color: color.inkFaint },
  bold: font.storyBold,
  italic: font.storyItalic,
  hashtag: font.storyBold,
  divider: { paddingVertical: 4, borderRadius: radius.field },
  dividerOn: { backgroundColor: color.rule },
  caption: { ...story.meta, color: color.inkSoft, marginTop: 6 },
  left: { alignSelf: 'flex-start' },
  center: { alignSelf: 'center' },
  right: { alignSelf: 'flex-end' },
  photoOn: { borderWidth: 2, borderColor: color.gold },
  // The bar: one quiet capsule beside Next, over the keyboard or at the foot.
  capsule: {
    flex: 1,
    flexDirection: 'row',
    alignItems: 'center',
    height: 60,
    paddingHorizontal: 6,
    borderRadius: radius.pill,
    borderWidth: 1,
    borderColor: color.goldLine,
    backgroundColor: color.paperRaised,
    ...lift,
  },
  tool: { flex: 1, height: 52, alignItems: 'center', justifyContent: 'center' },
  dock: { position: 'absolute', left: 16, right: 16, flexDirection: 'row', gap: 12 },
  byline: { flexDirection: 'row', flexWrap: 'wrap', alignItems: 'center', gap: 8, marginTop: 16 },
  // The byline as chips: who, when, where.
  tag: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
    height: 44,
    paddingHorizontal: 14,
    borderRadius: radius.pill,
    borderWidth: 1,
    borderColor: color.goldLine,
    backgroundColor: color.paperRaised,
    maxWidth: '100%',
  },
  tagAuthor: { paddingLeft: 7 },
  tagText: { ...font.uiBold, fontSize: 15, color: color.ink, flexShrink: 1 },
  tagPlace: { color: color.gold },

  // The seal: a page of its own over the story (docs/10, "Jewel Box").
  seal: {
    position: 'absolute',
    top: 0,
    left: 0,
    right: 0,
    bottom: 0,
    backgroundColor: color.paper,
  },
  sealBody: { alignItems: 'center', paddingHorizontal: 24, paddingTop: 16, paddingBottom: 24 },
  sealTitle: { ...screenTitle, textAlign: 'center' },
  chosen: {
    width: SEAL_GLOW,
    height: SEAL_GLOW - 60,
    alignItems: 'center',
    justifyContent: 'center',
  },
  sealGlow: { position: 'absolute', top: -30 },
  chosenImage: { width: SEAL, height: SEAL, resizeMode: 'contain' },
  sparkle: { position: 'absolute' },
  sealName: { ...font.title, fontSize: 30, lineHeight: 36, color: color.ink, textAlign: 'center' },
  sealMeta: { ...font.ui, fontSize: 15, color: color.inkSoft, marginTop: 4, textAlign: 'center' },
  sealLabel: { ...label, alignSelf: 'flex-start', marginTop: 32, marginBottom: 12 },
  lockets: { flexDirection: 'row', flexWrap: 'wrap', alignSelf: 'stretch', gap: 6 },
  // A tile each.
  locket: {
    width: 54,
    height: 80,
    borderRadius: 14,
    borderWidth: 1,
    borderColor: color.goldLine,
    alignItems: 'center',
    justifyContent: 'center',
    gap: 6,
  },
  locketOn: { borderWidth: 1.5, borderColor: color.gold, backgroundColor: color.quiet },
  locketImage: { width: 40, height: 40, resizeMode: 'contain' },
  locketDot: { width: 6, height: 6, borderRadius: 3 },
  locketDotOn: { backgroundColor: color.gold },
  sealNote: { ...font.ui, fontSize: 15, lineHeight: 21, color: color.inkSoft, marginTop: 16 },
  sealFoot: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 16,
    paddingHorizontal: 24,
    paddingTop: 8,
    paddingBottom: DOCK,
  },
  sealButton: { flex: 1 },
  meta: { ...story.meta, flexShrink: 1 },
  part: { gap: 8, marginTop: 24 },
  row: { flexDirection: 'row', flexWrap: 'wrap', alignItems: 'center', gap: 16, marginTop: 24 },
  action: { ...story.meta, color: color.inkSoft },

  chip: {
    borderRadius: radius.pill,
    paddingHorizontal: 14,
    // 40 tall with the label's line box, and the row gap keeps neighbours
    // from stealing the edges of the target.
    paddingVertical: 12,
    backgroundColor: color.quiet,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 5,
  },
  chipOn: { backgroundColor: color.gold },
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
