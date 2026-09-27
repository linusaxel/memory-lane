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

### A locked memory says what it is, not what it says

Status: Accepted 2026-09-26

The map's peek (F29) needs a reason to walk, and a place name alone is not
one. So a locked memory now carries its tags, its source's name (the archive's
`attribution`, else the channel) and its year. `api/gate.py` `locked_memory`.
The summary, the media, every link and the timestamp stay behind the gate, and
`tests/test_api_unlock.py` holds that.

Decided 2026-09-27: the peek shows the title and no stand-in for the text, so
`summary_words`, which drew the summary as grey bars, is gone from the API too.

**Options considered:** a blurred summary is the obvious peek and is a leak:
the text reaches the phone and a blur is a style. The bars were drawn from a
count, so there was nothing to un-blur, and then they were dropped as noise.
A full date was left out for the year: enough to say "1944", not enough to
find the story in an archive by date.

### The position is self-reported

Status: Accepted

This stops `curl`, not a determined spoofer — and since submissions, it cuts
both ways: a memory is also filed at a position nobody verified. Attestation is
the fix and needs more than accounts. Logged in `TODO.md`.

### Every memory is public

Status: Accepted (2026-09-26)

A memory can be read by anyone who stands at it. Nobody chooses who that is,
and no memory is held back until a date. The time capsule (F23, "Nobody until"
a year) is removed from the app, the API and the gate: `not_yet_open`, the
route and geofence exclusions, the sealed card, and the 423 on edit are all
gone. The founder chose to ship it this way for now. The proximity gate
stands, and it is the only lock.

`memories.opens_at` stays in the schema with nothing reading or writing it.
Dropping it would mean rewriting migration 009, which the migration-replay test
replays on its own. A memory sealed before the removal now reads like any
other.

**Options considered:** Hiding the "Who can read it" field and keeping the
server half. That leaves a gate branch nothing can reach and a feature the docs
would still have to explain.

### A map of what is locked, and only today's walk unlocks

Status: Accepted 2026-09-26. Supersedes the "no map of everything" clause below.

After sign-in the app opens on a map of the locked memories around you (F29),
and a walk is how you open any of them. A corpus you can browse is a corpus you
can finish, but locked pins cannot be browsed: nothing on them is readable
until you stand there on today's walk. So the rule the old clause protected
survives unchanged: `POST /v1/memories/{id}/unlock` still refuses any memory
that is not a stop of today's walk, and the peek has no unlock in it even
standing on the pin.

**Amended 2026-09-26: and what you filed.** The founder filed a memory and
never found it on the map, because filing opens it for you and the map drew
locked ones only. Your own pins are drawn too, open: they are where you left
them, not a corpus to browse, and every other open memory stays off the map.

### Only today's walk unlocks

Status: Accepted (2026-09-24). Replaces "Unlocking is Walk-only, and only the
app knows it". The "no map of everything" clause is **Superseded 2026-09-26**
by the entry above; the unlock rule stands.

The app is one walk at a time (one a day until 2026-09-26, *A walk can be
ended*), five stops, and nothing else: ~~no map of everything
(F29 is gone), because a corpus you can browse is a corpus you can finish.~~ So
`POST /v1/memories/{id}/unlock` refuses with 403 any memory that is not a stop
of today's `daily_routes` walk in progress for this account (`ON_TODAYS_ROUTE_QUERY`),
however close you stand.

The old decision kept this in the client because a "which tab" flag would be
as self-reported as the position. The route is not self-reported: the server
chose it and stored it on accept, and the client names at most one stop, which
the server vets (*Preview, then accept*). That is
what makes the rule enforceable here and not there.

Filing still opens its own memory for its author: that unlock is written by
`POST /v1/memories`, not by this endpoint. It no longer extends the streak
(F27), or the limit could be dodged by posting. Position is still self-reported,
so a spoofed GPS walks today's five from a sofa, and no more than five.

### A subscription opens the map

Status: Accepted 2026-09-26. Amends *Only today's walk unlocks* and *A walk
can be ended*; the gate is untouched.

The founder's monetisation: a walk is free and opens its stops; opening a pin
straight from the map, with no walk, is what a subscription buys. You still
stand on it: `SUBSCRIBED_QUERY` relaxes `ON_TODAYS_ROUTE_QUERY` in the unlock,
never the 20 m.

Walk here plans a walk through any pin and End walk frees the day, so on
their own they would open any pin for free in two taps and leave nothing to
sell. So the day lock is back, per account and for free accounts only
(`WALKED_TODAY_QUERY`, refused 403 `walked_today` at preview and accept). Its
old cost, a bad plan or rain spending the day, is kept small: an ended walk
that opened nothing is deleted (`ROUTE_PRUNE`), so it never counted.

**Consequences:** `subscriptions` is on the account, not the device, so an
unbound device (the dev-build Skip) is never subscribed. Only the store's
webhook may write it, never the app: a client-side entitlement is a
client-side gate (TODO.md S3). Until then nothing writes it and everybody is
free. A subscriber with a spoofed GPS opens every pin from a sofa, not five:
they have paid, and the position was always self-reported.

### RevenueCat sells it; our table decides

Status: Accepted 2026-09-27 (the founder's pick of the two in TODO.md S3).

RevenueCat takes both stores' purchases, renewals, refunds and grace periods
behind one SDK and one webhook, and is free until $2.5k a month of revenue.
Talking to the App Store Server API and the Play Developer API direct is free
for ever and roughly twice the code, in two integrations that break
separately. Launch is both platforms, monthly and yearly, no trial.

What stays ours is the only thing that opens anything: `subscriptions`. Three
rules keep it honest (`api/billing.py`):

- **RevenueCat's `app_user_id` is `users.id`.** The app calls `logIn` with the
  account id, so the webhook names a user we know. A device with no account
  (the dev-build Skip) is nobody to RevenueCat and cannot buy.
- **The event body is a doorbell, not a fact.** Every event reads the
  subscriber back from RevenueCat's REST API and makes the row match: an
  entitlement `map` with its `expires_date`, or no row. Duplicate, late and
  out-of-order events cannot leave a wrong row, and purchase, renewal, refund
  and expiry are one code path.
- **The app is never believed.** A purchase in the app calls
  `POST /v1/me/subscription`, which does the same read-back, so the unlock a
  second later is not waiting on the webhook. It cannot claim anything the
  store did not say.

**Consequences:** the webhook is the first endpoint here with a credential
other than a device id: a shared secret in `Authorization`, compared in
constant time, and 503 when unset (as `api/auth.py` does for sign-in). An
unknown `app_user_id` is answered 200 and ignored, or RevenueCat retries it
for days. `accounts.absorb` carries the row to the account it merges into,
keeping the longer. An entitlement with no end date (a promotional grant from
the dashboard) is stored as the year 9999.

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

### The title is the place name

Status: Accepted (2026-09-26)

A submission's Title is stored as its own place's `name`. Each submission
mints its own place (above), so the name was already per-memory. It was
already the card's heading, locked or not, and it was already required. A
`memories.title` column would have needed a migration, and extracted memories
would then have needed a title too, either from a fallback or a prompt change.
Extracted memories keep their place name as the heading.

**Options considered:** A title beside the place name: two headings for one
card, and one more field on a form the founder asked to shrink.

### Tags come from the text, and a walk has no theme

Status: Accepted 2026-09-26. Supersedes the submission half of *One tag
vocabulary, not two* and the theme in *Loop or one-way, and a theme, per walk*.

The founder: tags the way X does them. A person writes `#food` in the
description and that is the tag; the submit form has no Tags picker, and
`POST`/`PUT /v1/memories` take no `tags` field (an old app's is ignored).
`pipeline/tags.py`'s `from_text` reads them: `#` then letters, digits or `_`,
lowercased, at most eight. The app draws the same words highlighted in the text
(`mobile/src/hashtags.ts`), and `tests/fixtures/hashtags.json` holds the two
parsers to the same answers. Open, not closed: `#smørrebrød` is a tag. The
closed list stays for the extractor, which has no author to write hashtags;
its tags are kept and shown nowhere but the locked peek.

With open tags there is nothing fixed to theme a walk on, so the theme went
too: no chips on the plan page, no `tag` on `/v1/routes/preview` or
`/v1/routes/today`, and `SUBMISSION_TAGS` is gone from both ends.

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

### Sign-in comes first, and it is the whole onboarding

Status: Accepted 2026-09-26, built the same day (F22). Supersedes "Sign-in is
never a gate" (`mobile/UI.md`, `docs/08-ux-flows.md`) and the onboarding
non-goal below.

The founder's call: no account, no app. The first screen is Apple and Google
and nothing else, then the location primer (F8/F9), then the map. No carousel,
no name or email form: both providers hand over what little a profile needs.

What does not change: sign-in still binds the device (*No session tokens*
above), the device id stays the only credential, and emails are still never
matched on. The anonymous-absorb path stays for devices from before the gate.

**Consequences:** nothing can be tried before signing in, so the one screen has
to earn the tap on its own. Neither button works in Expo Go, so development and
`./e2e/run.sh` need a way past the gate that a release build cannot take: a
**Skip (dev build)** button under `__DEV__`, which Metro strips from a release
bundle. A button rather than an `EXPO_PUBLIC_DEV_*` knob, because `e2e/run.sh`
blanks every such knob and a button lets e2e drive the gate. The gate lives in
the client only; the server still serves an unbound device, which is what keeps
the anonymous-absorb path working.

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

Status: Superseded 2026-09-27

There is no font gate any more: the app's one font is the system's (see "One
font, the map's"). The replay from `onMapReady` stays, since the native map can
still be ready after a mount effect fires.

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

### The classifier passes history, not only first-hand experience

Status: Accepted (2026-09-27)

The pre-filter asked for "a PERSONAL EXPERIENCE at a SPECIFIC PHYSICAL PLACE"
while the extraction prompt already took "an event, a mishap, something that
stood here". So a 1943 sabotage at a named factory was rejected as "a factual
historical account", and every archive and text source screened at 0.00. It now
asks for what the extractor asks for: something that already happened at a
named place, first-hand or as history. Announcements and listings stay out.

`max_tokens` went from 100 to 300 with the same change: 48 of 297 stored
verdicts were a reason cut off mid-sentence, which fails open, so one chunk in
six reached Sonnet unjudged.

Measured by replaying 195 stored chunks through both prompts at 300 tokens:
unparseable replies 16% → 0; Historisk Atlas 0 → 5 of 6; KB notices stay 0 of 6;
Københavnerglimt 4 → 23 of 23 (Denmark's first film screening on Halmtorvet,
Kierkegaard dying at Frederikshospitalet); Københavnerliv 24 → 25 of 30. The 6
flips down were all right (botany, colour theory, cycling plans). The cost is
more Sonnet on history-heavy sources, some of it on places outside Copenhagen
(Greenland colonies in a Christianshavn lecture) that the judge has to drop.

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

`not_yet_open` (the time lock, since removed: *Every memory is public*) asked
Python for today's date, which is the host's local one.
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

Status: Accepted; the submission half **Superseded 2026-09-26** by *Tags come
from the text, and a walk has no theme*. The extractor still filters against
the one list.

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
  right building needs a real geocoder. Denmark has one now (*DAWA places
  Danish addresses*, below); everywhere else still has only the model's guess.
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

### Sources are a Protocol and a registry

Status: Accepted 2026-09-26

More text sources are coming (TODO.md § *Data sources*), and each should be one
file. `crawler/sources.py` defines `Record` (the dict `ingest_records` already
took) and `Source` (`name`, `source_name`, `source_type`, `fetch(query, limit)`),
plus `SOURCES`, one line per source. `python -m pipeline.ingest --source <name>
--query <q>` runs any of them.

**Options considered:** a base class or a plugin loader: both are more to read
for nothing a dict does not do. Folding YouTube in: it lists videos now and
fetches transcripts later, so it would need a second stage the interface does
not have. Revisit when a second source is two-stage.

**Consequences:** a source only fetches; it never touches the database. A source
that brings its own coordinates (Historisk Atlas) writes them into the text for
the model's `lat`/`lng`, so a geocoder hit can still move the pin. If pins land
off the atlas's point, `Record` grows `lat`/`lng` and `content` a column.

### Sources are rows with a status

Status: Accepted 2026-09-27. Replaces `config/content.yaml`.

A source is anything that yields a story tied to a spot: a channel, a
searchable archive, a book, an institution. Each is a row in `sources` with a
status, `candidate → trial → active`, or `paused` / `rejected` with the reason
in `note`. `content.source_id` points back, and the `source_yield` view ranks
them by memories per hour and by the Haiku pass rate (`screened`). The app's
own people are one extra row in that view, as the baseline.

The funnel is `pipeline/sources.py`: `discover` (YouTube search over Copenhagen
neighbourhoods; a hit counts only if it is long and its title names the place),
`screen` (Haiku on three items, about a cent, nothing to Sonnet), then a person
decides. A trial is one item: `ingest --video … --to <id>`, then `enqueue`.
Only `active` channels are polled. A candidate's or rejected source's items are
in `content` so they can be screened, and `PENDING_EXTRACTION` skips them, so
`enqueue --all` never bills a whole candidate.

**Options considered:** Keeping the YAML: it could hold a channel list but not
a status, a yield, or the TODO.md prose about why a source was dropped, and
discovery would have to write to a checked-in file. A column on `content`:
a candidate has no content yet.

**Consequences:** the seed rows are in both `db/schema.sql` and
`db/migrations/029_sources.sql`. A fresh database loses the hand-listed videos
that were in the YAML; re-add one with `ingest --video`. The first discovery run
(46 candidates, 2026-09-27) found local TV and local-history archives rather
than storytellers: the vein to screen first. Screening rejected Kend Din By at
0 of 8 chunks: silent archive film.

### DAWA places Danish addresses

Status: Superseded 2026-09-26 by *The LLM names the place; free geocoders place
it*, below. DAWA is now one national plug-in in that chain, and the `aa` → `å`
rule became the model's job (`address` in today's spelling).

The historical prompt asks for `address`, the street and number as the source
wrote them. For a Danish place, `pipeline/geocode.py` asks DAWA
(`api.dataforsyningen.dk`, free, no key) and a hit replaces the model's
coordinate, with `geocode_status = 'dawa'`. The model picks which place; DAWA
says where it is.

Two traps, both measured against the live API on 2026-09-26:

- **`fuzzy` always answers.** "Nonexistentgade 999" came back as Vestergade 9 in
  Nibe. A hit only counts if its street name is the one asked for (after
  `aa` → `å`).
- **Copenhagen renumbered its houses in 1859.** "Gothersgaden 330" in an 1856
  paper came back as Gothersgade 130; 330 today is another building. A pre-1859
  or undated number gives a street-level pin (200 m), never `exact`.

**Options considered:** `datavask`, which grades its own match: it graded
everything tested `C`, including the nonsense street.

**Consequences:** new extractions only; existing places keep their model
coordinates until a backfill earns its place. A miss or a network failure keeps
the model's coordinate, which is what happened before.

### The LLM names the place; free geocoders place it

Status: Accepted 2026-09-26

The model reads a messy transcript and decides *which* place is meant
("Vega, Copenhagen"); it is bad at *where*. GPSBench (arXiv 2602.16105): under
25% city-level accuracy for every model, though ~80% of misses still get the
country. Our own corpus: 93 of 361 model-placed places share a point.

So `save_memories` hands `address`, `venue`, `locality` and `country` to
`pipeline/geocode.py:place()`, which asks a chain of free geocoders, anywhere:

| Geocoder | What it knows | Licence |
|---|---|---|
| DAWA | Danish addresses (`country == "DK"` only) | Danish public data, free |
| Photon (`PHOTON_URL`) | OpenStreetMap: addresses and venues worldwide | Free; public server ~1 req/s, self-host a country extract for more |
| Wikidata | Notable places, including closed ones (CBGB) | CC0 |

Every one of them answers almost anything, so one guard judges them all, with
the trap each rule exists for (all found live, 2026-09-26):

- **The name must match** (`difflib` ≥ 0.85, street for an address, name for a
  venue). Photon answered "Blaagaardsgade 12" with Moltkes Palæ.
- **A city is not a place.** Photon put CBGB, closed in 2006, on the centre of
  New York. Refused, and Wikidata answers instead.
- **Within 25 km of the model's guess.** The model gets the city right when it
  gets the street wrong; that is what catches a same-name place elsewhere.
- **Precision comes from what matched, not from the model.** A house number
  before 1900 is street-level: cities renumbered (Copenhagen in 1859).

No surviving hit keeps the model's coordinate as `'llm'`. `geocode_status`
records which geocoder placed a pin: `dawa`, `photon`, `wikidata`.

Amended 2026-09-27, after the first Danish extraction (content 534) left 14 of
20 places on the model's guess, most of them on Photon under a slightly
different name:

- **A venue's name matches loosely.** Brackets and generic words (café, bar,
  bodega, pub, restaurant, the) are dropped and spaces ignored, so "Under
  Hylden" is "Café Under Hylden" and "Nørrebro Parken" is "Nørrebroparken". A
  POI's name may also sit inside the venue's ("Fri BikeShop Nørrebro" is "Fri
  BikeShop"), never the reverse: "Nørrebrogade" is not "Nørrebrogade Pizza".
- **A street without a number comes after the venue.** It is a guess along the
  whole street; the venue, if the map has it, is a point.
- **One venue is one place, across localities.** The model named Under Hylden's
  locality Frederiksberg once and Copenhagen twice. `save_memories` joins a
  place with the same venue within 10 km unless both are 50 m points (two
  of those apart are a chain), and a better placing replaces the stored one.
  New extractions only; `pipeline/dedup.py` is still the tool for old rows.

**Options considered:** Google keeps coordinates for 30 days and only on a
Google map; Mapbox's cheap tier forbids storing; HERE and TomTom cache 30 days.
We store coordinates forever, so all are out. Nominatim's public server
discourages bulk use. OpenCage allows storage but is €45/month past testing;
Geoapify's free tier is the fallback if Photon's public server stops serving us.

**Consequences:** OpenStreetMap's licence
([geocoding guideline](https://osmfoundation.org/wiki/Licence/Community_Guidelines/Geocoding_-_Guideline))
lets us store its geocodes with no share-alike on our other data, on condition
of credit. One line in Settings → About does it ("Places © OpenStreetMap
contributors", linking to its copyright page): the
[attribution guidelines](https://osmfoundation.org/wiki/Licence/Attribution_Guidelines)
ask the application to credit OSM, not each result. Geocoding costs
no tokens and saves none either: coordinates are ~20 output tokens a memory.

### Summary quality is measured, not asserted

Status: Accepted

"Improve the memory output" is unfalsifiable until the defects are counted, and
extraction costs money, so there is one chance to tell whether a prompt change
helped. `python -m pipeline.quality` prints the same four numbers before and
after. Every check was found by reading the corpus, not imagined; none is a hard
failure, they are a direction. The baseline is in [04-extract.md](04-extract.md#memory-quality).

### A memory must need its spot

Status: Superseded by [A memory is decided before it is written](#a-memory-is-decided-before-it-is-written).
`why_here` came after the summary in the schema, so the model wrote the story and
then justified it: the Kansas ski-bar story came back with a reason attached.

The reader is standing on the pin, so a story that could be pinned anywhere is
worth nothing to them. The first Copenhagen video showed this: a third of its
memories were nickname origins, ski trips and "he still lives on this street",
pinned to venues the model had invented because the prompt told it to "guess a
real, specific venue name even when unsure".

Two parts, because a rule the model only reads leaks ("a pub crawl is not a
venue" was in the prompt and it still returned "Nørrebro pubcrawl" twice):

- The schema requires `why_here`, one line on what the spot adds. An empty one
  is dropped in `filter_low_confidence`. It is not stored: it exists to make
  the model answer the test, not to be shown.
- `location_precision: city` is dropped there too. A 10km pin is not a spot.

Neighborhood (1km) stays: a park is legitimately that wide.

### A memory is decided before it is written

Status: Accepted

Three changes, each because a prompt rule alone had leaked on real output:

- **The decision comes first in the schema.** Claude fills fields in schema
  order, so with `venue` first it committed to a place and wrote the story before
  anything asked whether the place mattered. Now `place_words` (the transcript's
  own words for the place), `happened_there` and `spot_test` come before
  `venue`, and only `spot_test: pass` is kept.
- **The quote is checked in code.** `grounded()` drops a memory whose
  `place_words` are not in the chunk, with case, spaces and punctuation
  ignored because captions mangle names. It can't catch a real name used for
  the wrong story: "Levinho" is in the transcript. That is what `spot_test` is for.
- **Every chunk gets a brief of the whole video.** A chunk is four minutes. The
  crawl is introduced in minute one and Nørrebroparken comes up in minute 33, so
  the summary said "the pub crawl" to a reader with no idea which one.
  - `video_brief()` makes one call per video, stored in `extraction_chunks` at
    index -1. It names the events and people, and deliberately not the places:
    when it listed bars, a chunk pinned one bar's story to another bar's name.
  - This is Anthropic's contextual-retrieval pattern.

The merge also changed. It concatenated two summaries at one venue, which glued
two stories into 110-word cards. Now it keeps the first telling of one story, and
keeps different stories apart by word overlap (`_same_story`).
2026-09-27: the 60-second window it also required is gone. Café Woodstock's
raid was told at 3:07 and again at 4:14, 0.36 overlap, and came out as two
memories. Distinct stories at one place overlap 0.07 at most on the corpus.

`location_precision: city` is still dropped. A 10km pin is not a spot, and a park
at 1km is.

On one video, over six runs:
- the stories where the place was incidental went from about 7 of 18 to about 1 in 11;
- the invented ski bar and the crawl-named venues went to none;
- every run keeps Ringkaféen, Under Hylden, Maskot and Nørrebroparken.

What still leaks about once a run is a biography fact (where Maleren lives) and
"the crawl" without its name. The research's next steps, in order, are thinking at
low effort and then a separate yes/no judge per memory.

### A story has to be worth telling

Status: Accepted

Grounding a story to its spot doesn't make it interesting. "Maskot is where the
crawl always starts; a few drinks go down here" is true, named and on the spot,
and nobody would stop walking for it. Two parts of the pipeline pushed toward
producing something:
- The chunk message said "Extract memories", which implies there are some.
- Each chunk was judged alone, so a routine stop never competed with the bar
  that sank into a stream.

`worth_telling()` makes one Sonnet call per video over every candidate that
survived the grounding filters, and answers six yes/no questions for each:
- `only_here`: the swap test
- `breach`: it departs from the script
- `consequence`
- `visible_now`
- `so_what`
- `stands_alone`

These come from what the storytelling and editorial literature agrees on:
- Labov's reportability, and Bruner and Baroni on a breached script.
- Harcup and O'Neill's news values.
- Tilden and Ham's "so what".
- Atlas Obscura, and VoiceMap's stops.

Four choices shape how it works:
- **Yes/no, not a score.** Scores out of 10 are poorly calibrated, and a rubric
  of binary answers with anchors holds (Stureborg et al., Prometheus). The
  model answers; `tellable()` holds the bar in code.
- **A bar, not a top N.** Editors bar first and fit what passes. A quota would
  pad a dull video, and a dull video giving nothing is correct.
- **No brief.** The judge reads as a stranger does, so `stands_alone` means
  something.
- **It only filters.** An unreadable or unavailable judge keeps everything.

It is cached at `chunk_index = -2` like the brief.

**Tuned against labels, not intuition.** 16 stories from video 534 were labelled
keep or drop by hand.
- The first judge, with a bar of 3 of the 4 optional criteria, agreed on 12.
  Origin stories like Nørrebroparken have consequence and a point but break no
  script, so the bar is now 2 (`TELLABLE_MIN`).
- The same story, judged twice, flipped: Under Hylden passed, then failed.
  `JUDGE_PASSES = 3` runs are shown the candidates in different orders and take
  the majority, which also cancels position bias. A tie drops.
- The result is 15 of 16, and 10 of the 11 that are not close to a rubric
  example. The one miss is Lundtoftegade, where the founder lives.
- Across three full runs, no labelled "drop" survived. Each run kept 4–5
  memories, down from 9–11.

### One venue, one name per video

Status: Accepted 2026-09-27

Each chunk names its venue on its own, and `save_memories` matches
`(venue, locality)` exactly. Content 535 named Jørgen Leth's barber three ways
("Barbershop on Vognmagergade", "Herrefrisør på Vognmagergade", "Jørgen Let's
barbershop, Vognmagergade"), so one shop got three pins.

After the judge, `one_name_per_venue()` makes one call per video with two or
more distinct venues. It sends each venue with its first story and asks which
of them are the same place. Each duplicate takes the name of the one to keep.
The model only picks among the given names, so it can't invent one. A failed
reply changes nothing.

Rejected:
- Naming venues in the brief. `BRIEF_PROMPT` leaves places out, because a place
  listed there gets pinned to stories that happened elsewhere.
- `pipeline/dedup.py`'s token rule. The three names share only the street, and a
  street-only match would also fold "Mexibar, Nørrebrogade" into any other bar
  on Nørrebrogade. Only something that reads the stories knows a herrefrisør is
  a barbershop.

**Consequences:** one more cached call per video. Across videos, the same venue
under two names still makes two rows (`dedup.py` covers the cases it can).

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

### Preview, then accept, and the client names at most one stop

Status: Accepted, amended 2026-09-26

The app asks how far first (F1). `GET /v1/routes/preview` solves the walk and
stores nothing; `POST /v1/routes/today` solves it again with the same anchor
and length and stores it. The two agree because the solver is deterministic:
seeded on `device:date`, fed the same candidates, the same metres and the same
budget. So the accept carries no memory ids, and there is nothing from the
client to validate or trust — a device cannot accept a stop the solver would
not have picked.

**Amended 2026-09-26: at most one, and the server vets it.** "Walk here" on a
pin (Map first, M5) sends `include=<memory_id>` with the preview and the accept.
It is vetted by the same `ROUTE_CANDIDATES_QUERY` that decides every other stop:
the query sorts it first, and if it is not first it may not be a stop (hidden,
already earned, ambiguous, or beyond half the length). A pin too far
from a street, or whose walk there and back is longer than the slider, is also
refused, 422 for all of them; the last says the length that would reach it
(`too_far`, `min_budget_meters`), which the app lifts its slider to (M6). The solver then keeps it on every walk it
considers, and the cleanup never drops it. ~~The theme does not filter it out: a
pin somebody chose outranks the chip.~~ (There is no theme since 2026-09-26.) Seeding does not change, so preview and
accept still agree, and the client still cannot place a stop the rules forbid.

~~The day is locked by `ON CONFLICT (device_id, route_date) DO NOTHING`: the
first accept wins, and every later one, at any length and from anywhere, reads
that row back. One walk a day was the user's call, not a limitation.~~
**Superseded 2026-09-26** by *A walk can be ended, and another planned*,
below: the first accept still wins, but only until the walk is ended.

`GET /v1/routes/today` used to be the one GET here that wrote — it made the
route on the day's first call. With an explicit accept there is nothing for it
to create, so it only reads, and answers 404 until something has been accepted.
That 404 is how a launch picks the plan page over the walk.

### A walk can be ended, and another planned

Status: Accepted (2026-09-26). Supersedes the day lock in *Preview, then
accept*, and settles Map first M7 and M9 (TODO.md history).

The founder's call: one walk a day made a bad plan, or a walk cut short by
rain, the whole day's. **End walk** ends today's walk at any point, and the map
comes back with Plan a walk on it. The rule is now one walk *in progress* per
device, not one a day. **Amended 2026-09-26** by *A subscription opens the
map*: one free walk a day per account again, but ending one that opened
nothing gives the day back.

- `daily_routes` gains `ended_at` and an `id`, and `(device_id, route_date)` is
  a partial unique index over rows not ended (migration 027). Accept still
  writes with `ON CONFLICT ... DO NOTHING` against it, so two accepts racing
  still store one walk.
- `POST /v1/routes/today/end` sets `ended_at`. ~~The row is kept, not
  deleted: the journal lists the walk (F31), and the streak joins unlocks to
  walks (F27), so deleting it would take a day's streak with it.~~
  **Superseded 2026-09-26** by *A walk that opened nothing is deleted*: kept
  only if it opened something, which is all the streak ever joined on.
- An ended walk's unearned stops lock again: `ON_TODAYS_ROUTE_QUERY` and the
  completion check read only the walk in progress. What was opened stays open.
- The app asks first when stops are left ("End this walk?", an in-app card:
  the app raises no system dialog). A walked walk ends without asking, since
  nothing is lost.

Pause ("Resume walk") was the other option in M9, and the smaller change; it
kept the day lock, which is what the founder wanted gone. M7 (a pin tapped
during a walk) has no case left: off-route pins are hidden on a walk, and
after ending one, Walk here plans the next.

A walk planned again the same day is seeded the same (`device:date`), so the
same ask can give the same stops; the app rolls `again` afresh for every plan,
which is what varies it.

**The search radius is half the length.** A loop cannot reach further out than
half its length, so `budget_meters / 2` is where candidates come from. It
replaced two server knobs, `ROUTE_RADIUS_METERS` and `ROUTE_BUDGET_METERS`,
and migration 022 renamed `daily_routes.radius_meters` to `budget_meters`:
the length is what the person chose, and the radius follows from it.

### A walk that opened nothing is deleted

Status: Accepted (2026-09-26). Supersedes "the row is kept" in *A walk can be
ended, and another planned*.

The founder's call, from the UI pass: the journal keeps only walks that
unlocked something, and a walk that opened nothing is not kept hidden either,
because a hidden row is data left lying about.

- Deleting is safe because nothing depended on an empty row. The streak
  (`STREAK_DAYS_QUERY`) joins unlocks to that day's walk, so a walk with no
  unlock never counted. Nothing has a foreign key to `daily_routes`.
- `ROUTE_PRUNE` deletes this device's walks with no stop the account ever
  unlocked, except today's walk in progress. It runs when a walk ends, and
  when a walk is accepted, which sweeps a past day's walk that was never
  ended.
- It counts a reported (hidden) memory's unlock; the journal does not. The
  streak counts that unlock, so the row stays, and the journal leaves the walk
  out rather than list it as having opened nothing.
- `WALKED_QUERY` filters the same way in SQL, so today's walk stays out of the
  journal until its first unlock and `LIMIT` counts only walks it lists. The
  journal row says what the walk opened ("5 memories"), never "3 of 5".

### No notification when a route completes

Status: Accepted, amended 2026-09-22 and 2026-09-24

F25 ends its list of stops quietly: nothing is pushed at
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

### About a stop a km, five at least

Status: Superseded by [About a stop a km, from the first](#about-a-stop-a-km-from-the-first)

Five stops on the shortest street legs between them cannot fill a long
slider: `route_bench` gave walk ÷ budget 0.63 at 6 km, 0.55 at 8 and 0.33 at
10 on `seed_dev --dense`. The solver was not what fell short. On
`--routes lakes` the longest five-stop loop from Olufsvej, brute-forced, is
7.0 km, and it found 6.9 at a 9.1 km ask; ranking the fill above sharp turns
changed nothing. `_route_size` now aims for `max(ROUTE_SIZE, round(km))`, a
rule of thumb: a sparse map still gets fewer.

Measured over 140 runs on the dense seed: 8 km 0.55 → 0.76, 10 km 0.33 →
0.56, up to 5 km unchanged. The cost is time and some spurs: 10 km p50/p95
went from 344/890 ms to 663/2171 ms, and spurs over 50 m at 8-10 km from
10-19% to 25-38% (±22% noise at 16-20 runs a row). `_walking_order` is exact
only to six stops now, 2-opt above, because 8! orderings per walk scored took
seconds.

A long ask still falls short where the map runs out. The lakes top out at
7.4 km for any stop count: shortest legs cross the bridges, where the ~9 km
walk is the shore. Only legs longer than the shortest path would fill it.

### About a stop a km, from the first

Status: Accepted

The floor of five made every walk up to 5 km ask for five stops, so a 1 km
walk wanted as many as a 5 km one. `_route_size` is now `ceil(km)`, at least
one: 1 km is one stop, 4 km four, 10 km ten. `ceil`, not `round`, because the
slider steps half a km and `round` gives 2.5 → 2 but 3.5 → 4. It is still a
ceiling; a sparse map gets fewer. `ROUTE_SIZE` stays as the candidate pool's
scale (`8 * ROUTE_SIZE`) and the themed walks' size.

### Stops spread along the walk, before filling the slider

Status: Accepted

The founder saw stops bunch together. Stage 1 now counts bunched legs
(`_bunched`: a leg, out and home included, under half the walk split evenly)
and ranks the fewest just after sharp turns, ahead of the shortfall under
ROUTE_FILL and the prize. `route_bench` reports `gap`, the shortest leg over
the mean one. Over 140 runs on the dense seed, gap p50 went 0.43 → 0.50: 8 km
0.28 → 0.42, 10 km 0.27 → 0.35. Walk ÷ budget went 0.81 → 0.80 and spurs did
not move, within the ±8% noise. Ranked after the shortfall instead, 10 km
did not move at all: its walks fall short, so the shortfall decides first.

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

### A walk that doesn't cross itself

Status: Accepted

A loop drawn as a figure of eight reads as lost. The judge could not see one:
it adds no retraced metres, and the chords between stops do not cross even
when the streets do (a leg overshooting past the next stop, the way home
cutting back across it). On a street graph two legs cross at a shared corner,
so `crossings` (`api/streets.py`) counts corners the path comes back to on two
streets it has not walked. A spur walks the same street back, so it stays
`retraced_meters`', and a corner inside a stop's gate or the start's is where
legs meet.

Stage 2 adds `CROSSING_METERS` (300) a crossing to the one-number judge, a
walk as good must cross no more than the best, and the drop-a-stop cleanup
runs on a crossing as it does on a spur. A penalty rather than a rank of its
own, for the reason the turn-back one was: shape above the fill shrinks walks.

`route_bench` reports `cross`. Over 100 runs: `--scenario dense` 7% → 0%, and
the DB's seed map at 2-4 km 31-75% → 0%; walk ÷ budget, spurs and time within
noise. At 6-10 km on that map it did not move: `fresh` is 0%, there is one
walk to pick, and its way home already retraces the way out.

### Loop or one-way, and a theme, per walk

Status: Accepted; the theme **Superseded 2026-09-26** by *Tags come from the
text, and a walk has no theme*.

`ROUTE_LOOP` was a server setting. The plan page now sends `loop` ~~and an
optional `tag`~~ with both the preview and the accept, which have to agree
because the accept re-plans rather than trusting ids. `loop` is stored on
`daily_routes`, since a walk has to be drawn the same way tomorrow and in the
Walks list; ~~the tag is not, because the stops it chose are.~~ `ROUTE_LOOP` is
only the default for a client that sends neither. ~~The chips are the
submission tags, not the whole vocabulary: eighteen chips is a form, and the
server takes any tag in `pipeline/tags.py`.~~

### A one-way walk can end where you tap, and nothing stores it

Status: Accepted

"End at the subway": on **One way**, the plan page can take a spot tapped on
the map, and the preview and the accept both send it (`end_lat`/`end_lng`,
`end`). Like the start it is stored nowhere, not on `daily_routes` and not as
a preference, or it is the stored home that *A route is anchored on where you
were* turned down; the phone keeps it next to the start (`mobile/src/route.ts`).
The solver takes it as a loop's home: column 0 of the matrix is metres to the
end, so ordering, insertion and the routed last leg walk there unchanged.
Candidates come from within half the length of the midway point, and a walk
that cannot reach the end is `too_far`. Picked on the map, not searched by
name: no geocoder in the app, and it works anywhere.

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
- ~~Onboarding beyond what exists: a device id minted locally, optional
  Google/Apple sign-in, and the location primer (F8/F9). A complaint about one
  step there is a bug, not a feature.~~ **Superseded 2026-09-26** by
  *Sign-in comes first, and it is the whole onboarding*.

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

Status: Accepted 2026-09-26. Supersedes the entry below.

The founder's call: a consumer subscription is probably the most realistic
revenue, so it is the lead track, not the second one. The historical layer
still sells to tourism boards, audio-guide companies and city archives
(embeddable maps, delivered corpora), alongside it. No pricing, tier or
paywall is decided; nothing is built yet. The social layer earns nothing on
its own. Local-business seeded memories are a later option and must be marked.

~~Near-term revenue is the historical layer: embeddable maps and delivered
corpora for tourism boards, audio-guide companies and city archives. A
consumer subscription was reopened 2026-09-22 as a second track, once there is
a userbase; it does not delay the B2B plan.~~ **Superseded 2026-09-26.**

### Warm accent, not a reskin

Status: Superseded 2026-09-27 by *Friendly, not sharp*

~~Decided 2026-09-22, shipped 2026-09-23. The founder wanted the app to feel like
a cozy, peaceful walk. The muted-parchment palette stays, because its map
legibility and contrast work solve real problems. Only the accent moved: `seal`
went from stamp red to a warm ochre, re-measured against the same AA bar
(`mobile/UI.md`). If it does not read warm enough, revisit the accent, not the
whole palette. A second "urban" theme is parked until there is a second
neighborhood.~~ **Superseded 2026-09-27.** It did not read warm enough, and
the shape and type were the bigger half of why.

### One font, the map's

Status: Accepted 2026-09-27

The founder saw three faces on one screen: Fraunces on the walk card, Figtree
on its buttons and SF Pro in the map's street names, which `react-native-maps`
cannot restyle on iOS. Five variants were compared on the simulator, and the
app now uses **SF Pro Rounded** everywhere (`'ui-rounded'` in
`mobile/src/theme.ts`). It is the map's family and it is round, so it is still
friendly, and there is nothing to bundle or load. Android falls back to Roboto,
the map's face there. The web card (`api/card.py`, `api/embed.py`) still uses
Fraunces and Figtree. Supersedes the type bullet of "Friendly, not sharp".

### Friendly, not sharp

Status: Accepted 2026-09-27

The founder: the app was not fun or friendly, the colours clashed and the
buttons were too sharp. Paper and a serif stay; everything else that read as
an instrument went (`docs/09-visual-design.md` part 8 has the research):

- **One accent, `ember`, for a memory and the way to it**: every pin, the next
  stop, the preview line, the primary button. `brand` teal and `route` blue are
  gone; blue is the map's and your location dot's. Part 7's proposal, shipped.
- **`seal` is bright gold**, not ochre: ember beside the ochre collapsed to one
  colour under protanopia. Gold is a fill, never text.
- **Capsules and soft corners**: buttons are 52pt pills, cards over the map 28,
  fields 14. Supersedes "corners are 4px".
- **Soft Fraunces + Figtree**, still two families (superseded by "One font,
  the map's"). IBM Plex Mono and the
  uppercase label voice are gone; supersedes "Fraunces + Plex Mono".
- **Liquid Glass on the map controls only** (`expo-glass-effect`), paper and
  one soft shadow where it is unavailable. Supersedes "elevation is a rule, not
  a shadow" for things over the map; sheets stay flat.

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
