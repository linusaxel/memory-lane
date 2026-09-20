# Claude Code Guide

Quick reference for AI agents working on this codebase.

## Project Overview

**Memory Lane** extracts location-based memories from video transcripts and makes them queryable by geographic proximity.

Pipeline: `Content URLs → Transcripts → LLM Extraction (with coords) → Query API`

## Before you finish: run the gate

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
| `pipeline/geocode.py` | Utility to check geocoding stats (coords come from LLM) |
| `pipeline/db.py` | Database connection (SQLAlchemy + psycopg3) |
| `pipeline/config.py` | **Every env knob**, read once. Add new settings here |
| `api/main.py` | FastAPI server for location-based memory queries |
| `api/test_api.sh` | API test script (run with `./api/test_api.sh`) |
| `db/schema.sql` | PostgreSQL + PostGIS schema |
| `db/migrations/` | One-off SQL for databases that already exist |
| `pyproject.toml` | Ruff config. `./loop/verify.sh` enforces it |
| `config/content.yaml` | Content sources to process |
| `mobile/App.tsx` | The map screen: pins, banner, "Near me" |
| `mobile/src/MemorySheet.tsx` | The memory detail sheet — locked and open are two compositions |
| `mobile/src/UnlockButton.tsx` | Hold-to-unlock: the ring, the haptics |
| `mobile/src/MemoryMarker.tsx` | A coordinate's four states on the map |
| `mobile/src/unlocked.ts` | What this device has earned. On-device only; there are no accounts |
| `mobile/src/region.ts` | Viewport -> API radius maths (unit tested) |
| **`mobile/UI.md`** | **Read before touching the app.** Tokens, load-bearing rules, how to see it running |
| **`docs/08-ux-flows.md`** | **What the user does.** Implemented + proposed flows |
| `docs/09-visual-design.md` | Why the app looks the way it does, and what was rejected |

## Database Tables

```
content       → Source videos (url, platform_id, status flags)
transcripts   → JSONB segments with timestamps
places        → Locations with PostGIS coordinates
memories      → Extracted experiences linking content to places
```

Key queries:
```sql
-- Check pipeline status
SELECT transcript_fetched, memories_extracted, COUNT(*) FROM content GROUP BY 1, 2;

-- See extracted memories with coordinates
SELECT m.summary, p.name, ST_AsText(p.coordinates)
FROM memories m JOIN places p ON m.place_id = p.id;

-- Find nearby memories (within 10km of a point)
SELECT m.summary, p.name, ST_Distance(p.coordinates, ST_MakePoint(-73.9857, 40.7484)::geography) as dist_m
FROM memories m JOIN places p ON m.place_id = p.id
WHERE ST_DWithin(p.coordinates, ST_MakePoint(-73.9857, 40.7484)::geography, 10000)
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
- `CORS_ORIGINS` = `*` (comma-separated; the only lockdown knob for a public API)
- `UNLOCK_RADIUS_METERS` = 150 (how close you must stand to read a memory)

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

# Check status
python -m pipeline.enqueue --status <content_id>
```

### Mobile app (`mobile/`)
Expo + react-native-maps. One map screen, one detail sheet, one endpoint
(`/v1/memories/nearby`). Before changing it read **`mobile/UI.md`** for the
design tokens and the constraints that are load-bearing (blank maps fail store
review, foreground-only location, 400ms debounce, radius-only API), and
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
- `GET /v1/memories/{id}?at_lat=X&at_lng=Y` - Get single memory. This is the unlock read
- `GET /v1/places/nearby?lat=X&lng=Y&radius_km=10` - Get places with memory counts
- `GET /v1/places/{id}` - Get single place details
- `GET /v1/places/{id}/memories` - Get all memories for a place
- `GET /v1/content/{id}/memories` - Get all memories from a video
- `GET /v1/stats` - Database statistics
- `GET /docs` - Swagger UI

Test the API:
```bash
./api/test_api.sh                    # Test local server
./api/test_api.sh http://host:port   # Test custom URL
```

### Proximity unlock
Only memories you are standing near are readable. The gate is in `row_to_memory`
(`api/main.py`), not in an endpoint, so every memory-shaped response is redacted
by the same code — `/v1/memories/search` and `/v1/places/nearby`'s
`sample_memory` reach the same rows and would otherwise be side doors.

Only a coordinate no other place shares is gated. 111 of 186 placed memories sit
on city centroids the model emitted when it did not know the address, and
locking those would ask somebody to walk to a fiction. Full reasoning in
`docs/08-ux-flows.md` F7; assertions in `tests/test_api_unlock.py`.

### Memory Quality
Summaries should be vivid and personal, not generic. The prompt instructs Claude to include:
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
-- Then run extract again
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
- [ ] Clustering nearby memories on map view
- [x] Full-text search across memory summaries
- [ ] Rate limiting / authentication for API
