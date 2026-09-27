/** The notes under an open memory: F33. Only rendered once a memory is open -
 *  the server refuses the list to anyone who has not unlocked it, and a note
 *  needs the same. One each, no replies. See
 *  docs/10-decisions.md#notes-are-gated-like-a-purchase. */

import { useEffect, useState } from 'react';
import { Pressable, StyleSheet, Text, TextInput, View } from 'react-native';

import { fetchNotes, hideNote, leaveNote, type Note } from './api.ts';
import { deviceId } from './device.ts';
import { color, dim, font, input, label } from './theme.ts';

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
  const [failed, setFailed] = useState(false);

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
    } catch {
      setFailed(true);
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
      {notes.length > 0 && <Text style={styles.heading}>Notes from people who stood here</Text>}
      {notes.map((note) => (
        <View key={note.id} style={styles.note}>
          <Text style={styles.body}>{note.body}</Text>
          <View style={styles.row}>
            <Text style={styles.author}>{note.mine ? 'You' : note.author}</Text>
            {note.mine && !editing && (
              <Pressable
                accessibilityRole="button"
                style={dim(styles.link)}
                onPress={() => {
                  setDraft(note.body);
                  setEditing(true);
                }}
              >
                <Text style={styles.linkText}>Rewrite</Text>
              </Pressable>
            )}
            {(note.mine || isAuthor) && (
              <Pressable
                accessibilityRole="button"
                accessibilityLabel={note.mine ? 'Remove your note' : 'Remove this note'}
                style={dim(styles.link)}
                onPress={() => remove(note)}
              >
                <Text style={styles.linkText}>Remove</Text>
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
              style={dim(styles.link)}
              disabled={busy || !draft.trim()}
              onPress={send}
            >
              <Text style={[styles.linkText, styles.send, !draft.trim() && styles.off]}>
                {mine ? 'Save note' : 'Leave note'}
              </Text>
            </Pressable>
          </View>
        </>
      )}
      {failed && <Text style={styles.counter}>That didn't send. Try again.</Text>}
    </View>
  );
}

const styles = StyleSheet.create({
  notes: { marginTop: 32, gap: 14 },
  heading: { ...label },
  note: { gap: 6, paddingTop: 12, borderTopWidth: 1, borderTopColor: color.rule },
  body: { ...font.prose, fontSize: 16, lineHeight: 25, color: color.ink },
  row: { flexDirection: 'row', alignItems: 'center', gap: 16 },
  author: { ...label, fontSize: 12, flex: 1 },
  link: { paddingVertical: 6 },
  linkText: { ...label, fontSize: 12, color: color.inkFaint },
  send: { color: color.ink },
  off: { opacity: 0.3 },
  input: { ...input },
  prose: { minHeight: 90, lineHeight: 24 },
  counter: { ...label, fontSize: 12, flex: 1 },
});
