# Claude Code Guide

Quick reference for AI agents working on this codebase.

## Project Overview

**Memory Lane** extracts location-based memories from video transcripts and makes them queryable by geographic proximity.

Pipeline: `Content URLs → Transcripts → LLM Extraction (with coords) → Query API`

## Before you finish: run the gate

Two things verify this project and they answer different questions. The gate
says the rules are right; `./e2e/run.sh` says the product works, by driving the
real app on a simulator. The gate is the one you must not leave red.

One trap worth knowing: `./loop/verify.sh | tail` reports `tail`'s exit status,
not the gate's. Check `$?` on the gate itself, or a red gate reads as green.

```bash
./loop/verify.sh     # 0 GREEN | 1 RED (fix it) | 2 INFRA (needs a human)
```

It runs compileall, ruff check + format --check, pytest, and the app's
typecheck. If it reports RED because of formatting:

```bash
venv/bin/python -m ruff format .
```

Style is not a matter of taste here - `pyproject.toml` decides and the gate
enforces. Don't hand-align anything.

### Then log the friction

Every session, before the last commit: add to `TODO.md` § **Friction** anything
that cost this session real time or nearly shipped something wrong. The aim is
clean code, speed, understandability, and a repo an agent can work in without
tripping. Be strict:

- **In:** it will happen again to the next person or agent, and there is a
  concrete fix. A stale doc, a slow loop, a trap in the tooling, code that took
  two readings, a fake that lies.
- **Out:** one-offs, your own slips, anything already logged (sharpen that
  entry instead), and a problem you fixed in the same session.
- **Shape:** one entry each. What happened, dated, what it cost, and the fix
  in one line. No entry beats a vague one.

If nothing qualifies, add nothing.

## Quick Start

```bash
# Start database + Redis
docker compose up -d

# Setup Python (first time)
python3 -m venv venv && source venv/bin/activate && pip install -r requirements.txt

# Run pipeline (one command)
source venv/bin/activate
python -m pipeline.run_all

# Or run stages individually
python -m pipeline.ingest
python -m pipeline.transcripts
python -m pipeline.extract

# Run pipeline (scaled/parallel with workers)
python -m pipeline.ingest
python -m pipeline.transcripts
python -m pipeline.enqueue --all       # Queue videos for extraction
python -m pipeline.worker              # Start worker (run multiple in separate terminals)

# Seed memories you can actually reach (the real corpus has none nearby)
python -m pipeline.seed_dev          # --clear removes them
python -m pipeline.seed_dev --dense 300 --seed 1   # plus a full map for the route to choose from
python -m pipeline.seed_dev --routes bimodal   # one route scenario alone, all in Copenhagen: sparse, dense, bimodal, linear, one-layer, stack-heavy, lakes

# Start API server
python -m api.main
# or: uvicorn api.main:app --reload
```

## Key Files

| File | Purpose |
|------|---------|
| `pipeline/run_all.py` | **Run full pipeline** in one command with `--dry-run`, `--skip-*` options |
| `crawler/yt_crawler.py` | **Channel discovery** via yt-dlp — lists a channel's videos + metadata |
| `pipeline/ingest.py` | Loads video URLs from `config/content.yaml` into DB (expands `channel:` sources) |
| `pipeline/transcripts.py` | Fetches YouTube transcripts via youtube-transcript-api |
| `pipeline/extract.py` | **Core logic** - Claude extracts memories + coordinates (sequential) |
| `pipeline/tasks.py` | RQ tasks for parallel extraction with Haiku pre-filter |
| `pipeline/worker.py` | RQ worker entry point for scaled extraction |
| `pipeline/enqueue.py` | CLI to queue videos for parallel processing |
| `pipeline/queue.py` | Redis/RQ queue setup |
| `pipeline/quality.py` | **Score the summaries.** Run before and after any prompt change; `--compare` scores a candidate prompt against the current one on the same chunks |
| `pipeline/classifier_audit.py` | Re-extract a sample of chunks the pre-filter rejected; counts what it drops. Bills |
| `pipeline/review.py` | **Review extractions by hand.** Accept/edit/reject; `--stats` is the edit rate |
| `pipeline/seed_dev.py` | **Memories you can walk to.** The real corpus has none near any dev coordinate |
| `pipeline/tags.py` | The one tag vocabulary. Both write paths filter against it |
| `pipeline/dedup.py` | Propose place merges; `--only` applies a reviewed subset |
| `pipeline/perf.py` | **Time the read path on a corpus this size isn't.** Run before and after touching `api/queries.py` |
| `pipeline/route_bench.py` | **How the route does on a full map.** Every plan setting rolled at random; spurs, stops, walk vs budget, `fresh` (another roll, another walk), ms, over `seed_dev --dense`. Needs `ROUTING_URL`; `--solvers` needs nothing and scores the solver against brute force |
| `pipeline/sweep.py` | Reap uploads no submission ever claimed. Describes unless `--apply` |
| `pipeline/db.py` | Database connection (SQLAlchemy + psycopg3) |
| `pipeline/config.py` | **Every env knob**, read once. Add new settings here |
| `api/main.py` | The app: CORS, the media mount, and the router includes. 60 lines |
| `api/models.py` | Every shape the API accepts or returns |
| `api/queries.py` | Every SQL string. `tests/test_api_sql.py` EXPLAINs them all |
| `api/gate.py` | row → Memory, redacted unless you are standing there |
| `api/read.py` | The read endpoints |
| `api/route_solver.py` | **Today's walk.** Which stops, what order; its docstring is how a walk is ranked |
| `api/write.py` | Unlock, media, submissions, reports |
| `api/accounts.py` | `/v1/me` and `/v1/auth/*` |
| `api/card.py` | The server-rendered card. Gates itself; see below |
| `api/embed.py` | The embeddable map. Off when `ENABLE_EMBED=0` |
| `api/streets.py` | Walking metres and street shapes for today's route, from OSRM. Crow-flies × 1.3 without it |
| `api/media.py` | What an upload is allowed to be, and where it lands |
| `api/auth.py` | Google and Apple ID tokens: the three checks, and why each one |
| `api/test_api.sh` | API test script (run with `./api/test_api.sh`) |
| `e2e/run.sh` | **Watch the flows happen.** Drives the real app on a simulator; `--record` leaves an mp4 |
| `.maestro/` | Three journeys covering the ids in `docs/08-ux-flows.md`. Read `e2e/README.md` before writing one |
| `tests/test_flows.py` | The same six journeys headless, so a red flow can be attributed |
| `db/schema.sql` | PostgreSQL + PostGIS schema |
| `db/migrations/` | One-off SQL for databases that already exist |
| `pyproject.toml` | Ruff config. `./loop/verify.sh` enforces it |
| `config/content.yaml` | Content sources to process |
| `mobile/App.tsx` | Plan → preview → walk: one map, only today's stops on it, the pill recentres |
| `mobile/src/Plan.tsx` | **How far today.** The slider page and the preview card with Accept |
| `mobile/src/MemorySheet.tsx` | The memory detail sheet — locked and open are two compositions |
| `mobile/src/UnlockButton.tsx` | Hold-to-unlock: the ring, the haptics |
| `mobile/src/MemoryMarker.tsx` | One pin, lit when it can be opened from here |
| `mobile/src/unlocked.ts` | What this device has earned. Cached locally, authoritative on the server |
| `mobile/src/RouteLine.tsx` | The route drawn: ink over a paper casing, still. Why still: docs/09 §3a |
| `mobile/src/route.ts` | What this device's daily walk looks like. Cached, server-authoritative, resets at midnight |
| `mobile/src/Submit.tsx` | **The only screen that writes.** Photo, voice, tags, and why there is no map picker |
| `mobile/src/SignIn.tsx` | Google and Apple buttons. Neither works in Expo Go |
| `mobile/src/MemoryMedia.tsx` | A submitted memory's photo and its recording |
| `mobile/src/region.ts` | Viewport -> API radius maths (unit tested) |
| **`mobile/UI.md`** | **Read before touching the app.** Tokens, the spacing/radius/shadow scale, measured contrast, load-bearing rules, how to see it running |
| **`docs/08-ux-flows.md`** | **What the user does.** Implemented + proposed flows |
| **`docs/10-decisions.md`** | **Why the code is shaped this way.** Read before "fixing" something odd |
| `docs/09-visual-design.md` | Why the app looks the way it does, what was rejected, and why the web card does not match it yet |
| `docs/11-memory-types.md` | What a memory is and isn't, layer vs. tag vs. confidence, and the pin guardrails to check before decorating one further |

## Database Tables

```
content       → Source videos (url, platform_id, publisher, status flags)
transcripts   → JSONB segments with timestamps
extraction_chunks → Each chunk's raw model reply, keyed on the exact request
classifier_verdicts → What the Haiku pre-filter decided per chunk, and why
memory_reviews → A person's accept / edit / reject on an extracted memory. Outlives it
places        → Locations with PostGIS coordinates
memories      → Experiences pinned to places. content_id OR user_id, never both
devices       → An installation's self-issued UUID. Not a person
users         → A display name and an id. Not an account either — yet
identities    → (google|apple, subject) → user. How a person proves it is them
unlocks       → (device, memory) — who has earned what
routes        → An authored walk: title, draft|published, loop
route_stops   → (route, position, memory). daily_routes keeps its array
media         → Photos and recordings attached to a submitted memory
reports       → (memory, device) — what makes public submissions defensible
```

**There are no session tokens anywhere, signed in or not.** `devices` is an
opaque UUID the app generates for itself and keeps in the keychain; the server
never issues one, and it is the only credential — it travels in the request
body, so anybody holding yours can act as you. Same threat model as the unlock's
self-reported position.

Signing in does not change that. Google and Apple hand the app an **ID token**;
the server verifies it (`api/auth.py`) and binds `devices.user_id`. Every
endpoint keeps working unchanged, and a second phone becomes a second device on
one user — which is the whole of what sign-in buys, and why nothing else needed
inventing to get it.

Google and Apple **only**. No passwords: nothing to store, reset, rotate or
leak, and no reset-email flow. Apple is required by App Store review as soon as
any other third-party sign-in exists on iOS, so it is not a preference either.

Two rules in that code are load-bearing and easy to get wrong:

- **Audience is checked.** A valid Google token issued to somebody else's app is
  still a valid Google token. With `GOOGLE_CLIENT_IDS`/`APPLE_CLIENT_IDS` unset
  there is nothing to check against, so `/v1/auth/*` answers **503** rather than
  verifying against nothing.
- **Emails never link accounts.** `identities.email` is recorded and never
  matched on. An address can be reassigned, and Apple's may be a relay.

What survives what, because this is the question that matters and the answer is
not uniform:

| | Survives app data cleared | Survives reinstall | Survives a new phone |
|---|---|---|---|
| Local copy (AsyncStorage) | no | no | no |
| Device id (keychain) | yes | usually | no |
| Server unlocks | yes, via the id | usually | no |

Key queries:
```sql
-- Check pipeline status
SELECT transcript_fetched, memories_extracted, COUNT(*) FROM content GROUP BY 1, 2;

-- See extracted memories with coordinates
SELECT m.summary, p.name, ST_AsText(p.coordinates)
FROM memories m JOIN places p ON m.place_id = p.id;

-- Places the extractor could not place. `pipeline/geocode.py` used to print
-- this and geocoded nothing; it was deleted.
SELECT geocode_status, COUNT(*) FROM places GROUP BY 1;

-- Find nearby memories (within 10km of the dev seed)
SELECT m.summary, p.name, ST_Distance(p.coordinates, ST_MakePoint(12.57586, 55.67886)::geography) as dist_m
FROM memories m JOIN places p ON m.place_id = p.id
WHERE ST_DWithin(p.coordinates, ST_MakePoint(12.57586, 55.67886)::geography, 10000)
ORDER BY dist_m;
```

## Environment

Required: `ANTHROPIC_API_KEY`

Optional (with defaults):
- `DATABASE_URL` = postgresql://memorylane:memorylane@localhost:5432/memorylane
- `REDIS_URL` = redis://localhost:6379/0
- `EXTRACTION_MODEL` = claude-sonnet-5
- `CLASSIFIER_MODEL` = claude-haiku-4-5 (for pre-filtering chunks)
- `CHUNK_MINUTES` = 4
- `CHUNK_OVERLAP_SECONDS` = 30
- `MIN_VIDEO_MINUTES` = 20 (shorter videos - clips cut from episodes - are never
  transcribed or extracted; backfill old rows with `python -m pipeline.ingest --refresh-sources`)
- `TRANSCRIPT_PROXY` = empty (`http://user:pass@host:port`; YouTube blocks IPs that
  fetch many transcripts, and cloud IPs outright. A block stops the run, rows stay pending)
- `TRANSCRIPT_DELAY_SECONDS` = 1.5 (mean jittered pause between transcript fetches)
- `CORS_ORIGINS` = `*` (comma-separated; the only lockdown knob for a public API)
- `UNLOCK_RADIUS_METERS` = 20 (how close you must stand to read a memory)
- `MEDIA_DIR` = `media` (where uploads are written; a volume under Docker)
- `REPORT_THRESHOLD` = 3 (distinct devices needed to hide a submission)
- `ROUTE_SIZE` = 5, `ROUTE_LOOP` = 1 (today's route: how many stops, and
  whether it comes back to where it started unless the request says; `0` is
  one-way). The walk length
  is the app's slider, sent as `budget_meters`; candidates come from within
  half of it)
- `ROUTING_URL` = empty (an OSRM `foot` server. Empty or down means
  crow-flies × 1.3 and straight lines. Local: `./osrm/build.sh` once, then
  `docker compose --profile routing up -d osrm` and `ROUTING_URL=http://localhost:5001`)
- `GOOGLE_CLIENT_IDS`, `APPLE_CLIENT_IDS` = empty (comma-separated audience
  whitelists. Empty means sign-in is off and `/v1/auth/*` answers 503)

## Architecture Notes

### LLM Extraction (`pipeline/extract.py` - Sequential)
- Transcripts split into 4-min chunks with 30s overlap
- Claude extracts: place_name, place_query, lat, lng, summary, tags, confidence
- Coordinates come directly from LLM (no external geocoding API)
- Low confidence memories filtered out
- Nearby same-place memories merged (within 60s)

### Scaled Extraction (`pipeline/tasks.py` - Parallel)
Two-stage extraction with Redis queues:
1. **Classify (Haiku)**: Quick check if chunk has location memories (~$0.0001/chunk)
2. **Extract (Sonnet)**: Full extraction only for chunks that pass filter (~$0.003/chunk)

```
Video → Chunks → [Haiku Classifier] → [Sonnet Extractor] → Aggregator → DB
                        ↓ skip                  ↓
                  (no memories)          (parallel workers)
```

Run multiple workers for parallel processing:
```bash
# Terminal 1-N: Start workers
python -m pipeline.worker

# Or size each queue on its own: Haiku and Sonnet have separate rate limits
python -m pipeline.worker classify   # x2
python -m pipeline.worker extract aggregate   # x4

# Check status
python -m pipeline.enqueue --status <content_id>
```

### Mobile app (`mobile/`)
Expo + react-native-maps. A plan page, a preview, one map that shows only
today's accepted walk, and one detail sheet; the routes endpoints feed it
(`/v1/routes/preview`, `POST`/`GET /v1/routes/today`). Before changing it read
**`mobile/UI.md`** for the design tokens and the constraints that are
load-bearing (never blank or a dead end, foreground-only location), and
**`docs/08-ux-flows.md`** for the flows it has to satisfy.

```bash
cd mobile && npm run typecheck                   # also run by the gate
cd mobile && npx expo start --ios                # see it (UI.md has the recipe)
```

### API (`api/main.py`)
FastAPI server with PostGIS proximity queries:
- `GET /v1/memories/nearby?lat=X&lng=Y&radius_km=10&tags=food,travel&min_confidence=medium` - Find memories near location (tags and confidence optional)
  - Gated memories always come back locked here, with no summary, tags or source.
    This endpoint never unlocks. See "Proximity unlock" below.
- `GET /v1/memories/search?q=coffee&lat=X&lng=Y&radius_km=50` - Full-text search across summaries and place names (location optional)
- `GET /v1/memories/{id}?at_lat=X&at_lng=Y` - Get single memory, gated
- `POST /v1/memories/{id}/unlock` `{device, lat, lng}` - **the unlock.** Same gate,
  and the only route that records one. POST because it creates something
- `GET /v1/unlocks?device=UUID` - that device's collection, always unlocked
- `GET /v1/routes/preview?device=UUID&lat=X&lng=Y&budget_meters=4000&loop=true&tag=food` - the walk
  of that length from there would be: up to five stops. Stores nothing.
  `budget_meters` is 1000–10000; `loop` defaults to `ROUTE_LOOP`, `tag` (one of
  `pipeline/tags.py`) keeps only stops carrying it; `again` is "Show me
  another" (F32), another walk as good
- `POST /v1/routes/today` `{device, lat, lng, budget_meters, loop?, tag?, again?}` - accept it. The
  same solve, stored; one per device per day, and a second accept gets the
  first walk back. The client never sends stop ids
- `GET /v1/routes/today?device=UUID` - today's accepted walk, or 404. Only reads
- `GET /v1/routes/walked?device=UUID` - every walk the account accepted,
  newest first: earned stops open, `earned` of `size`, `completed_at`
- `GET /v1/routes/{id}` - an authored walk: its stops in order, locked like
  today's. 404 while it is a draft. Nothing writes these yet but SQL
- `POST /v1/memories` `{device, lat, lng, place_name, summary, tags, ...}` -
  **file your own memory.** One coordinate: it is both where you are and where
  the memory goes. Lands in the `stranger` layer, gated like everything else,
  and records the unlock for the person who filed it
- `POST /v1/media` (multipart: `device`, `file`, optional `duration_seconds`) -
  a photo or a recording, held until a submission claims it. `api/media.py`
  decides what a file may be; see **Uploads** below
- `POST /v1/memories/{id}/report` `{device, reason}` - REPORT_THRESHOLD distinct
  devices and the memory stops being served by every endpoint
- `GET /v1/me?device=UUID` / `PUT /v1/me` `{device, display_name}` - the name a
  submission is signed with, plus which sign-ins are attached. The GET creates
  nothing
- `POST /v1/auth/google` / `POST /v1/auth/apple` `{device, id_token,
  display_name?}` - verify a provider ID token and bind this device to that
  account. `display_name` is for Apple, which gives the name to the client once
  and never again
- `POST /v1/auth/signout` `{device}` - unlink the device. Deletes nothing, and
  there is no token to revoke
- `GET /v1/places/nearby?lat=X&lng=Y&radius_km=10` - Get places with memory counts
- `GET /v1/stats` - Database statistics
- `GET /docs` - Swagger UI

Test the API:
```bash
./api/test_api.sh                    # Test local server
./api/test_api.sh http://host:port   # Test custom URL
```

### Uploads
Three things never come from the client: the filename, the extension, and the
claim about what the bytes are. The extension is looked up from `ALLOWED` by the
declared type, the declared type has to match the file's first bytes, and the
stored name is a fresh uuid. Files are served by `NoSniff`, a `StaticFiles`
subclass that sets `X-Content-Type-Options`, because the extension is what
decides the Content-Type on the way back out and "HTML that says it is a PNG" is
the whole attack. `MEDIA_DIR` is a named volume in `docker-compose.yml`; without
it a rebuild deletes everybody's submissions.

### Proximity unlock
Only memories you are standing near are readable. The gate is in `row_to_memory`
(`api/main.py`), not in an endpoint, so every memory-shaped response is redacted
by the same code — `/v1/memories/search` and `/v1/places/nearby`'s
`sample_memory` reach the same rows and would otherwise be side doors.

`api/card.py` renders HTML and cannot use `row_to_memory`, so it gates itself —
if you add another route that emits a summary, it is a hole until you do the
same.

An extracted memory is gated only when no other place shares its coordinate. 121
of 215 placed memories sit on city centroids the model emitted when it did not
know the address, and locking those would ask somebody to walk to a fiction.

A **submitted** memory is always gated: it was filed from the phone of somebody
standing there, so there is no centroid problem to protect anyone from. The
other half of that rule is load-bearing — each submission mints its own place
row, so `COORDINATE_IS_UNIQUE` excludes places carrying one. Without that,
filing a memory outside Katz's puts a second place in the grid cell and unlocks
Katz's for everybody. A gate anybody could open by posting next to it.

Full reasoning in `docs/08-ux-flows.md` F7 and F5; assertions in
`tests/test_api_unlock.py` and `tests/test_api_submit.py`.

### Memory Quality
The summary is the product: somebody standing on the spot, on a phone, outdoors.
Measure before and after any prompt change — extraction costs money and you get
one shot:

```bash
python -m pipeline.quality
python -m pipeline.quality --compare candidate.txt   # same 10 chunks, both prompts, side by side
```

Baseline on the 224-memory corpus, all four found by reading it rather than
guessing, and all four now addressed in `SYSTEM_PROMPT`:

| | | |
|---|---|---|
| anonymous subject | 55% | "The speaker drove the van…" instead of the name |
| talks about talking | 20% | "He describes…" reports the recording, not the event |
| not past tense | 12% | "He's playing the Fillmore on the 14th" is a ticket ad |
| over 70 words | 32% | a summary of the conversation, not of what happened |

The prompt now bans the labels outright, rejects upcoming shows as hard as it
rejects hypotheticals, asks for 2–3 sentences, and carries three worked examples
taken from the corpus's own failures. It is structured with XML tags, gives
explicit permission to return nothing, and is sent as a cached block — it is
~1.2k tokens resent for every chunk, and a cached read costs 10% of input.

**None of it has been run against real credits** (the account balance is empty),
so the numbers above are still the current state.

- WHO: Use names ("Mark and Joe" not "the hosts")
- WHAT HAPPENED: Anecdotes, funny moments, mishaps
- THE VIBE: Emotions, humor, what made it memorable

### PostGIS
- Coordinates stored as `GEOGRAPHY(POINT, 4326)`
- Use `ST_DWithin()` for proximity queries
- Index: `idx_places_coordinates` (GIST)

## Common Tasks

### Add new videos
1. Edit `config/content.yaml` — either list URLs under `videos:`, or add a
   `channel:` (plus optional `limit:`) to auto-discover a channel's back catalogue.
   Both can be combined; ingest merges and dedups them.
2. Run `python -m pipeline.ingest`
3. Run `python -m pipeline.transcripts`
4. Run `python -m pipeline.extract`

### Reset and reprocess a video
```sql
UPDATE content SET memories_extracted = FALSE, extraction_failed = FALSE WHERE id = X;
DELETE FROM memories WHERE content_id = X;
-- Then run extract again. Chunks whose request is unchanged are read back from
-- extraction_chunks for free; add this to pay for them again:
-- DELETE FROM extraction_chunks WHERE content_id = X;
```

### Check extraction quality
```sql
SELECT m.summary, p.name, m.extraction_confidence, m.tags
FROM memories m JOIN places p ON m.place_id = p.id
ORDER BY m.id DESC LIMIT 10;
```

## Testing Tips

- **There is no `--limit` flag.** `python -m pipeline.extract` runs
  `extract_all_pending()` and bills every pending video. To spend a few cents
  instead, extract one video through the queue path:
  `python -m pipeline.enqueue --video <content_id>` (then `--status <id>`).
- The extraction prompt is in `extract.py:SYSTEM_PROMPT` - tweak for better results
- Check `geocode_status` column: 'llm' means coordinates from extraction, 'pending' means missing

## Not Yet Implemented

- [x] `api/main.py` - FastAPI endpoint for proximity queries
- [x] `api/test_api.sh` - API test script
- [x] `pipeline/run_all.py` - Run full pipeline in one command
- [x] Deduplication across videos - *exact* `place_query` match only
      (unique index + `ON CONFLICT`). Near-duplicates like "Oslo Norway" vs
      "comedy club Oslo Norway" still make separate places.
- [x] Clustering nearby memories on map view - zoom-banded grid in `cluster.ts`
- [x] Full-text search across memory summaries
- [x] User-submitted memories, with photo and audio
- [x] Google/Apple sign-in, so a collection survives a new phone
- [x] A daily guided route - F25, `GET /v1/routes/today`
- [ ] Rate limiting / authentication for API
