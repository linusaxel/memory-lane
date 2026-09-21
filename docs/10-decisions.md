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

121 of 215 placed memories sit on 28 shared city-centroid points — coordinates the
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

### Search is a stored vector, so it can use an index

It was a sequential scan on purpose for a long time, and the reasoning was
sound: `SEARCH_VECTOR` spanned two tables (`m.summary || ' ' || p.name`), and
no expression index can serve an expression like that. Splitting it into
`to_tsvector(m.summary) @@ q OR to_tsvector(p.name) @@ q` indexes cleanly and
silently changes what search *means* — a query whose words straddle the two
fields ("cellar heckler", where the Comedy Cellar is the place and the heckler
is in the summary) matches the joined vector and neither half of the OR.
`tests/test_api_search.py` pins that behaviour and says so.

So the concatenation is materialised rather than recomputed: the same text, on
the row, GIN-indexed, kept true by triggers on both tables
(`db/migrations/010`). Search means exactly what it meant before, and the plan
uses `idx_memories_search`.

The cost is a trigger on each side. The one that is easy to forget is the
second: a place rename has to rewrite the vector of every memory filed there,
or a renamed place answers to its old name for ever — which is worse than the
scan was. Renames come from `pipeline/dedup.py` in reviewed batches, so that
is a handful of rows at a time.

### The gate's uniqueness question is indexed, and it is the hot path

`COORDINATE_IS_UNIQUE` decides whether a memory is gated at all, by asking
whether any other place shares its snapped grid cell. It compares
`ST_SnapToGrid(...)` on both sides, which nothing could serve, so Postgres
scanned every place in the table - once per row returned.

Measured on 50,000 memories across 20,000 places, `/v1/memories/nearby` at a
10km radius: **338 ms before, 14 ms after**, with 305 ms of the original in
that one subplan. `/v1/places/nearby` went 265 ms to 9 ms. The app refires
`nearby` on every pan, so this was the single slowest thing in the product.

The index must match the query's expression exactly, argument form included -
`ST_SnapToGrid(geom, size)` and `ST_SnapToGrid(geom, 0, 0, size, size)` are the
same answer and different expressions, and only the matching one is used. The
test asserts the planner reaches for it rather than that the index exists.

### `/v1/stats` is cached for five minutes

Four unbounded counts and `ST_ClusterDBSCAN(...) OVER ()` — one partition, so
no index helps and no filter shrinks it — over every placed memory in the
corpus. It is also the endpoint every phone calls when the map comes back
empty, which is the normal experience anywhere the corpus does not reach. The
cheapest way to make the server work hardest is to stand somewhere it has
nothing.

None of its answers change between pipeline runs, so they are held for
`STATS_TTL_SECONDS`. In-process and per hotspot count, because the count is a
query parameter. Two threads can compute it at once and the loser has simply
done the work twice, which is cheaper than holding a lock across a query that
long. Tests share a process, so `api_client` clears it.

### `NULLS LAST` in `CONTRAST_ORDER` is load-bearing

Postgres sorts NULL *first* under `DESC`. Every memory extracted before contrast
scoring existed has no score, so without `NULLS LAST` the unscored ones outrank
every scored one and the ranking is exactly inverted.

### Hotspots cluster places, not memories

DBSCAN was fed one point per memory, so a place with fifty memories handed it
fifty identical points - and it is the one query here whose cost is
superlinear in its input. Clustering places and summing their counts afterwards
gives the same hotspots for a ninth of the work: measured on 50,000 memories
across 20,000 places, 10.9s became 1.2s with the same four areas and the same
totals.

Two things move slightly, both toward the question being asked. The centroid is
the centre of the places in a cluster rather than one dragged toward the
busiest venue in it, and the label is the modal trailing name-component across
places rather than across memories. "The closest memories are in New York" is a
question about an area.

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

### A quota checked before the write is not a quota

Both allowances — twenty submissions and 64MB of uploads a day — read a count
in one transaction and wrote in another. Anybody can win that race by not
waiting: fire twenty requests at once, all twenty read the same count, all
twenty are allowed. That defeats the control exactly when it matters, because
the only person it exists to stop is the one doing it deliberately.

The cheap check stays, because it is what refuses the ordinary case without
taking a lock at all. The write transaction then asks again under a lock: the
user row for submissions, and for uploads the device row that `touch_device`
was already locking with its `ON CONFLICT DO UPDATE` — the serialisation was
there, the count was simply on the wrong side of it.

Uploads have a second half. The bytes are on the disk before the authoritative
check can run, so every way out of that block deletes them, a failed insert
included. Orphans there are invisible: referenced by no row, returned by no
query, costing disk for ever.

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

### A long `animateToRegion` never reports back at all

The paragraph above is true of short flights and false of long ones. Fly 40 m
and the map settles and calls `onRegionChangeComplete`; fly 6,000 km and it
never does. Measured on one build, from `[CAM]` traces of the same code path:
reported at 40 m, silent at 6,000 km.

Two flows died on it, and both looked like something else. Opening the app far
from `FALLBACK_REGION` fetched the fallback once and then nothing, so somebody
in Copenhagen read Manhattan's memory count over their own city and F19's card
never appeared at all — the map was visibly in the right place, which is what
made it look like a data problem. And F19's own "Show me New York" is a long
jump by definition, so it moved the camera and left the pins behind.

`useMapCamera` therefore watches a flight instead of trusting it. The map's own
report wins when it comes, because it knows the region it fitted to the screen
and we do not; if nothing arrives by the time the flight is over, the hook
reports the destination itself. While a flight is in the air a report about
somewhere else is the map describing where it used to be — the region it was
born at, announced after we flew away — and is dropped, or it would fetch the
wrong pins *and* win by being the later request.

The guard against eager fetching still holds for every move the map does
report, which is nearly all of them. `.maestro/f19-elsewhere.yml` is what fails
if this regresses; there is no unit test, because the behaviour being relied on
is the native map's.

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

### The pool is sized to the server, and the server to the pool

FastAPI runs a `def` handler on anyio's thread pool — forty threads by default,
and every endpoint here but one is a `def` — while SQLAlchemy was left on its
own defaults of five connections plus ten overflow. Twenty-five of those
threads could be parked on a pool that cannot grow, each holding an OS thread
in order to wait.

The pool is sized explicitly now, and a lifespan hook narrows the thread pool
to the same ceiling, so the queueing happens before a thread is taken rather
than after. One number, `MAX_CONCURRENCY`, so they cannot drift apart.

The wait for a connection is five seconds, not thirty. The app gives up on any
request after eight (`REQUEST_TIMEOUT_MS`), so a connection handed over at
thirty seconds is handed to nobody — it just holds the slot for a client that
has gone. `tests/test_db_pool.py` keeps the two in that order.

### The server has one clock, and it is UTC

`not_yet_open` asked Python for today's date, which is the host's local one.
`ANNIVERSARY` asked the database for `CURRENT_DATE`, which is the cluster's. A
CEST laptop against a UTC container disagreed for two hours every night — and
those two rules decide whether a memory is shut and whether it is "on this
day", so for two hours a night the app could hold both opinions at once. It is
also how two tests that had passed for weeks failed at 00:04 with nothing
changed but the clock.

Both are UTC, and the SQL says so explicitly rather than inheriting whatever
the cluster is set to. Neither machine's local time meant anything to the
person holding the phone anyway — a viewer's own date is the honest answer to
"on this day", and getting it right would mean the client sending its date.

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
