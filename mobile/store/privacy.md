# Privacy policy (source of truth)

The plain-text twin of the HTML served at `GET /privacy` (`api/main.py`). Change
one, change the other — `tests/test_store_copy.py` compares the claims, not the
wording, and will fail if either grows a section the other lacks.

Memory Lane shows travel memories drawn from publicly available video
transcripts, on a map near you, and lets you file your own.

**Location.** If you grant location permission, your device's approximate
coordinates are sent to our servers to look up memories near you, and to check
that you are close enough to unlock one. Coordinates are used for that request
and are not stored, profiled, or linked to you — an unlock records which memory
was opened and when, never where you were standing.

**Accounts.** You can use Memory Lane without signing in, and nothing in it is
behind a sign-in. We never ask for a password, because we do not have any to
store.

If you do sign in, it is with Google or Apple. They tell us an identifier for
your account with them and, if you allow it, an email address; we store both so
that your collection can follow you to a new phone. We receive nothing else — no
contacts, no calendar, no profile, no access to anything in your Google or Apple
account — and we never post anywhere on your behalf. Apple's Hide My Email gives
us a relay address instead of your real one, and that works fine here. You can
sign out at any time, which unlinks the device and deletes nothing.

We do not collect advertising identifiers.

If you post a memory you may give a display name. It is optional, it is shown
publicly under what you post, it is whatever you type, and you can change or
clear it at any time. It is not verified and is not linked to anything else
about you.

**What you post.** A memory you file is public. Its text, tags, the place name
you give it and the coordinates you were standing at are shown to anyone who
comes to that spot, alongside the display name you chose or "Anonymous". Do not
post anything you would not want a stranger standing there to read.

Photos and recordings you attach are stored on our servers and shown with the
memory. We strip nothing from them beyond re-encoding photos for size, so do not
attach a file whose contents you would not publish.

Anyone can report a memory. Enough reports and it stops being shown to anybody;
the record of it is kept so a dispute can be answered. To have something you
posted removed, open an issue on the project repository.

**Your unlocked memories.** To keep the memories you unlock, your copy of the
app generates a random identifier for itself the first time you unlock
something, and sends it with that unlock. We store the identifier and which
memories it has opened, so your collection survives the app losing its local
data.

It is created on your device, not issued by us. It is not linked to your name,
your phone, your advertising identifier, or any other app, and it tells us
nothing except that one installation of Memory Lane unlocked a particular
memory. Deleting the app discards it, and the collection it refers to becomes
unreachable.

**Camera, photos and microphone.** Used only when you choose to attach something
to a memory you are posting, and only for that. Nothing is captured in the
background and nothing is uploaded that you did not attach.

**What we do keep.** Our servers keep standard technical request logs
(timestamp, coarse IP, endpoint) for reliability and abuse prevention.

**Third parties.** We sell nothing and share nothing. Opening a memory's source
video hands you off to YouTube, whose own privacy policy then applies.

**Contact.** Open an issue on the project repository.
