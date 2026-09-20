"""The privacy policy, served from the API because both app stores require a
publicly reachable URL and this host already exists.

`mobile/store/privacy.md` is the plain-text twin a human pastes into App Store
Connect. tests/test_store_copy.py holds the two to the same set of disclosures.
"""

from fastapi import APIRouter
from fastapi.responses import HTMLResponse

router = APIRouter()

PRIVACY_HTML = """<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Memory Lane - Privacy Policy</title>
<style>body{font-family:system-ui,sans-serif;max-width:40rem;margin:3rem auto;padding:0 1rem;line-height:1.6;color:#222}h1{font-size:1.5rem}h2{font-size:1.05rem;margin-top:2rem}</style>
</head><body>
<h1>Memory Lane - Privacy Policy</h1>
<p>Memory Lane shows travel memories drawn from publicly available video transcripts,
on a map near you.</p>

<h2>Location</h2>
<p>If you grant location permission, your device's approximate coordinates are sent to
our servers to look up memories near you, and to check that you are close enough to
unlock one. Coordinates are used for that request and are not stored, profiled, or
linked to you &mdash; an unlock records which memory was opened and when, never where
you were standing.</p>

<h2>Accounts</h2>
<p>You can use Memory Lane without signing in, and nothing in it is behind a sign-in.
We never ask for a password, because we do not have any to store.</p>
<p>If you do sign in, it is with Google or Apple. They tell us an identifier for your
account with them and, if you allow it, an email address; we store both so that your
collection can follow you to a new phone. We receive nothing else &mdash; no contacts,
no calendar, no profile, no access to anything in your Google or Apple account &mdash;
and we never post anywhere on your behalf. Apple's Hide My Email gives us a relay
address instead of your real one, and that works fine here. You can sign out at any
time, which unlinks the device and deletes nothing.</p>
<p>We do not collect advertising identifiers.</p>
<p>If you post a memory you may give a display name. It is optional, it is shown publicly
under what you post, it is whatever you type, and you can change or clear it at any time.
It is not verified and is not linked to anything else about you.</p>

<h2>What you post</h2>
<p>A memory you file is public. Its text, tags, the place name you give it and the
coordinates you were standing at are shown to anyone who comes to that spot, alongside
the display name you chose or &ldquo;Anonymous&rdquo;. Do not post anything you would
not want a stranger standing there to read.</p>
<p>Photos and recordings you attach are stored on our servers and shown with the memory.
We strip nothing from them beyond re-encoding photos for size, so do not attach a file
whose contents you would not publish.</p>
<p>Anyone can report a memory. Enough reports and it stops being shown to anybody; the
record of it is kept so a dispute can be answered. To have something you posted removed,
open an issue on the project repository.</p>

<h2>Your unlocked memories</h2>
<p>To keep the memories you unlock, your copy of the app generates a random identifier
for itself the first time you unlock something, and sends it with that unlock. We store
the identifier and which memories it has opened, so your collection survives the app
losing its local data.</p>
<p>It is created on your device, not issued by us. It is not linked to your name, your
phone, your advertising identifier, or any other app, and it tells us nothing except
that one installation of Memory Lane unlocked a particular memory. Deleting the app
discards it, and the collection it refers to becomes unreachable.</p>

<h2>Camera, photos and microphone</h2>
<p>Used only when you choose to attach something to a memory you are posting, and only
for that. Nothing is captured in the background and nothing is uploaded that you did not
attach.</p>

<h2>What we do keep</h2>
<p>Our servers keep standard technical request logs (timestamp, coarse IP, endpoint)
for reliability and abuse prevention.</p>

<h2>Third parties</h2>
<p>We sell nothing and share nothing. Opening a memory's source video hands you off to
YouTube, whose own privacy policy then applies.</p>

<h2>Contact</h2>
<p>Questions: open an issue on the project repository.</p>
</body></html>"""


@router.get("/privacy", response_class=HTMLResponse, include_in_schema=False)
def privacy_policy():
    """Both app stores require a publicly reachable privacy policy URL."""
    return PRIVACY_HTML
