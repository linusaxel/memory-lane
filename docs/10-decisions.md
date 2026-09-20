# Decisions

Why the code is shaped the way it is, for the calls where the obvious
alternative is wrong and the reason is not visible from the code.

This file exists because the reasoning used to live in comments, and comments
next to code are prose nobody re-reads when the code changes. By the time
sign-in shipped, eight separate comments still said the app had no accounts.
Anything here that stops being true should be edited or deleted, not left.

Code points here by anchor: `# see docs/10-decisions.md#the-gate`.

---

## The gate

### Only an unshared coordinate is gated

`api/main.py` `COORDINATE_IS_UNIQUE`, and `api/card.py` keeps a copy.

111 of 186 placed memories sit on 34 city-centroid points — coordinates the
model emitted when the transcript never said the address. A memory filed 2 km
from where it happened cannot be gated on standing there, so gating those would
ask somebody to walk to a fiction. Only a coordinate no other place shares is
trusted enough to lock. 0.0001 degrees is ~11 m, the same grid the app clusters
pins on.

This is a proxy. `precision_meters` is the direct measure and would be the
better rule, but 35 of those stacked places claim 50 m accuracy, so the column
cannot be trusted until extraction is re-run. See `TODO.md`.

### Places holding a submission do not count toward that

Each submission mints its own place row at the submitter's GPS position. Without
excluding those from the count, filing a memory outside Katz's would put a second
place in that grid cell and silently unlock every memory already there — a gate
anybody could open by posting next to it.

It is `NOT EXISTS` over a user memory rather than `EXISTS` over an extracted one
so that a place with no memories at all still counts, which is what it did
before submissions existed.

A submitted memory is gated on its own terms instead: the person was standing
there, so the coordinate is real by construction.

### 150 m, not 50 m

Urban GPS drifts tens of metres. A gate that will not open while you are
standing on the spot is a bug the person blames on themselves.

### The position is self-reported

This stops `curl`, not a determined spoofer — and since submissions, it cuts
both ways: a memory is also filed at a position nobody verified. Attestation is
the fix and needs more than accounts. Logged in `TODO.md`.

---

## Queries

### Search is a sequential scan, on purpose

`SEARCH_VECTOR` spans two tables (`m.summary || ' ' || p.name`), so no expression
index can serve it.

Splitting it into `to_tsvector(m.summary) @@ q OR to_tsvector(p.name) @@ q` looks
like the fix and is not: an OR across two tables still cannot use either index,
because a row can qualify from the other side. Measured against the live
database — the planner keeps scanning. The two designs that would work are in
`TODO.md`; both cost more than a 224-memory corpus is worth.

### `NULLS LAST` in `CONTRAST_ORDER` is load-bearing

Postgres sorts NULL *first* under `DESC`. Every memory extracted before contrast
scoring existed has no score, so without `NULLS LAST` the unscored ones outrank
every scored one and the ranking is exactly inverted.

### Hotspots use DBSCAN, not a rounded grid

0.5 degrees is roughly a metro area. A grid splits any city that straddles a cell
boundary — New York's places span 40.70–40.82, and a 0.1 grid cut them into two
separate "hotspots".

The label is the most common trailing component of the cluster's place names:
"Gotham Comedy Club, New York" → "New York". Crude, and correct for every
cluster in the corpus, which is the bar for a hint.

### A count query must mirror its result query's WHERE

Otherwise `meta.total` is wrong and pagination breaks. This bit three endpoints
once already.

---

## Writing

### A submission mints its own place

Not reusing one by name: two people filing at the same café would fight over
whose spelling wins. The map groups by coordinate, so they land under one pin
either way.

### Media lives on a disk, not in object storage

One volume is the whole feature until somebody is paying for bandwidth. The
upload path is a trust boundary in three places — filename, extension, and the
claim about what the bytes are — and none of the three comes from the client.
`api/media.py` has the detail.

### `REPORT_THRESHOLD` is the whole moderation system

Three distinct devices hide a memory. Low, because the corpus is small and a
wrongly hidden memory is recoverable while a libel left up for a week is not.
`hidden` is a flag and not a delete: a takedown that destroys the evidence makes
the next dispute unanswerable. There is no appeal, no reinstatement and no queue
for a human — that is the ceiling, and it is fine until there is a moderator.

---

## Identity

### No session tokens, signed in or not

The device id the app generates for itself is the only credential; signing in
binds `devices.user_id`. Every endpoint written before sign-in keeps working
unchanged, and a second phone becomes a second device on one user — which is the
whole of what sign-in buys. Nothing else needed inventing to get it.

The consequence: the device id is a bearer token in a request body, so anyone
holding yours can act as you. Same threat model as the self-reported position
above, and OAuth did **not** replace it.

### Google and Apple only

No passwords means nothing to store, reset, rotate or leak, and no reset-email
flow. Apple is not a preference: App Store review requires Sign in with Apple as
soon as any other third-party sign-in exists on iOS.

`api/auth.py` covers what a token has to survive — signature, audience, issuer —
and why an unconfigured server answers 503 rather than verifying against nothing.

### `MY_DEVICES` keeps a `d.id = :device_id` arm

Unlocks are recorded against a device, which was right while a device was all
there was. Signed in, the collection has to follow the person. That arm is what
keeps it working before anybody signs in, and after signing out.

`MIN(unlocked_at)` because two of somebody's phones can both have earned the same
memory; the first time is the one that counts, and without the grouping it would
appear twice.

### An anonymous user is absorbed on sign-in; a real account never is

Filing a memory and then signing in is the normal order, and losing it in between
is the version of this nobody forgives. But folding together two accounts that
each have their own sign-in is not a decision this code is in a position to make,
so the device switches and both keep what is theirs.

Emails are recorded and never matched on. Linking two identities because they
share an address is the classic takeover: an address can be reassigned, and
Apple's may be a relay.

---

## The app

### `animateToRegion` never lands on the region you give it

The map fits the deltas to the screen, so the viewport it settles on covers
noticeably more ground — asked 0.70 km, settled 0.89 km. Moving the camera and
calling `load()` in the same breath is therefore two requests for one action, the
first of them for a viewport that never exists. Move the camera; let
`onRegionChangeComplete` report back.

It is also discarded silently if it fires before `onMapReady`, which looks
exactly like the bug it was meant to fix. Readiness is tracked in a ref rather
than inferred from `mapRef.current`, which is set earlier.

### The font gate makes effects run before the map exists

The app renders `null` until the two font families load, so a mount effect's
recentre fires into nothing and leaves everybody at the fallback zoom. Pending
regions are queued and replayed from `onMapReady`.

### Glass was tried and reverted

Blur panels are on every list of tells for a generated interface. The app uses
paper and rules instead. `docs/09-visual-design.md` has the research.

---

## Pipeline

### The RQ worker re-execs itself on macOS

`OBJC_DISABLE_INITIALIZE_FORK_SAFETY` has to be set *before* any ObjC-linked
library is imported, and RQ's work horse forks. Setting it with
`os.environ.setdefault` inside Python is too late — measured, 22 of 22 work
horses still crashed with signal 6. `pipeline/worker.py` re-execs itself with the
variable set before importing anything else.

### The classifier fails loud on a config error and open on a transient one

A 404/401/403 means `CLASSIFIER_MODEL` is unusable and will fail identically on
every chunk forever — that exact bug once reported 22 fictional classifications
because the handler was blanket fail-open. A 429, a 5xx or a connection error is
transient, and over-processing one chunk is the cheaper mistake.

---

## Serving

### The card is rendered on the server

One template, three consumers: the app sheet, the embed widget, and any pasted
link. Rendered server-side because the attribution is the legal posture — a
client that assembles the card from JSON can drop the credit line, and this is
somebody else's archive. Server-rendered means the credit ships welded to the
content.

It was also a hole once. `/v1/memories/{id}/card` rendered a locked memory in
full, and ids are sequential, so the whole corpus was one loop away. The card
does not go through `row_to_memory`, so it has to remember the gate separately —
`tests/test_api_unlock.py` holds it to that.

### The embed is an iframe, not injected markup

It is somebody else's site: their CSS cannot reach our map, our CSS cannot reach
their article, and their Content-Security-Policy has one origin to allow instead
of a script rewriting their DOM.

Contrast ordering matters more here than in the app — an embed is a handful of
pins on a tourism page, so the first card has to be the one worth reading.

---

## Pipeline, continued

### Place dedup matches on names, not coordinates

`db/migrations/001_places_unique.sql` stopped the same exact `place_query`
minting a new row. What it cannot catch is one venue described two ways:

    [108] Gotham Comedy Club New York City           6 memories  40.75890, -73.98510
    [211] Gotham Comedy Club Chelsea New York City   1 memory    40.74310, -73.99670

One venue, two pins, 1.8 km apart — and both rows claim 50 m precision, so the
obvious rule (collapse places whose coordinates fall within their combined
precision) would never fire. The model disagreed with itself about where Gotham
is. Names are the reliable signal; coordinates are only a sanity bound.

Naive token-subset matching finds 148 pairs among 194 places, because "New
Orleans Louisiana" is a subset of every venue in New Orleans and would absorb
the first one it met. The fix needs no gazetteer: a token appearing in many
places is a location or filler word, and one appearing in few is the venue's
actual name. Both sides must contribute a distinctive token — which is exactly
what a bare city reference cannot do.

Deliberately conservative. A wrong merge destroys data and is invisible
afterwards.

### Channel discovery uses yt-dlp, not a scrape

As of 2026-09-20 a regex over `"videoId":"..."` in the channel HTML returns zero
videos for every channel tested — YouTube no longer serves that markup to a plain
client. Rebuilding it on the internal `youtubei/v1/browse` endpoint means a lot
of undocumented JSON walking that fails silently by returning a short list.
yt-dlp is that parser, maintained weekly.

`crawler/` must not import `pipeline` — `pipeline.ingest` imports it.

### Summary quality is measured, not asserted

"Improve the memory output" is unfalsifiable until the defects are counted, and
extraction costs money, so there is one chance to tell whether a prompt change
helped. `python -m pipeline.quality` prints the same four numbers before and
after. Every check was found by reading the corpus, not imagined; none is a hard
failure, they are a direction. The baseline is in `CLAUDE.md`.

### Markers are anchored explicitly, because the two platforms disagree

`react-native-maps` gives a custom marker view a different anchor on each
platform. iOS centres it on the coordinate (a marker with children stops being
an `MKMarkerAnnotationView`, whose balloon tip is what sits on the point);
Android calls `setAnchor(0.5f, 1.0f)` unconditionally and hangs the view above
it. With a 46px tap-target wrap that was roughly 70 m of apparent offset at
street zoom on Android — so the reach ring, whose whole job is to be the thing
you are standing inside, was not centred on the person.

`anchor={{ x: 0.5, y: 0.5 }}` on every marker. It is one prop, it is correct on
both, and it has to stay: the bug is invisible on the simulator anybody is
likely to be testing on.

### Reach is measured to the memory, not to the pin

`cluster.ts` draws a group on a *rounded* coordinate. At the 4dp street grid
that is within ~8 m of its members and measuring to it was harmless. It stopped
being harmless when the grid started following the zoom: at 1dp a group's point
can sit kilometres from everything under it, and `reachOf` would then either
offer an unlock for something 5 km away — which the server refuses, so the
button fails in the person's hand — or hide the mechanic while they stand on it.

`reachOf` and `nearestLocked` both measure to the nearest *locked member*. It is
the same haversine count and it is correct at any precision.

### A tap on a wide group zooms instead of opening

Once the grid loosens, a group is two different things wearing one pin: several
memories sharing a doorway, or several places the zoom merged. The sheet pager
says "1 of 23 here", which is true of the first and a lie about the second.
`spanMeters` tells them apart — the furthest member from the drawn point, zero
at a genuine shared centroid — and past `CLUSTER_SPAN_M` the tap flies the
camera in rather than opening anything.

No `load()` alongside that `flyTo`: landing fires `onRegionChangeComplete`,
which is what fetches. Doing both is two requests for one action, the first of
them for a viewport that never exists.
