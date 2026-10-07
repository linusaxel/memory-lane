"""The privacy policy, served from the API because both app stores require a
publicly reachable URL and this host already exists.

`mobile/store/privacy.md` is the plain-text twin a human pastes into App Store
Connect. tests/test_store_copy.py holds the two to the same set of disclosures.
"""

from fastapi import APIRouter
from fastapi.responses import HTMLResponse

from pipeline.config import CONTACT_EMAIL

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

<h2>Background location and notifications</h2>
<p>Turning on &ldquo;Notify me when a memory is nearby&rdquo; in Settings asks for an
additional permission &mdash; location in the background &mdash; so we can check your
position against memories you have not unlocked yet even while the app is closed, and
show a local notification when one is close. This is off unless you turn it on, and it
only affects that check: your coordinates are still not stored or linked to you, the
notification is generated on your device, and nothing is sent anywhere beyond the same
nearby-memories check the map already makes. Turning it off stops the check immediately.</p>

<h2>Walks and levels</h2>
<p>A memory opens only as a stop of a walk the app planned, standing there. Finished
walks earn experience, worked out from the walks we already keep and never stored on
its own, and it cannot be bought. Your walks are shown back to you as their shapes.
Deleting your account deletes the walks. If you once bought keys, we keep the store's
transaction id for each pack until you delete your account.</p>

<h2>Accounts</h2>
<p>Memory Lane asks you to sign in before you use it. We never ask for a password,
because we do not have any to store.</p>
<p>You sign in with Google or Apple. They tell us an identifier for your
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
Photos are re-encoded when they arrive, which removes the location, camera and time
the phone wrote into them. Nothing else is stripped, so do not attach a file whose
contents you would not publish.</p>
<p>Before anything you post is shown, its text is checked for abuse, and refused if it
is. Anyone signed in can report a memory. Enough reports and it stops being shown to
anybody until we review it; the record of it is kept so a dispute can be answered. You
can block a person, and you will not see anything they post again. You can delete anything you posted
from the app, or delete your account, which deletes everything you posted with it.</p>

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
<p>We sell nothing. The text of what you post is sent to Anthropic, only to check it
before it is shown; it is not used to train their models. Opening a memory's source
video hands you off to YouTube, whose own privacy policy then applies.</p>

<h2 id="contact">Contact</h2>
<p>CONTACT_LINE To ask a question, to report something, or for a copy of everything we
hold about you.</p>
</body></html>"""


@router.get("/privacy", response_class=HTMLResponse, include_in_schema=False)
def privacy_policy():
    """Both app stores require a publicly reachable privacy policy URL. The app's
    Contact row opens it at #contact, so the address lives in one setting."""
    line = (
        f'Write to <a href="mailto:{CONTACT_EMAIL}">{CONTACT_EMAIL}</a>.'
        if CONTACT_EMAIL
        else "A contact address is published here before launch."
    )
    return PRIVACY_HTML.replace("CONTACT_LINE", line)
