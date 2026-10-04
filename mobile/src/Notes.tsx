/** The notes under an open memory: F33. Only rendered once a memory is open -
 *  the server refuses the list to anyone who has not unlocked it, and a note
 *  needs the same. One each, no replies. See
 *  docs/10-decisions.md#notes-are-gated-like-a-purchase. */

import { useEffect, useState, type ReactNode } from 'react';
import { Pressable, StyleSheet, Text, TextInput, View } from 'react-native';

import { fetchNotes, hideNote, leaveNote, wasRefused, type Note } from './api.ts';
import { deviceId } from './device.ts';
import { when } from './format.ts';
import { color, dim, input, label, story } from './theme.ts';

export const NOTE_MAX = 280;

type Props = {
  memoryId: number;
  /** This account filed the memory, so it may take down anyone's note. */
  isAuthor: boolean;
  /** The memory's heart: the section's header row, with the count of notes
   *  beside it (docs/10, "The heart heads the notes"). */
  heart?: ReactNode;
};

export default function Notes({ memoryId, isAuthor, heart }: Props) {
  const [notes, setNotes] = useState<Note[] | null>(null);
  const [draft, setDraft] = useState('');
  const [editing, setEditing] = useState(false);
  const [busy, setBusy] = useState(false);
  const [failed, setFailed] = useState<boolean | 'refused'>(false);

  useEffect(() => {
    let live = true;
    setNotes(null);
    setEditing(false);
    deviceId()
      .then((device) => fetchNotes(memoryId, device))
      .then((got) => live && setNotes(got))
      // Silent, like F26's heart: the memory is still readable without them.
      .catch(() => live && setNotes([]));
    return () => {
      live = false;
    };
  }, [memoryId]);

  if (notes === null) return heart ? <View style={styles.row}>{heart}</View> : null;
  const mine = notes.find((n) => n.mine);
  const writing = !mine || editing;

  const send = async () => {
    setBusy(true);
    setFailed(false);
    try {
      setNotes(await leaveNote(memoryId, await deviceId(), draft.trim()));
      setEditing(false);
      setDraft('');
    } catch (e) {
      setFailed(wasRefused(e) ? 'refused' : true);
    } finally {
      setBusy(false);
    }
  };

  const remove = async (note: Note) => {
    try {
      await hideNote(memoryId, note.id, await deviceId());
      setNotes(notes.filter((n) => n.id !== note.id));
    } catch {
      setFailed(true);
    }
  };

  const composer = writing && (
    <View style={styles.note}>
      <TextInput
        style={styles.input}
        value={draft}
        onChangeText={setDraft}
        placeholder="You were here. Leave a note."
        placeholderTextColor={color.inkFaint}
        multiline
        maxLength={NOTE_MAX}
        textAlignVertical="top"
        // Return sends: a note has no paragraphs, and the send link below
        // is under the keyboard on a long memory.
        returnKeyType="send"
        submitBehavior="blurAndSubmit"
        onSubmitEditing={() => draft.trim() && !busy && send()}
        // Rewrite means "let me type": straight into the field, cursor at the end.
        autoFocus={editing}
        accessibilityLabel="Your note"
        // The placeholder goes once Rewrite fills the field, so the flows
        // find it by id.
        testID="note"
      />
      {/* One line at rest, growing as you type; the send link arrives with
          something to send (docs/10, "The notes are a thread"). */}
      {(draft.trim() !== '' || editing) && (
        <View style={styles.row}>
          {/* Only near the end: a number that counts down from the first key is noise. */}
          <Text style={styles.grow}>
            {draft.length > NOTE_MAX - 40 ? `${NOTE_MAX - draft.length} left` : ''}
          </Text>
          <Pressable
            accessibilityRole="button"
            style={dim(!draft.trim() && styles.off)}
            hitSlop={12}
            disabled={busy || !draft.trim()}
            onPress={send}
          >
            <Text style={styles.sendText}>{mine ? 'Save note' : 'Leave note'}</Text>
          </Pressable>
        </View>
      )}
    </View>
  );

  return (
    <View style={styles.notes}>
      {(heart || notes.length > 0) && (
        <View style={styles.row}>
          {heart}
          {notes.length > 0 && (
            <Text style={styles.heading}>
              {notes.length === 1 ? '1 note' : `${notes.length} notes`}
            </Text>
          )}
        </View>
      )}
      {composer}
      {notes.map((note) => (
        <View key={note.id} style={styles.note}>
          {/* Who and when above what they wrote, as a review or a reply
              does; your own controls at the far end of the same line. */}
          <View style={styles.row}>
            <Text style={styles.grow} numberOfLines={1}>
              {[note.mine ? 'You' : note.author, when(Date.parse(note.created_at))]
                .filter(Boolean)
                .join(' · ')}
            </Text>
            {note.mine && !editing && (
              <Pressable
                accessibilityRole="button"
                style={dim()}
                hitSlop={12}
                onPress={() => {
                  setDraft(note.body);
                  setEditing(true);
                }}
              >
                <Text style={styles.action}>Rewrite</Text>
              </Pressable>
            )}
            {(note.mine || isAuthor) && (
              <Pressable
                accessibilityRole="button"
                accessibilityLabel={note.mine ? 'Remove your note' : 'Remove this note'}
                style={dim()}
                hitSlop={12}
                onPress={() => remove(note)}
              >
                <Text style={styles.action}>Remove</Text>
              </Pressable>
            )}
          </View>
          <Text style={styles.body}>{note.body}</Text>
        </View>
      ))}
      {failed && (
        <Text style={styles.heading}>
          {failed === 'refused'
            ? "That note can't be posted here."
            : "That didn't send. Try again."}
        </Text>
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  notes: { gap: 20 },
  heading: { ...label },
  note: { gap: 8 },
  body: story.body,
  row: { flexDirection: 'row', alignItems: 'center', gap: 16 },
  grow: { ...label, flex: 1 },
  action: { ...label, color: color.inkSoft },
  // The same text action as Rewrite, in gold: the one thing to do here.
  sendText: { ...label, color: color.gold },
  off: { opacity: 0.35 },
  input: { ...input, ...story.body },
});
