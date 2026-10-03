# Setup

## Prerequisites

- Docker and Docker Compose
- Python 3.12 (**not** 3.14: its pyexpat is broken and breaks pip; the Dockerfile pins 3.12 for the same reason)
- Anthropic API key

## Python Environment

Use a virtual environment to avoid system package conflicts:

```bash
uv venv --python 3.12 venv  # uv's venv has no pip
source venv/bin/activate  # On Windows: venv\Scripts\activate
uv pip install --python venv/bin/python -r requirements.txt -r requirements-dev.txt
```

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `DATABASE_URL` | On Railway | PostgreSQL connection string (default: local Docker; on Railway there is none, and the API refuses to start) |
| `REDIS_URL` | No | Queue backend (default: local Docker) |
| `ANTHROPIC_API_KEY` | Yes | Claude API key |
| `EXTRACTION_MODEL` | No | Claude model (default: claude-sonnet-5) |
| `CLASSIFIER_MODEL` | No | Haiku pre-filter (default: claude-haiku-4-5) |
| `CHUNK_MINUTES` | No | Transcript chunk size (default: 4) |
| `CHUNK_OVERLAP_SECONDS` | No | Chunk overlap (default: 30) |
| `MIN_VIDEO_MINUTES` | No | Shorter videos (clips cut from episodes) are never transcribed or extracted (default: 20). Backfill old rows with `python -m pipeline.ingest --refresh-sources` |
| `TRANSCRIPT_PROXY` | No | `http://user:pass@host:port`. YouTube blocks IPs that fetch many transcripts, and cloud IPs outright. A block stops the run, rows stay pending |
| `PHOTON_URL` | No | The OpenStreetMap geocoder (default: the public `https://photon.komoot.io`, ~1 req/s). A self-hosted country extract is the same API |
| `OVERPASS_URL` | No | What stands on a pin today (default: the public `https://overpass-api.de/api/interpreter`, which rate-limits bursts). A mirror or a self-hosted Overpass is the same API |
| `WEBSHARE_PROXY_USERNAME`, `WEBSHARE_PROXY_PASSWORD` | No | Webshare **rotating residential** credentials (not datacenter: those are blocked too). Rotates IP on a block, about 400 KB a transcript. Wins over `TRANSCRIPT_PROXY` |
| `TRANSCRIPT_DELAY_SECONDS` | No | Mean jittered pause between transcript fetches (default: 1.5, which `screen` needs). A backlog drips from cron instead of bursting into a block: `0 * * * * cd <repo> && TRANSCRIPT_DELAY_SECONDS=45 venv/bin/python -m pipeline.transcripts --limit 3` |
| `ROUTE_SIZE`, `ROUTE_LOOP` | No | Today's route: how many candidates it draws from, 8 × this (default: 5; a walk aims for about one stop a km), and whether it comes back to where it started unless the request says (default: 1; `0` is one-way). The walk length is the app's slider, sent as `budget_meters`; candidates come from within half of it |
| `LAUNCH_BBOX` | No | South, west, north, east. An extracted memory pinned outside it is not saved. Default `55.60,12.45,55.74,12.66` (Copenhagen); empty means anywhere |
| `ROUTING_URL` | No | An OSRM `foot` server. Empty or down means crow-flies × 1.3 and straight lines. Local: `./osrm/build.sh` once, then `docker compose --profile routing up -d osrm` and `ROUTING_URL=http://localhost:5001` |
| `CORS_ORIGINS` | No | Comma-separated origins (default: `*`). The only lockdown knob |
| `UNLOCK_RADIUS_METERS` | No | How close you must stand to read a memory (default: 20) |
| `MEDIA_DIR` | No | Where uploads are written (default: `media`; a volume in Docker) |
| `REPORT_THRESHOLD` | No | Distinct devices needed to hide a submission (default: 3) |
| `ENABLE_EMBED` | No | `/embed` and `/embed.js`. Default on locally, off on Railway; `1` turns it on there |
| `GOOGLE_CLIENT_IDS` | For sign-in | Comma-separated audience whitelist. Empty = `/v1/auth/*` answers 503 |
| `APPLE_CLIENT_IDS` | For sign-in | Same, for Apple |
| `CONTACT_EMAIL` | Before launch | The address the privacy policy's Contact section gives, and so the app's Contact row. Unset, it says one is coming |
| `UNLIMITED_WALKS` | No | `1` lifts the one walk a day. Ignored on the public host. `docker-compose.yml` turns it on for the local API |
| `REVENUECAT_WEBHOOK_SECRET` | For subscriptions and keys | What RevenueCat's webhook sends as `Authorization: Bearer …`. Empty = `/v1/billing/revenuecat` answers 503 |
| `REVENUECAT_API_KEY` | For subscriptions and keys | RevenueCat's secret server key (not the app's public one), to read a subscriber back. Empty = `/v1/billing/revenuecat` and `/v1/me/subscription` answer 503 |

Every one is read once, in `pipeline/config.py`; add new ones there.
`RAILWAY_ENVIRONMENT_NAME`, which Railway sets itself, marks the public host:
no dev database fallback, no `/docs`, the embed off.
The app has its own, baked in at dev-server start - see `mobile/.env.example`.

Note: there is no geocoding stage. During extraction Claude names the place and
`pipeline/geocode.py` places it with free geocoders (Photon, Wikidata, no
keys); Claude's own coordinate is the fallback.

## Database

### Container
- Image: `postgis/postgis:16-3.4`
- Extensions: PostGIS for geographic queries

### Schema

Nineteen tables and a view. `db/schema.sql` is the full definition and is applied on first
container init; `db/migrations/` carries the same changes for databases that
already exist. `python -m pipeline.migrate` applies whichever is missing and
records each file in `schema_migrations`; the Dockerfile runs it before the API,
so a deploy migrates itself. A new migration must replay as a no-op, and
`tests/test_schema_layers.py` holds the two in agreement.
It also fails the gate when your dev database is missing a migration, and
names the columns.
Who writes which is in [architecture.md](architecture.md#data-ownership).

| Table | What it holds |
|---|---|
| `sources` | Where memories come from: kind, locator, `candidate → trial → active`, why. `source_yield` is the view that ranks them |
| `content` | Source videos (url, platform_id, publisher, status flags) |
| `transcripts` | JSONB segments with timestamps |
| `extraction_chunks` | Each chunk's raw model reply, keyed on the exact request |
| `classifier_verdicts` | What the Haiku pre-filter decided per chunk, and why |
| `memory_reviews` | A person's accept / edit / reject on an extracted memory. Outlives it |
| `places` | Locations with PostGIS coordinates |
| `memories` | Experiences pinned to places. `content_id` **or** `user_id`, never both |
| `devices` | An installation's self-issued UUID. Not a person |
| `users` | A display name and an id. Not an account either — yet |
| `identities` | `(google\|apple, subject)` → user. How a person proves it is them |
| `unlocks` | `(device, memory)` — who has earned what |
| `memory_hearts` | `(device, memory)` — one heart each, never taken back |
| `daily_routes` | Today's accepted walk per device, stops as an array |
| `routes` | An authored walk: title, draft\|published, loop |
| `route_stops` | `(route, position, memory)`. `daily_routes` keeps its array |
| `media` | Photos and recordings attached to a submitted memory |
| `reports` | `(memory, device)` — what makes public submissions defensible |

The four original tables are detailed below. For the rest, read `db/schema.sql`:
it is commented and it is the one copy that cannot go stale.

#### `content` table
Stores video/audio source information.

| Column | Type | Description |
|--------|------|-------------|
| id | SERIAL | Primary key |
| url | VARCHAR(1024) | Unique content URL |
| platform | VARCHAR(50) | Source platform (youtube, etc.) |
| platform_id | VARCHAR(255) | Platform-specific ID |
| source_name | VARCHAR(255) | Channel/show name |
| title | VARCHAR(512) | Content title |
| published_at | TIMESTAMP | Publication date |
| transcript_fetched | BOOLEAN | Transcript fetch status |
| transcript_failed | BOOLEAN | Transcript fetch failed |
| memories_extracted | BOOLEAN | Extraction status |
| extraction_failed | BOOLEAN | Extraction failed |

#### `transcripts` table
Stores fetched transcripts with timing.

| Column | Type | Description |
|--------|------|-------------|
| id | SERIAL | Primary key |
| content_id | INTEGER | FK to content |
| segments | JSONB | Timestamped segments |
| full_text | TEXT | Concatenated text |
| language | VARCHAR(10) | Detected language |

#### `places` table
Stores geographic locations.

| Column | Type | Description |
|--------|------|-------------|
| id | SERIAL | Primary key |
| name | VARCHAR(512) | Human-readable name |
| place_query | VARCHAR(512) | Search string for geocoding |
| coordinates | GEOGRAPHY | PostGIS point |
| precision_meters | INTEGER | Location precision |
| geocode_status | VARCHAR(20) | pending/success/failed |

#### `memories` table
Stores extracted memories.

| Column | Type | Description |
|--------|------|-------------|
| id | SERIAL | Primary key |
| place_id | INTEGER | FK to places |
| content_id | INTEGER | FK to content |
| timestamp_start | REAL | Seconds into the recording. NULL for a submission and for any source that is not a recording |
| summary | TEXT | Memory description |
| tags | VARCHAR(50)[] | Category tags |
| extraction_confidence | VARCHAR(20) | high/medium/low |

## Project Structure

See [repository-map.md](repository-map.md).

## Startup Commands

```bash
# Start database
docker compose up -d

# Verify database is ready
docker compose exec db pg_isready -U memorylane

# Setup Python environment (first time only)
uv venv --python 3.12 venv
source venv/bin/activate
uv pip install --python venv/bin/python -r requirements.txt

# Run pipeline stages (with venv activated)
python -m pipeline.ingest       # Poll the active sources
python -m pipeline.transcripts  # Fetch YouTube transcripts
python -m pipeline.extract      # Extract memories with coordinates

# Score the summaries - run before and after any prompt change
python -m pipeline.quality

# Or run all stages
python -m pipeline.run_all

# Start API
uvicorn api.main:app --reload --port 8000
```

## Common Tasks

### Add new videos
1. Find and judge the source in `sources` (`python -m pipeline.sources list`):
   `discover` or `add` it, `screen` it (Haiku, about a cent), then either
   `python -m pipeline.ingest --video <url> --to <id>` for one trial episode, or
   `set <id> active` (with `poll_limit`) to have ingest poll the channel.
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

### Useful queries
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
