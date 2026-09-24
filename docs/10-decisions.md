# Decisions

Why the code is shaped the way it is, for the calls where the obvious
alternative is wrong and the reason is not visible from the code.

This file exists because the reasoning used to live in comments, and comments
next to code are prose nobody re-reads when the code changes. By the time
sign-in shipped, eight separate comments still said the app had no accounts.
Anything here that stops being true should be edited or marked Superseded, not left.

Code points here by anchor: `# see docs/10-decisions.md#the-gate`.

Each entry is a decision record in one file, so the anchors hold. It opens
with a `Status:` line: Accepted, Superseded or Rejected, dated where the
decision was. **Options considered:** and **Consequences:** label a paragraph
only where the entry already argues one; nothing is written to fill the form.
A superseded entry stays, marked, and is never deleted: the next person to
have the same idea needs to find out why it went.

---

## The gate

### Only an unshared coordinate is gated

Status: Accepted

`api/main.py` `COORDINATE_IS_UNIQUE`, and `api/card.py` keeps a copy.

121 of 215 placed memories sit on 28 shared city-centroid points — coordinates the
model emitted when the transcript never said the address. A memory filed 2 km
from where it happened cannot be gated on standing there, so gating those would
ask somebody to walk to a fiction. Only a coordinate no other place shares is
trusted enough to lock. 0.0001 degrees is ~11 m, the same grid the app clusters
pins on.

**Options considered:** This is a proxy. `precision_meters` is the direct measure and would be the
better rule, but 35 of those stacked places claim 50 m accuracy, so the column
cannot be trusted until extraction is re-run. See
[the coordinates are mostly guesses](#the-coordinates-are-mostly-guesses-and-they-do-not-admit-it).

### Places holding a submission do not count toward that

Status: Accepted

Each submission mints its own place row at the submitter's GPS position. Without
excluding those from the count, filing a memory outside Katz's would put a second
place in that grid cell and silently unlock every memory already there — a gate
anybody could open by posting next to it.

**Options considered:** It is `NOT EXISTS` over a user memory rather than `EXISTS` over an extracted one
so that a place with no memories at all still counts, which is what it did
before submissions existed.

A submitted memory is gated on its own terms instead: the person was standing
there, so the coordinate is real by construction.

### 20 m

Status: Accepted 2026-09-24

Decided 2026-09-24: you should be standing at the place, not down the street
from it. It was 150 m, on the argument that urban GPS drifts tens of metres and
a gate that will not open while you stand on the spot is a bug the person
blames on themselves. That risk is now accepted, not solved: between tall
buildings a phone can read 20-30 m off, and on those spots the ring will refuse
somebody who is there. `UNLOCK_RADIUS_METERS` is the knob if the street says so.

**Consequences:** Two things follow. A pin further than the gate from any walkable way can never
be stood on, so with streets a route drops it (`api/route_solver.py`, `_plan_route`).
And the proximity notification cannot use the gate as its region - iOS does not
reliably fire under ~100 m - so it watches 100 m and lets the map do the rest
(`mobile/src/geofenceRegions.ts`).

### The position is self-reported

Status: Accepted

This stops `curl`, not a determined spoofer — and since submissions, it cuts
both ways: a memory is also filed at a position nobody verified. Attestation is
the fix and needs more than accounts. Logged in `TODO.md`.

### Only today's walk unlocks

Status: Accepted (2026-09-24). Replaces "Unlocking is Walk-only, and only the
app knows it".

The app is one walk a day, five stops, and nothing else: no map of everything
(F29 is gone), because a corpus you can browse is a corpus you can finish. So
`POST /v1/memories/{id}/unlock` refuses with 403 any memory that is not a stop
of today's `daily_routes` row for this account (`ON_TODAYS_ROUTE_QUERY`),
however close you stand.

The old decision kept this in the client because a "which tab" flag would be
as self-reported as the position. The route is not self-reported: the server
chose it and stored it on accept, and the client never sends stop ids. That is
what makes the rule enforceable here and not there.

Filing still opens its own memory for its author: that unlock is written by
`POST /v1/memories`, not by this endpoint. It no longer extends the streak
(F27), or the limit could be dodged by posting. Position is still self-reported,
so a spoofed GPS walks today's five from a sofa, and no more than five.

---

## Queries

### Search is a stored vector, so it can use an index

Status: Accepted

**Options considered:** It was a sequential scan on purpose for a long time, and the reasoning was
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

**Consequences:** The cost is a trigger on each side. The one that is easy to forget is the
second: a place rename has to rewrite the vector of every memory filed there,
or a renamed place answers to its old name for ever — which is worse than the
scan was. Renames come from `pipeline/dedup.py` in reviewed batches, so that
is a handful of rows at a time.

### The gate's uniqueness question is indexed, and it is the hot path

Status: Accepted

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

Status: Accepted

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

Status: Accepted

Postgres sorts NULL *first* under `DESC`. Every memory extracted before contrast
scoring existed has no score, so without `NULLS LAST` the unscored ones outrank
every scored one and the ranking is exactly inverted.

### Hotspots cluster places, not memories

Status: Accepted

DBSCAN was fed one point per memory, so a place with fifty memories handed it
fifty identical points - and it is the one query here whose cost is
superlinear in its input. Clustering places and summing their counts afterwards
gives the same hotspots for a ninth of the work: measured on 50,000 memories
across 20,000 places, 10.9s became 1.2s with the same four areas and the same
totals.

**Consequences:** Two things move slightly, both toward the question being asked. The centroid is
the centre of the places in a cluster rather than one dragged toward the
busiest venue in it, and the label is the modal trailing name-component across
places rather than across memories. "The closest memories are in New York" is a
question about an area.

### Hotspots use DBSCAN, not a rounded grid

Status: Accepted

**Options considered:** 0.5 degrees is roughly a metro area. A grid splits any city that straddles a cell
boundary — New York's places span 40.70–40.82, and a 0.1 grid cut them into two
separate "hotspots".

The label is the most common trailing component of the cluster's place names:
"Gotham Comedy Club, New York" → "New York". Crude, and correct for every
cluster in the corpus, which is the bar for a hint.

### A count query must mirror its result query's WHERE

Status: Accepted

Otherwise `meta.total` is wrong and pagination breaks. This bit three endpoints
once already.

---

## Writing

### A submission mints its own place

Status: Accepted

**Options considered:** Not reusing one by name: two people filing at the same café would fight over
whose spelling wins. The map groups by coordinate, so they land under one pin
either way.

### Media lives on a disk, not in object storage

Status: Accepted

One volume is the whole feature until somebody is paying for bandwidth. The
upload path is a trust boundary in three places — filename, extension, and the
claim about what the bytes are — and none of the three comes from the client.
`api/media.py` has the detail.

### `REPORT_THRESHOLD` is the whole moderation system

Status: Accepted

Three distinct devices hide a memory. Low, because the corpus is small and a
wrongly hidden memory is recoverable while a libel left up for a week is not.
`hidden` is a flag and not a delete: a takedown that destroys the evidence makes
the next dispute unanswerable. There is no appeal, no reinstatement and no queue
for a human — that is the ceiling, and it is fine until there is a moderator.

### A report count needs a lock too

Status: Accepted

Two people reporting the same memory at once would each read the count before
either insert commits, so both would see two reports where there are three -
the threshold reached and nothing done until a fourth report happened to land.
`SELECT ... FOR UPDATE` on the memory row serialises one memory's own reports
against each other; it takes no lock against anybody else's.

---

### A quota checked before the write is not a quota

Status: Accepted

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

---

### Notes are gated like a purchase

Status: Accepted

Authors keep filing when they hear back, so a memory takes notes, not
comments. Bandcamp is the model: only a buyer can leave a note on a release,
one each, and paying is what keeps spam out. Here the price is standing on the
spot. A note needs an unlock on one of the account's devices, and so does
reading them, because a note can quote the memory it is under.

One per device and no replies: a note is a visitor signing the book, not a
thread, and a thread is where the floodgates are. The author of the memory is
the whole of note moderation: they, or the note's writer, set `hidden`, and the
row stays for the same reason a reported memory's does. That is the ceiling,
fine until authors abandon memories or notes turn abusive; then notes get
reports and `REPORT_THRESHOLD`.

The weak spot is the gate's own:
[the position is self-reported](#the-position-is-self-reported), so a spoofed
GPS buys a note as cheaply as it buys an unlock. A note is shown to people who
stood there, too, which keeps its audience small.

A note is named by its own `id`, never its device: a device UUID is the only
credential and never goes to anyone else.

## Identity

### No session tokens, signed in or not

Status: Accepted

The device id the app generates for itself is the only credential; signing in
binds `devices.user_id`. Every endpoint written before sign-in keeps working
unchanged, and a second phone becomes a second device on one user — which is the
whole of what sign-in buys. Nothing else needed inventing to get it.

**Consequences:** the device id is a bearer token in a request body, so anyone
holding yours can act as you. Same threat model as the self-reported position
above, and OAuth did **not** replace it.

### Google and Apple only

Status: Accepted

No passwords means nothing to store, reset, rotate or leak, and no reset-email
flow. Apple is not a preference: App Store review requires Sign in with Apple as
soon as any other third-party sign-in exists on iOS.

`api/auth.py` covers what a token has to survive — signature, audience, issuer —
and why an unconfigured server answers 503 rather than verifying against nothing.

### `MY_DEVICES` keeps a `d.id = :device_id` arm

Status: Accepted

Unlocks are recorded against a device, which was right while a device was all
there was. Signed in, the collection has to follow the person. That arm is what
keeps it working before anybody signs in, and after signing out.

`MIN(unlocked_at)` because two of somebody's phones can both have earned the same
memory; the first time is the one that counts, and without the grouping it would
appear twice.

### An anonymous user is absorbed on sign-in; a real account never is

Status: Accepted

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

Status: Accepted

The map fits the deltas to the screen, so the viewport it settles on covers
noticeably more ground — asked 0.70 km, settled 0.89 km. Moving the camera and
calling `load()` in the same breath is therefore two requests for one action, the
first of them for a viewport that never exists. Move the camera; let
`onRegionChangeComplete` report back.

It is also discarded silently if it fires before `onMapReady`, which looks
exactly like the bug it was meant to fix. Readiness is tracked in a ref rather
than inferred from `mapRef.current`, which is set earlier.

### A long `animateToRegion` never reports back at all

Status: Accepted

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

Status: Accepted

The app renders `null` until the two font families load, so a mount effect's
recentre fires into nothing and leaves everybody at the fallback zoom. Pending
regions are queued and replayed from `onMapReady`.

### Glass was tried and reverted

Status: Superseded

Blur panels are on every list of tells for a generated interface. The app uses
paper and rules instead. `docs/09-visual-design.md` has the research.

---

## Pipeline

### `except (A, B):` stays exploded

Status: Accepted

`pipeline/extract.py` writes one tuple `except` over three lines with a trailing
comma. Single-line ones were once rewritten to `except A, B:`, which does not
compile on the Python this repo runs. It was blamed on `ruff format`, but it was
reproduced with ruff nowhere near the tree and traced to an editor watching the
directory. The gate caught every instance at `compileall` and none reached a
commit. The trailing comma stays so that no formatter collapses it again.

### The RQ worker re-execs itself on macOS

Status: Accepted

`OBJC_DISABLE_INITIALIZE_FORK_SAFETY` has to be set *before* any ObjC-linked
library is imported, and RQ's work horse forks. Setting it with
`os.environ.setdefault` inside Python is too late — measured, 22 of 22 work
horses still crashed with signal 6. `pipeline/worker.py` re-execs itself with the
variable set before importing anything else.

### The classifier fails loud on a config error and open on a transient one

Status: Accepted

A 404/401/403 means `CLASSIFIER_MODEL` is unusable and will fail identically on
every chunk forever — that exact bug once reported 22 fictional classifications
because the handler was blanket fail-open. A 429, a 5xx or a connection error is
transient, and over-processing one chunk is the cheaper mistake.

But only after the job's retries are spent. Failing open on the first 429 turned
a throttled Haiku into every chunk billed to Sonnet, which then throttles too:
the two models have separate rate limits, and failing open joined them. So a
transient error raises and RQ retries the classify job on its own queue, and
only the last attempt fails open.

---

## Serving

### The pool is sized to the server, and the server to the pool

Status: Accepted

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

### One statement cannot run for ever

Status: Accepted

Nothing bounded a query. One pathological statement holding a connection is
survivable; thirty of them is the pool, and the way to discover that is for it
to happen at three in the morning.

Thirty seconds is a safety net, not a policy — the slowest thing here by a wide
margin is `/v1/stats`' DBSCAN, measured at 1.3s on 50,000 memories
(`python -m pipeline.perf`). If that ever approaches the ceiling the answer is
to precompute hotspots, not to raise it. It binds the pipeline as well as the
API, since both share the engine in `pipeline/db.py` — nothing there comes
close today, the inserts are per row, but a bulk job that legitimately needs
longer should raise this for its own process rather than have the API carry
its ceiling.

`statement_timeout` is set on the connection rather than per query, so it
covers the queries nobody thought of as slow. Thirty seconds is a safety net,
not a policy — the slowest thing here by a wide margin is `/v1/stats`' DBSCAN
at about 1.3s on 50,000 memories (`python -m pipeline.perf`). If that ever
approaches this number the answer is to precompute hotspots, not to raise it.

### The server has one clock, and it is UTC

Status: Accepted

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

### An offset only exists when the source is a recording

Status: Accepted

`memories.timestamp_start` is seconds into a recording. That is meaningful for
a YouTube transcript and meaningless for a newspaper, a registry or a memory
somebody filed standing on the spot — and `content.source_type` is deliberately
open precisely so those can arrive.

Three places used to manufacture the number anyway. `pipeline/extract.py`
defaulted it to `0`, though `HISTORICAL_SYSTEM_PROMPT` never asks for it;
`ContentRef.timestamp_start` was a required float, so NULL could not be
expressed; and `row_to_memory` wrote `row.timestamp_start or 0` to satisfy it.
The app then rendered **"Watch at 0:00"** for anything with a content row. The
corpus was all video, so it was a lie nobody had been told yet.

The offset is optional now, and its absence is the signal: no offset, no time in
the label, and the button offers the source rather than a moment in it.

`api.gate.source_link` is the single rule — an archival `source_url` is a
document and is linked untouched, only a video takes a `?t=` offset, and only
YouTube is known to honour one. `api/card.py` had that rule right and the API
had its own diverged copy; the card's docstring claimed they matched. Now they
do, because there is one of them. Asserted in `tests/test_source_link.py`, which
is the half that had nothing — all 33 card tests pass with the rule broken.

`timestamp_end` went with it: written only when two mentions merged, read by
nothing, selected on every memory query.

### The card is rendered on the server

Status: Accepted

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

Status: Accepted

It is somebody else's site: their CSS cannot reach our map, our CSS cannot reach
their article, and their Content-Security-Policy has one origin to allow instead
of a script rewriting their DOM.

Contrast ordering matters more here than in the app — an embed is a handful of
pins on a tourism page, so the first card has to be the one worth reading.

---

## Pipeline, continued

### One tag vocabulary, not two

Status: Accepted

The extractor's prompt listed thirteen tags, `api/write.py` offered eleven for
submissions, and they overlapped on six — so the app's `sport` chip matched
none of the four memories stored as `sports`, and `m.tags && …` is an
exact-string overlap. `pipeline/tags.py` is now the one list both writers
filter against, which also makes the prompt's list binding: the model had been
emitting `comedy`, `entertainment`, `celebrity` and others off its own menu,
because nothing checked. `sports` was renamed to the singular `sport` in place
(`db/migrations/008_one_tag_vocabulary.sql`).

### Place dedup matches on names, not coordinates

Status: Accepted, amended 2026-09-23

`db/migrations/001_places_unique.sql` stopped the same exact `place_query`
minting a new row. What it cannot catch is one venue described two ways:

    [108] Gotham Comedy Club New York City           6 memories  40.75890, -73.98510
    [211] Gotham Comedy Club Chelsea New York City   1 memory    40.74310, -73.99670

**Options considered:** One venue, two pins, 1.8 km apart — and both rows claim 50 m precision, so the
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

**2026-09-23 follow-up (W4-02):** the token heuristic above has a ceiling it
cannot climb past — four of the seven merges it got wrong on live data are two
*real* venues sharing a street or neighbourhood ("Andaz West Hollywood" vs.
"Comedy Store Sunset Boulevard"), which no amount of token weighting
separates, because both names are equally "distinctive" and equally close
together. The actual fix: extraction now emits `venue`/`locality`/`region` as
structured fields (`pipeline/extract.py`'s prompts), and `save_memories` keys
its `ON CONFLICT` on an exact, case-folded match of `(venue, locality)`
(`idx_places_venue_locality`, `db/migrations/016_structured_place_fields.sql`)
instead of parsing one `place_query` string. New rows self-dedup at insert
time and never reach `pipeline/dedup.py`. That module is unchanged and still
runs — it is the only thing that can clean up the places written *before*
this migration (`venue`/`locality` NULL there), which are not being
re-extracted since that costs API credits.

18 of the heuristic's 25 proposals were reviewed and applied by hand with
`--only` (194 places → 176, memories unchanged). The 7 rejected are the useful
half, and none is a tuning problem:

| Proposal | Why not |
|---|---|
| bar French Quarter ← upscale restaurant French Quarter | two venues on one block |
| Manhattan apartment building ← Manhattan apartment | generic; plausibly two apartments |
| Irvine California ← Irvine California comedy club | a city and a venue in it are different granularities |
| New Jersey residential area ← airport gate boarding area | unrelated; the matcher failed |
| Barry Park City Hudson River ← Hudson River New York City | a park is not the river |
| Andaz West Hollywood ← Comedy Store Sunset Boulevard | two venues, one street |
| Halifax comedy venue ← Lobster Pier 7 Halifax | two venues, one city |

Merge mechanics follow `001_places_unique.sql`: repoint `memories.place_id`
first, then delete orphans guarded by `NOT EXISTS`. `memories.place_id` is
`ON DELETE CASCADE`, and an unguarded delete eats memory rows.

### The coordinates are mostly guesses, and they do not admit it

Status: Accepted

Measured 2026-09-20 on the podcast corpus: 92 of 168 placed places sit on 28
shared points, and 121 of 215 placed memories are on them. Fourteen unrelated
venues share Duffy Square in Times Square. The model emits a city centroid
whenever it does not know an address, and 35 of those stacked places still
claim `precision_meters = 50`, so "exact" and "I guessed the city" are the same
value.

| Point | Places | Memories | What it is |
|---|---|---|---|
| `POINT(-73.9851 40.7589)` | 14 | 23 | Duffy Square, Times Square |
| `POINT(-90.0715 29.9511)` | 11 | 11 | New Orleans centroid |
| `POINT(-77.0369 38.9072)` | 5 | 6 | Washington DC centroid |
| `POINT(46.6753 24.7136)` | 5 | 6 | Riyadh centroid |

**Consequences:**

- **Distance is anti-correlated with identity.** Two places on one centroid are
  usually different venues, and one venue appears at two points. Dedup matches
  names for this reason (above).
- **Structured venue fields fix matching, not placement.** Putting a pin on the
  right building needs a real geocoder, which was never built.
- **No OSM/Overpass contrast enrichment.** It assumes the coordinate is the
  place, and would confidently describe the wrong street corner. Contrast is
  scored from the source text only.
- **The gate trusts only an unshared coordinate** (under *The gate*), and
  clustering (`cluster.ts`) makes a stack readable without making it right.

```sql
SELECT ST_AsText(coordinates), count(*) FROM places WHERE coordinates IS NOT NULL
GROUP BY 1 HAVING count(*) > 1 ORDER BY 2 DESC;
```

### Channel discovery uses yt-dlp, not a scrape

Status: Accepted

**Options considered:** As of 2026-09-20 a regex over `"videoId":"..."` in the channel HTML returns zero
videos for every channel tested — YouTube no longer serves that markup to a plain
client. Rebuilding it on the internal `youtubei/v1/browse` endpoint means a lot
of undocumented JSON walking that fails silently by returning a short list.
yt-dlp is that parser, maintained weekly.

**Consequences:** `crawler/` must not import `pipeline` — `pipeline.ingest` imports it.

### Summary quality is measured, not asserted

Status: Accepted

"Improve the memory output" is unfalsifiable until the defects are counted, and
extraction costs money, so there is one chance to tell whether a prompt change
helped. `python -m pipeline.quality` prints the same four numbers before and
after. Every check was found by reading the corpus, not imagined; none is a hard
failure, they are a direction. The baseline is in [04-extract.md](04-extract.md#memory-quality).

### Markers are anchored explicitly, because the two platforms disagree

Status: Accepted

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

Status: Accepted

`cluster.ts` draws a group on a *rounded* coordinate. At the 4dp street grid
that is within ~8 m of its members and measuring to it was harmless. It stopped
being harmless when the grid started following the zoom: at 1dp a group's point
can sit kilometres from everything under it, and `reachOf` would then either
offer an unlock for something 5 km away — which the server refuses, so the
button fails in the person's hand — or hide the mechanic while they stand on it.

`reachOf` measures to the nearest *locked member*. It is the same haversine
count and it is correct at any precision.

### A tap on a wide group zooms instead of opening

Status: Accepted

Once the grid loosens, a group is two different things wearing one pin: several
memories sharing a doorway, or several places the zoom merged. The sheet pager
says "1 of 23 here", which is true of the first and a lie about the second.
`spanMeters` tells them apart — the furthest member from the drawn point, zero
at a genuine shared centroid — and past `CLUSTER_SPAN_M` the tap flies the
camera in rather than opening anything.

No `load()` alongside that `flyTo`: landing fires `onRegionChangeComplete`,
which is what fetches. Doing both is two requests for one action, the first of
them for a viewport that never exists.

## Routes

### A route is anchored on where you were, not a stored home

Status: Accepted

`daily_routes` is the first calendar-day-keyed table in this schema — see
`db/migrations/013_daily_routes.sql` — and it needed something to draw a route
*from*. The obvious answer, a saved home address, does not exist anywhere in
this product and was not worth inventing: `devices` and `users` already hold
the least this app can get away with (docs/10-decisions.md#identity), and a
home location is exactly the kind of fact a route feature could ask for
without needing at all.

So the anchor is whatever position the device sends with its preview and its
accept — the one moment it is guaranteed to have anywhere honest to stand on
— and nothing stores it. Two people planning from opposite ends of a city get
two different routes on the same day, which is correct: the route was never a
citywide itinerary, it was one device's walk.

### Preview, then accept, and the client never names a stop

Status: Accepted

The app asks how far first (F1). `GET /v1/routes/preview` solves the walk and
stores nothing; `POST /v1/routes/today` solves it again with the same anchor
and length and stores it. The two agree because the solver is deterministic:
seeded on `device:date`, fed the same candidates, the same metres and the same
budget. So the accept carries no memory ids, and there is nothing from the
client to validate or trust — a device cannot accept a stop the solver would
not have picked.

The day is locked by `ON CONFLICT (device_id, route_date) DO NOTHING`: the
first accept wins, and every later one, at any length and from anywhere, reads
that row back. One walk a day was the user's call, not a limitation.

`GET /v1/routes/today` used to be the one GET here that wrote — it made the
route on the day's first call. With an explicit accept there is nothing for it
to create, so it only reads, and answers 404 until something has been accepted.
That 404 is how a launch picks the plan page over the walk.

**The search radius is half the length.** A loop cannot reach further out than
half its length, so `budget_meters / 2` is where candidates come from. It
replaced two server knobs, `ROUTE_RADIUS_METERS` and `ROUTE_BUDGET_METERS`,
and migration 022 renamed `daily_routes.radius_meters` to `budget_meters`:
the length is what the person chose, and the radius follows from it.

### No notification when a route completes

Status: Accepted, amended 2026-09-22 and 2026-09-24

F25 ends its list of stops the same way F23 ends a seal: nothing is pushed at
anyone, as of today's code. This product had no notifications at all — see
F1's "deliberately absent" list in `docs/08-ux-flows.md` — and a route was not
going to be the first feature to need one invented. The pill just says a truer
number the next time the app is opened.

**Reopened 2026-09-22, both shipped 2026-09-23**
([a streak and a proximity notification](#a-streak-and-a-proximity-notification-after-all)): a streak counter (F27) and a geofenced
proximity notification (F28). Neither changes this section's reasoning about
the *route-complete* moment specifically — that stays a silent pill update,
reusing the existing unlock haptic rather than a push — the proximity
notification watches today's route's still-locked stops for a reason to
interrupt somebody, not the moment the route itself completes, so the two
never fire for the same reason.

**Still no push, but no longer silent** (2026-09-24): finishing a walk shows
a card, in the app, to somebody who is already looking at it. See below.

### The walk ends on a card, once, and nothing records that it did

Status: Accepted 2026-09-24

F30. Decided with the founder 2026-09-24. Each choice here is one somebody may
want to change later, so each one carries its reason:

- **A card over the map, not a page.** The accomplishment is the loop, so the
  map behind the card is the real map, fitted to the whole walk and drawn with
  the preview's own `RouteLine`. It is `WalkDone` beside `Preview` in
  `src/Plan.tsx`, the same card slot and shadow, so UI.md's two shadows stay
  two.
- **After the last memory, not over it.** The hold earns a memory, and the
  person reads it first. The card waits for that sheet to close
  (`walkDone && openAt.length === 0`).
- **The camera lets go while it shows.** `pinned` is false while `walkDone` is
  set, or the follow effect would fly straight back from the fit. Done
  pins it again.
- **Once per walk, by construction.** `walkDone` is set by the unlock that
  earns the last stop in this session, the same condition as the second
  haptic. A relaunch on a walked day starts with every stop earned and no
  unlock to set it, so it lands on the pill. Nothing is stored. Moving
  this to the server is `daily_routes.completed_at` (migration 024), and that is
  for the list of past walks, not for this.
- **Time is first unlock to last,** from the local `unlocked_at`s. It is left
  off when a stop was earned on an earlier day (a span over 12 h), because a
  stop earned yesterday still counts toward today's walk and the number would
  be days, not minutes.
- **The streak is refetched** (`fetchProfile`) when the walk ends, because the
  profile loaded at launch predates today's first unlock. It is shown only past
  one day: "1 day in a row" is not an accomplishment.
- **Metres are the planned walk,** the loop through every stop and home. They
  are not what the phone's GPS says was walked. Nothing records the track, and
  foreground-only location (UI.md rule 2) could not record it faithfully.
- **No share button.** Decided, not deferred. A screenshot of the card still
  works, and the card carries no memory text, so rule 11's credit strip has
  nothing to credit.

### Street legs stop at the stops

Status: Accepted

With `ROUTING_URL` set, stops are chosen and ordered on OSRM walking metres
(`api/streets.py`), and the line follows the streets. The distances from the
anchor are used for choosing and then dropped. The street *shapes* are stored
on `daily_routes.legs`, but only from stop to stop: a shape leaving the anchor
starts at the anchor, and would be the stored home location this section
refuses, in all but name. The preview, which stores nothing, also returns
`out_leg` and `home_leg`; the phone keeps them in its cached line beside the
start it already holds, so the whole loop follows the streets and the server
still has no start. Without the sidecar, or with it down, every
distance is crow-flies × 1.3 and `legs` is null. The route still works, it just
cuts through buildings.

### A clean loop, not the shortest one

Status: Accepted

The shortest walk through five stops often visits one down a side street and
comes back the same way: a line with spurs, drawn twice over itself. With a 20 m gate there is no passing a stop at a distance, so
the fix is choosing different stops. `_plan_route` routes the solver's walk on
the streets and measures the metres it retraces (`api/streets.py`,
`retraced_meters`). Then, up to `ROUTE_CLEANUPS` rounds, it drops each stop in
turn, re-picks, and keeps any walk with as many stops that retraces less. It
draws from `8 * ROUTE_SIZE` candidates so there is something to swap in. A
sparse area can still end with a spur; there is nothing cleaner to pick.
Without streets there is nothing to measure and the solver's walk stands.

### The walk the slider asked for, and a loop before a short one

Status: Accepted

"Shortest walk once five stops fit" gave a 6 km slider a 900 m knot on any
full map: 28% of the budget, measured over `seed_dev --dense` with
`pipeline/route_bench.py`. `_choose_walks` now ranks by count, layer mix,
**turns back on itself**, **shortfall below `ROUTE_FILL` (80%) of the
budget**, prize, then metres, in that order. The loop comes before the length
on purpose: a clean walk a little short beats a full one with a spur.

A turn back is a turn sharper than `SHARP_TURN_DEGREES` on the map itself, at
a stop or at a loop's start. That is all a straight-line map can say, and it is
what keeps a crow-flies deployment (no sidecar, Railway today) from zig-zagging
behind you and back. A street spur needs the street shapes, so the solver hands
`_plan_route` a shortlist of up to `ROUTE_SHORTLIST` walks as good on count and
mix as its best. Each is routed (~7 ms apiece; it is the `/table` that is slow),
and the one retracing the fewest `SPUR_STEP_METERS` of street wins. The
drop-a-stop cleanup still runs after it.

**Options considered:** Two estimates were tried first and dropped. An angle on *street metres* (law of
cosines on the matrix) missed the worst case: the walk home retracing the walk
out still looks like a 66° turn at the start. Shared street from the matrix,
`(d[b][a] + d[b][c] - d[a][c]) / 2` at each turn, caught that but reads a
wide turn on a street grid as overlap. Ranked above the fill, it shrank a 6 km
walk back to 14% of its budget.

Two more pieces, because ranking alone cannot build a long walk:

- **Candidates are spread, not nearest.** On a full map the forty nearest all
  sit within a few hundred metres. `_spread` reads `ROUTE_POOL` rows and keeps
  the nearest per grid cell of budget/15 first. Still forty: the MLD sidecar's
  `/table` costs ~19 ms a point, which is nearly all of a plan's ~1 s.
- **Seed walks are shaped like the ask.** For `ROUTE_HEADINGS` headings, the
  candidates nearest targets on a circle through the start that is about the
  budget round. Insertion by prize per metre still tops them up and still
  builds one walk from nothing, which is what a sparse map falls back on.

`retraced_meters` also stopped counting the part of a stub inside a stop's
gate: the line runs to the pin, but a person unlocks from 20 m out. That was
93% of what it used to call a spur.

Measured over 150 runs on `seed_dev --dense 300 --seed 1`: walk ÷ budget went
from a median 0.28 to 0.84, and spurs over 50 m from ~10% of walks to 9%, at
the same ~1.1 s. Two things only got there together. The shortlist is the best
walk plus one walk per heading, not the best walk's shake variants, which all
share the stops next to the start where the walk home overlaps the walk out.
And the circle walks respect the layer quota, or most of them fall off a
shortlist that requires the best walk's mix.

### No U-turn at a stop, and none at the start

Status: Accepted

Most of what `route_bench --scenario` still called a spur was not the solver's
choice of stops at all. It was OSRM's `foot` profile turning round at a
waypoint: walk to a mid-block pin, U-turn, walk back to the corner you came
from. Measured over `--scenario dense`, 2,074 m of the 3,700 m retraced sat
within 120 m of a stop and 1,308 m round the start.

- **`continue_straight=true`** on the `/route` call forbids the U-turn at every
  waypoint in the middle of a route. The walk goes round the block instead.
- **The start is routed as a waypoint too.** It is the route's two ends, and an
  end may turn round, so out and home left by the same corner. `streets()` in
  `_plan_route` asks for one leg more, past home to the first stop, and uses
  that last leg as the way out.
- **Round the block is longer than the table says**, so over-budget is judged on
  the routed legs, and a walk that went over is solved again for as much less
  as it overshot. Short of `ROUTE_FILL` is still read from the table: routed,
  a stub walked in and out adds metres and pays for its own spur.
- **The judge is one number**, metres off the slider plus metres retraced, not
  the fill first and spurs second. Fill first let a 6 km ask buy its length
  with a 2 km out-and-back.

Spur rate over 40 runs a scenario, before and after: dense 88% → 25%, bimodal
82% → 45%, linear 82% → 28%, one-layer 98% → 38%, stack-heavy 100% → 72%; over
50 m, 57–78% → 5–30%. Full walks fell a few points, nearly all at 1 km, where
five stops without a U-turn do not fit and the walk now says so rather than
running to 1.35 km.

### Loop or one-way, and a theme, per walk

Status: Accepted

`ROUTE_LOOP` was a server setting. The plan page now sends `loop` and an
optional `tag` with both the preview and the accept, which have to agree
because the accept re-plans rather than trusting ids. `loop` is stored on
`daily_routes`, since a walk has to be drawn the same way tomorrow and in the
Walks list; the tag is not, because the stops it chose are. `ROUTE_LOOP` is
only the default for a client that sends neither. The chips are the
submission tags, not the whole vocabulary: eighteen chips is a form, and the
server takes any tag in `pipeline/tags.py`.

---

## Product

Rules that decide what gets built at all. Moved here from TODO.md's "Decided
— do not revisit" on 2026-09-24.

### Non-goals

Status: Rejected

- Ad product (needs millions of DAU).
- Multi-city launch. Saturate one neighborhood before adding a second.
- Personal video archives as a source: GPS is already in EXIF, and people film
  the thing rather than narrate what happened there.
- Unmarked sponsored placement.
- Generic Wikipedia-grade facts as primary content.
- **A search UI.** Decided 2026-09-22: the only way to unlock a memory is to
  walk there. `/v1/memories/search` stays a typed, tested endpoint with no
  client. Its results carry no viewer position, so they cannot unlock anything,
  and what it could show open is the centroid-placed rows, the corpus's worst.
- Onboarding beyond what exists: a device id minted locally, optional
  Google/Apple sign-in, and the location primer (F8/F9). A complaint about one
  step there is a bug, not a feature.

### Core, not polish

Status: Accepted

- **Contrast scoring** decides whether the product is interesting or wallpaper.
  Rank by the gap between the memory and what is there now, not by fame.
- **Screenshot-native cards** are the only distribution channel geo-gated
  content has. Place name and attribution visible, readable at thumbnail size.
- **Layer separation.** Friend content is intimate and ephemeral, historical is
  public and permanent. Never equal weight in one feed; friend comes first.
- **Density over coverage.** One neighborhood before a second.
- **Never re-extract.** Extraction is a one-time, cached cost per place, with a
  hard cap on user-submitted ingestion.
- **Legal posture.** Snippets, attribution, deep links to the source at the
  right timestamp. Behave like a search engine. Never sell the raw corpus.

### Copenhagen first, and the podcast is test data

Status: Accepted 2026-09-20

Decided 2026-09-20. Copenhagen is the launch area. The US comedy podcast
(`Tuesdays with Stories`: 224 memories, none within 20 km of Copenhagen) stays
as end-to-end test data under its own `source_name`, and nothing on the roadmap
builds on it. The first historical source is deferred on purpose; see TODO.md's
open questions.

### Money

Status: Accepted

Near-term revenue is the historical layer: embeddable maps and delivered
corpora for tourism boards, audio-guide companies and city archives. A
consumer subscription was reopened 2026-09-22 as a second track, once there is
a userbase; it does not delay the B2B plan. The social layer earns nothing on
its own. Local-business seeded memories are a later option and must be marked.

### Warm accent, not a reskin

Status: Accepted 2026-09-22

Decided 2026-09-22, shipped 2026-09-23. The founder wanted the app to feel like
a cozy, peaceful walk. The muted-parchment palette stays, because its map
legibility and contrast work solve real problems. Only the accent moved: `seal`
went from stamp red to a warm ochre, re-measured against the same AA bar
(`mobile/UI.md`). If it does not read warm enough, revisit the accent, not the
whole palette. A second "urban" theme is parked until there is a second
neighborhood.

### A streak and a proximity notification, after all

Status: Accepted 2026-09-22

Decided 2026-09-22, against the earlier "no notifications, no streaks" rule
(`docs/11-memory-types.md`) and foreground-only location (`mobile/UI.md` rule
2). The streak is counted from `unlocks`, never stored (F27). The notification
is on-device geofencing over today's route with a local notification, no push
server, off by default (F28). Background location costs Play's
background-location declaration and a screencast review, weeks of latency,
and that was accepted because the notification cannot work without it.

### Rejected approaches, do not retry

Status: Rejected

- Scraping channel HTML for `"videoId"`: returns 0 for every channel.
- Homebrew Python 3.14: broken `pyexpat`.
- expo-router, bottom-sheet or react-query for a one-screen app.
- Shelling out to `pytest --collect-only` inside a test.
