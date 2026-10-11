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
<style>body{font-family:system-ui,sans-serif;max-width:40rem;margin:3rem auto;padding:0 1rem;line-height:1.6;color:#222}h1{font-size:1.5rem}h2{font-size:1.05rem;margin-top:2rem}td,th{text-align:left;vertical-align:top;padding:.25rem .5rem .25rem 0}</style>
</head><body>
<h1>Memory Lane - Privacy Policy</h1>
<p>Memory Lane plans a walk past stories of the places on it, and a story opens only
when you stand on its spot. This page says what we collect to do that, why, who else
sees it, how long we keep it, and what you can ask of us.</p>

<h2>Who we are</h2>
<p>The data controller is [COMPANY NAME AB, a Swedish company not yet registered:
its organisation number and postal address go here before launch]. See
<a href="#contact">Contact</a> for how to reach us.</p>

<h2>Location</h2>
<p>The app uses your phone's precise location, with your permission, for three things:
to plan a walk from where you are, to check that you are standing at a stop before its
story unlocks, and to place a memory you post.</p>
<p>The position itself is sent with each of those requests and is not saved in our
database. What is saved: the walks you plan (their stops and the streets between them,
but not where you started from or where you finished), and which story you opened and
when. Since every story has a known spot, a record of an opening is also a record that
you were at that spot at that time, and the first stop of a walk is usually near where
you planned it. Your position also appears in our request logs (see
<a href="#logs">Request logs</a>).</p>
<p>The app does not read your step count, your motion or fitness data, or any health
data.</p>

<h2>Background location and notifications</h2>
<p>Turning on &ldquo;Notify me when a memory is nearby&rdquo; in Settings asks for an
additional permission, location in the background, so the phone can notice a stop of
your walk, or a locked story, close by while the app is closed, and show a local
notification. It is off unless you turn it on. The watching happens on your phone;
while it is on, the phone asks our server for the stories around it as you move, and,
at most once a week, may ask to open one of them for half an hour as a surprise. We
keep which story was offered and when, as we do for an opening. Turning it off, or
taking the permission away, stops it immediately.</p>

<h2>Accounts</h2>
<p>Memory Lane asks you to sign in, with Google or Apple, before you use it.
We never ask for a password. They tell us an
identifier for your account with them and, if you allow it, a verified email address,
and we store both. Google also tells us your name, and Apple tells the app your name the
first time you sign in: if you have not chosen a display name, that name becomes it, and
it is shown publicly under anything you post. You can change or clear it at any time.
We receive nothing else from your Google or Apple account, and never post anywhere on
your behalf. Apple's Hide My Email gives us a relay address, and that works fine here.
We do not use the email address to contact you or to match accounts.</p>
<p>You can sign out at any time, which unlinks the phone and deletes nothing. Deleting
your account, in the app, deletes everything listed below as ours to delete.</p>
<p>We do not collect advertising identifiers and do not track you across other apps or
websites.</p>

<h2>What you post</h2>
<p>A memory you file is public. Its text, tags, the place name and the coordinates you
were standing at are shown to anyone who walks to that spot, with your display name
and profile photo, or &ldquo;Anonymous&rdquo;. A note you leave under a memory is shown
to the others who have opened it. Do not post anything you would not want a stranger
standing there to read.</p>
<p>Photos and recordings you attach, and a profile photo, are stored on our servers and
shown with what you post. Photos are re-encoded when they arrive, which removes the
location, camera and time the phone wrote into them. Recordings are not changed, so do
not attach a file whose contents you would not publish.</p>
<p>Before a post is shown, its text is checked on our own server, against a word list
and for email addresses, phone numbers and links, and refused if it fails. Anyone can
report a memory; a report for privacy, defamation or copyright from a signed-in account
hides it at once, and other reports hide it once enough people make them, until we
review it. We keep the report so a dispute can be answered. You can block a person and
never see what they post again. You can delete anything you posted, in the app.</p>

<h2>Your walks, openings, hearts and notes</h2>
<p>We keep the walks you planned and finished, which stories you opened and when, the
stories you hearted, the notes you left, the reports you made and the people you
blocked. They make your journal, your walk history and its experience points, your
streak, and the counts an author sees (how many walkers read their memory and hearted
it, never who). A walk that opened nothing is deleted when it ends.</p>

<h2>The identifier your app makes</h2>
<p>The first time it talks to us, your copy of the app generates a random identifier
for itself and sends it with every request. It is created on your phone, not issued by
us, and is not your phone's advertising or hardware identifier. Once you sign in, it is
linked to your account. Anyone holding it can act as that installation, so the app
keeps it in the phone's secure storage.</p>

<h2>Subscriptions</h2>
<p>A subscription is bought through the App Store or Google Play, who take the payment;
we never see your card. RevenueCat, which handles subscriptions for us, receives your
account's identifier from us and the purchase from the store, and we keep only whether
your subscription is active and until when.</p>

<h2>Camera, photos and microphone</h2>
<p>Used only when you choose to attach something to a memory you are posting, or to set
a profile photo, and only for that. Nothing is captured in the background and nothing
is uploaded that you did not attach.</p>

<h2 id="logs">Request logs</h2>
<p>Our servers log each request: the time, the address it came from (IP), and the
address it asked for. For some requests that address includes your position and your
app's identifier. The logs are used to keep the service running and to stop abuse, and
are kept for [NUMBER] days by our hosting provider.</p>

<h2>Who else receives data</h2>
<p>We sell nothing and share nothing for advertising. These receive personal data while
we run the service:</p>
<ul>
<li><b>Railway</b> (United States) hosts our servers, database and request logs, on our
behalf.</li>
<li><b>RevenueCat</b> (United States) handles subscriptions, on our behalf.</li>
<li><b>Anthropic</b> (United States) runs the models that write the stories. The text of
a post may be sent to it when we check the collection for the same story told twice; it
does not train its models on what we send.</li>
<li><b>Google</b> and <b>Apple</b>, when you sign in, under their own terms. On Android,
the map is drawn by Google Maps.</li>
<li>When you post, the phone asks its own geocoder (Apple's, or Google's on Android) for
the name of the street you are on.</li>
<li>Opening a source, a Wikipedia preview or a picture loads it from that site, which
sees your IP address. Opening a source video hands you off to YouTube, whose own
privacy policy then applies.</li>
</ul>
<p>Where data goes to the United States, we rely on the EU-US Data Privacy Framework or
the European Commission's standard contractual clauses.</p>

<h2>Stories about other people</h2>
<p>The stories retold on Memory Lane come from published books, newspapers, archives,
plaques and videos, and some name the people in them. We retell them because a place
is worth knowing about. If a story is about you, or someone close to you who has
died, report it in the app (&ldquo;Privacy&rdquo;) or write to us, and it comes down
while we look at it.</p>

<h2>Why we may</h2>
<table>
<tr><th>What</th><th>Legal basis (GDPR Art. 6(1))</th></tr>
<tr><td>Your account, walks, openings, posts, notes, hearts, subscription, and the
location each of them needs</td><td>(b) providing the service you asked for</td></tr>
<tr><td>Background location</td><td>(a) your consent, which you withdraw by turning it
off</td></tr>
<tr><td>Checking posts, reports, blocking, request logs</td><td>(f) our legitimate
interest in a safe service, and (c) the Digital Services Act's notice-and-action
duty</td></tr>
<tr><td>Stories naming people, retold from published sources</td><td>(f) our legitimate
interest in telling the history of a place, weighed against theirs</td></tr>
</table>

<h2>How long we keep it</h2>
<ul>
<li>Your account, posts, media, walks, openings, hearts, notes, blocks and reports: until
you delete them or your account.</li>
<li>A report of somebody else's memory, after it was handled: as long as that memory
exists.</li>
<li>A photo or recording uploaded but never posted: until we next clear them out.</li>
<li>Request logs: [NUMBER] days.</li>
<li>Backups: [NUMBER] days.</li>
<li>Subscription records with RevenueCat and the stores: under their own terms.</li>
</ul>

<h2>Your rights</h2>
<p>You can ask for a copy of everything we hold about you, and to have it corrected,
deleted, or restricted; you can object to what we do on our legitimate interest, and
take back a consent at any time. We answer within a month. Most of it you can do in the
app: change your name or photo, delete a post, delete your account. You can also
complain to the Swedish Authority for Privacy Protection (IMY) or to the data protection
authority where you live, such as Datatilsynet in Denmark.</p>

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
