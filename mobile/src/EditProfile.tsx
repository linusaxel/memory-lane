/** Edit profile: the photo and the name other people see on what you file.
 *  Opened from the journal's header. Both are public, like every memory
 *  (docs/10-decisions.md, "A profile photo is public, like the name"). */

import { useState } from 'react';
import { Modal, Pressable, ScrollView, StyleSheet, Text, TextInput, View } from 'react-native';
import * as ImagePicker from 'expo-image-picker';

import { removeAvatar, uploadAvatar, type Profile } from './api.ts';
import Avatar from './Avatar.tsx';
import Button from './Button.tsx';
import CloseButton from './CloseButton.tsx';
import DiamondRule from './DiamondRule.tsx';
import { color, dim, font, input, label, screenTitle } from './theme.ts';

type Props = {
  visible: boolean;
  onClose: () => void;
  device: string | null;
  profile: Profile | null;
  onProfile: (next: Profile) => void;
  /** Empty means Anonymous. Saved as it is typed, so there is no Save button
   *  to forget to press. */
  displayName: string;
  onDisplayName: (next: string) => void;
  /** Set when the last save did not land. The field keeps the typed value
   *  either way, so without this the name looks saved and is not. */
  nameError: string | null;
};

export default function EditProfile({
  visible,
  onClose,
  device,
  profile,
  onProfile,
  displayName,
  onDisplayName,
  nameError,
}: Props) {
  const [busy, setBusy] = useState(false);
  const [photoError, setPhotoError] = useState<string | null>(null);

  const choose = async (fromCamera: boolean) => {
    if (!device) return;
    setPhotoError(null);
    const permission = fromCamera
      ? await ImagePicker.requestCameraPermissionsAsync()
      : await ImagePicker.requestMediaLibraryPermissionsAsync();
    if (!permission.granted) {
      setPhotoError(
        fromCamera
          ? 'Allow camera access in Settings to take a photo.'
          : 'Allow photo access in Settings to choose one.',
      );
      return;
    }
    // As Submit's addPhoto: re-encoded, and a JPEG rather than a HEIC.
    const options: ImagePicker.ImagePickerOptions = {
      mediaTypes: ['images'],
      allowsEditing: true,
      aspect: [1, 1],
      quality: 0.7,
      preferredAssetRepresentationMode:
        ImagePicker.UIImagePickerPreferredAssetRepresentationMode.Compatible,
    };
    const result = fromCamera
      ? await ImagePicker.launchCameraAsync(options)
      : await ImagePicker.launchImageLibraryAsync(options);
    const picked = result.canceled ? null : result.assets[0];
    if (!picked) return;

    setBusy(true);
    try {
      onProfile(await uploadAvatar(device, picked.uri, picked.mimeType ?? 'image/jpeg'));
    } catch {
      setPhotoError("That didn't upload. Try again in a moment.");
    } finally {
      setBusy(false);
    }
  };

  const remove = async () => {
    if (!device) return;
    setPhotoError(null);
    setBusy(true);
    try {
      onProfile(await removeAvatar(device));
    } catch {
      setPhotoError("That didn't go through. Try again in a moment.");
    } finally {
      setBusy(false);
    }
  };

  return (
    <Modal
      visible={visible}
      animationType="slide"
      presentationStyle="pageSheet"
      onRequestClose={onClose}
    >
      <ScrollView
        style={styles.screen}
        contentContainerStyle={styles.body}
        keyboardShouldPersistTaps="handled"
      >
        <View style={styles.top}>
          <Text style={styles.title}>Profile</Text>
          <CloseButton onPress={onClose} label="Close profile" />
        </View>

        <View style={styles.photo}>
          <View style={styles.ring}>
            <Avatar url={profile?.avatar_url} name={displayName} size={112} />
          </View>
          <View style={styles.actions}>
            <Button
              kind="quiet"
              label="Choose photo"
              glyph="photo"
              onPress={() => choose(false)}
              disabled={busy}
            />
            <Button
              kind="quiet"
              label="Take photo"
              glyph="camera"
              onPress={() => choose(true)}
              disabled={busy}
            />
          </View>
          {profile?.avatar_url && (
            <Pressable
              style={dim(styles.link)}
              onPress={remove}
              disabled={busy}
              accessibilityRole="button"
            >
              <Text style={styles.linkText}>Remove photo</Text>
            </Pressable>
          )}
          {photoError && <Text style={styles.saveFailed}>{photoError}</Text>}
        </View>

        <DiamondRule place={styles.rule} />
        <View style={styles.section}>
          <Text style={styles.sectionTitle}>Your name</Text>
          <Text style={styles.note}>
            Shown with your photo on the memories you leave. Leave it blank to stay anonymous.
          </Text>
          <TextInput
            style={styles.input}
            value={displayName}
            onChangeText={onDisplayName}
            placeholder="Anonymous"
            placeholderTextColor={color.inkFaint}
            maxLength={60}
            autoCapitalize="words"
            accessibilityLabel="The name your memories are signed with"
          />
          {nameError && <Text style={styles.saveFailed}>{nameError}</Text>}
        </View>
      </ScrollView>
    </Modal>
  );
}

// Settings' sheet, so the two read as one app.
const styles = StyleSheet.create({
  screen: { flex: 1, backgroundColor: color.paper },
  body: { paddingHorizontal: 24, paddingTop: 28, paddingBottom: 72, gap: 6 },
  top: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' },
  title: screenTitle,
  photo: { alignItems: 'center', gap: 14, marginTop: 28 },
  // Gold-rimmed, like a portrait in a locket.
  ring: { padding: 4, borderRadius: 999, borderWidth: 2, borderColor: color.gold },
  actions: { flexDirection: 'row', gap: 10 },
  rule: { marginTop: 32 },
  section: { marginTop: 24, gap: 12 },
  sectionTitle: { ...label },
  note: { ...font.prose, fontSize: 15, lineHeight: 24, color: color.inkFaint },
  input: { ...input, ...font.title, fontSize: 24 },
  // Gold, as Settings' and Submit's error lines.
  saveFailed: { ...font.ui, fontSize: 13, lineHeight: 20, color: color.gold, textAlign: 'center' },
  link: { alignSelf: 'center' },
  linkText: { ...font.uiMedium, fontSize: 13, color: color.ink, textDecorationLine: 'underline' },
});
