/** What somebody attached to a memory they filed.
 *
 * Only ever rendered for an open memory. A photograph of the place is the
 * memory as much as the text is, so it stays behind the gate with the summary -
 * the sheet decides that, and this component never sees a locked one.
 *
 * The audio control is deliberately not a scrubber. It is a forty-second
 * recording made on a phone in the street, listened to on a phone in the
 * street; a progress bar and a seek handle would be more interface than
 * content.
 */

import { useState } from 'react';
import { Image, Pressable, StyleSheet, Text, View } from 'react-native';
import { useAudioPlayer, useAudioPlayerStatus } from 'expo-audio';

import { AUDIO, mediaUrl, type MediaItem } from './api.ts';
import { duration } from './format.ts';
import { color, dim, label, radius } from './theme.ts';

function Recording({ item }: { item: MediaItem }) {
  const player = useAudioPlayer(mediaUrl(item));
  const status = useAudioPlayerStatus(player);
  // Falls back to what the phone measured at recording time: duration is not
  // known until the remote file has loaded, and "0:00" under a play button
  // reads as a broken clip.
  const length = status.duration || item.duration_seconds || 0;

  return (
    <Pressable
      style={dim(styles.audio)}
      accessibilityRole="button"
      accessibilityLabel={status.playing ? 'Pause the recording' : 'Play the recording'}
      onPress={() => {
        if (status.playing) {
          player.pause();
          return;
        }
        // Replaying from the end has to start over, or the second press looks
        // like nothing happened.
        if (status.didJustFinish || status.currentTime >= length) player.seekTo(0);
        player.play();
      }}
    >
      <View style={styles.glyph}>
        {status.playing ? (
          <View style={styles.pause}>
            <View style={styles.bar} />
            <View style={styles.bar} />
          </View>
        ) : (
          <View style={styles.play} />
        )}
      </View>
      <View style={styles.audioText}>
        <Text style={styles.audioLabel}>In their voice</Text>
        <Text style={styles.audioTime}>
          {status.playing ? `${duration(status.currentTime)} / ${duration(length)}` : duration(length)}
        </Text>
      </View>
    </Pressable>
  );
}

export default function MemoryMedia({ media }: { media: MediaItem[] }) {
  // Above the early return, and it has to stay there. React counts hooks per
  // render, so a `useState` reached only when there is media makes this
  // component call one hook on some renders and none on others - and the
  // second one throws "rendered more hooks than during the previous render"
  // and takes the sheet down with it.
  //
  // It is reachable, not theoretical. The sheet pages through every memory at
  // one point without remounting, two submissions filed ten metres apart
  // group onto one pin, and only one of them need carry a photograph: page
  // from it to the other and the count changes underneath the same instance.
  const [failed, setFailed] = useState<MediaItem['id'][]>([]);

  if (media.length === 0) return null;

  const photos = media.filter((item) => item.kind === 'photo');
  const sounds = AUDIO ? media.filter((item) => item.kind === 'audio') : [];

  return (
    <View style={styles.wrap}>
      {photos.map((photo) =>
        // Fixed aspect rather than a measured one: react-native cannot know a
        // remote image's size before it loads, and a block that resizes under
        // the reader is worse than one that crops.
        failed.includes(photo.id) ? (
          // Without this a dead URL is an empty rule-coloured rectangle for
          // ever, which reads as a load that never finishes rather than as a
          // photograph that is gone.
          <View key={photo.id} style={[styles.photo, styles.photoGone]}>
            <Text style={styles.goneText}>Photo didn't load</Text>
          </View>
        ) : (
          <Image
            key={photo.id}
            testID="photo"
            source={{ uri: mediaUrl(photo) }}
            style={styles.photo}
            onError={() => setFailed((current) => [...current, photo.id])}
          />
        ),
      )}
      {sounds.map((sound) => (
        <Recording key={sound.id} item={sound} />
      ))}
    </View>
  );
}

const styles = StyleSheet.create({
  wrap: { gap: 8 },
  photo: { width: '100%', aspectRatio: 4 / 3, borderRadius: radius.field, backgroundColor: color.rule },
  photoGone: { alignItems: 'center', justifyContent: 'center' },
  goneText: { ...label, color: color.inkSoft },
  audio: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 14,
    borderWidth: 1,
    borderColor: color.rule,
    borderRadius: radius.field,
    padding: 14,
    backgroundColor: color.paperRaised,
  },
  glyph: {
    width: 44,
    height: 44,
    borderRadius: 22,
    borderWidth: 1.5,
    borderColor: color.ember,
    alignItems: 'center',
    justifyContent: 'center',
  },
  // A triangle out of borders, so there is no icon font and no svg for one shape.
  play: {
    width: 0,
    height: 0,
    marginLeft: 4,
    borderTopWidth: 8,
    borderBottomWidth: 8,
    borderLeftWidth: 13,
    borderTopColor: 'transparent',
    borderBottomColor: 'transparent',
    borderLeftColor: color.ember,
  },
  pause: { flexDirection: 'row', gap: 4 },
  bar: { width: 4, height: 16, backgroundColor: color.ember },
  audioText: { gap: 2 },
  audioLabel: { ...label },
  audioTime: { ...label, color: color.ink },
});
