/** The notes under an open memory: F33. Only rendered once a memory is open -
 *  the server refuses the list to anyone who has not unlocked it, and a note
 *  needs the same. One each, no replies. See
 *  docs/10-decisions.md#notes-are-gated-like-a-purchase. */

import { useEffect, useState } from 'react';
import { Pressable, StyleSheet, Text, TextInput, View } from 'react-native';

import { fetchNotes, hideNote, leaveNote, wasRefused, type Note } from './api.ts';
import { deviceId } from './device.ts';
import { color, dim, input, label, story } from './theme.ts';

export const NOTE_MAX = 280;

type Props = {
  memoryId: number;
  /** This account filed the memory, so it may take down anyone's note. */
  isAuthor: boolean;
};

export default function Notes({ memoryId, isAuthor }: Props) {
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

  if (notes === null) return null;
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

  return (
    <View style={styles.notes}>
      {notes.length > 0 && <Text style={styles.heading}>Notes</Text>}
      {notes.map((note) => (
        <View key={note.id} style={styles.note}>
          <Text style={styles.body}>{note.body}</Text>
          {/* Who, then what you may do, on one grey line: a comment's footer
              everywhere (docs/10, "The open story is one type scale"). */}
          <View style={styles.row}>
            <Text style={styles.author}>{note.mine ? 'You' : note.author}</Text>
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
        </View>
      ))}

      {writing && (
        <>
          <TextInput
            style={[styles.input, styles.prose]}
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
          <View style={styles.row}>
            <Text style={styles.counter}>{NOTE_MAX - draft.length} left</Text>
            <Pressable
              accessibilityRole="button"
              style={dim(!draft.trim() && styles.off)}
              hitSlop={12}
              disabled={busy || !draft.trim()}
              onPress={send}
            >
              <Text style={styles.sendText}>
                {mine ? 'Save note' : 'Leave note'}
              </Text>
            </Pressable>
          </View>
        </>
      )}
      {failed && (
        <Text style={styles.counter}>
          {failed === 'refused' ? "That note can't be posted here." : "That didn't send. Try again."}
        </Text>
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  notes: { gap: 16 },
  heading: { ...label },
  note: { gap: 8 },
  body: story.body,
  row: { flexDirection: 'row', alignItems: 'center', gap: 16 },
  author: { ...label },
  action: { ...label, color: color.inkSoft },
  // The same text action as Rewrite, in ember: the one thing to do here.
  sendText: { ...label, color: color.ember },
  off: { opacity: 0.35 },
  input: { ...input, ...story.body },
  prose: { minHeight: 90 },
  counter: { ...label, flex: 1 },
});
