# Setup

## Prerequisites

- Docker and Docker Compose
- Python 3.12 (**not** 3.14: its pyexpat is broken and breaks pip; the Dockerfile pins 3.12 for the same reason)
- Anthropic API key

## Python Environment

Use a virtual environment to avoid system package conflicts:

```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `DATABASE_URL` | No | PostgreSQL connection string (default: local Docker) |
| `REDIS_URL` | No | Queue backend (default: local Docker) |
| `ANTHROPIC_API_KEY` | Yes | Claude API key |
| `EXTRACTION_MODEL` | No | Claude model (default: claude-sonnet-5) |
| `CLASSIFIER_MODEL` | No | Haiku pre-filter (default: claude-haiku-4-5) |
| `CHUNK_MINUTES` | No | Transcript chunk size (default: 4) |
| `CHUNK_OVERLAP_SECONDS` | No | Chunk overlap (default: 30) |
| `CORS_ORIGINS` | No | Comma-separated origins (default: `*`). The only lockdown knob |
| `UNLOCK_RADIUS_METERS` | No | How close you must stand to read a memory (default: 150) |
| `MEDIA_DIR` | No | Where uploads are written (default: `media`; a volume in Docker) |
| `REPORT_THRESHOLD` | No | Distinct devices needed to hide a submission (default: 3) |
| `ENABLE_EMBED` | No | Set `0` to withhold `/embed` on a public host |
| `GOOGLE_CLIENT_IDS` | For sign-in | Comma-separated audience whitelist. Empty = `/v1/auth/*` answers 503 |
| `APPLE_CLIENT_IDS` | For sign-in | Same, for Apple |

The app has its own, baked in at dev-server start - see `mobile/.env.example`.

Note: geocoding is handled by Claude during extraction; there is no geocoding
API and no geocoding stage.

## Database

### Container
- Image: `postgis/postgis:16-3.4`
- Extensions: PostGIS for geographic queries

### Schema

Ten tables. `db/schema.sql` is the full definition and is applied on first
container init; `db/migrations/` carries the same changes for databases that
already exist, and `tests/test_schema_layers.py` holds the two in agreement.

| Table | What it holds |
|---|---|
| `content` | Source videos and archive items |
| `transcripts` | JSONB segments with timestamps |
| `places` | Locations, with PostGIS coordinates |
| `memories` | Experiences pinned to places. `content_id` **or** `user_id`, never both |
| `devices` | An installation's self-issued UUID. Not a person |
| `users` | A display name and an id. Created on first submission or sign-in |
| `identities` | `(google\|apple, subject)` → user. How a new phone proves it is you |
| `unlocks` | `(device, memory)` — who has earned what |
| `media` | Photos and recordings attached to a submitted memory |
| `reports` | `(memory, device)` — what makes public submissions defensible |

The four original tables are detailed below. For the six that arrived with
submissions and sign-in, read `db/schema.sql` — it is commented and it is the
one copy that cannot go stale.

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

```
memory-lane/
├── .env                    # Environment variables (copy from .env.example)
├── .env.example            # Template for environment variables
├── docker-compose.yml
├── requirements.txt
├── config/
│   └── content.yaml        # Content sources to process
├── crawler/
│   └── yt_crawler.py       # YouTube channel discovery (yt-dlp)
├── db/
│   ├── schema.sql          # Full schema, applied on first container init
│   └── migrations/         # The same changes, for databases that already exist
├── pipeline/
│   ├── db.py               # Database connection
│   ├── config.py           # Every env knob, read once
│   ├── ingest.py           # Load content from config
│   ├── transcripts.py      # Fetch YouTube transcripts
│   ├── extract.py          # LLM memory extraction (sequential)
│   ├── tasks.py            # The same, over RQ, with a Haiku pre-filter
│   ├── worker.py           # RQ worker entry point
│   ├── enqueue.py          # Queue videos for the parallel path
│   ├── dedup.py            # Propose place merges
│   ├── quality.py          # Score the summaries
│   └── run_all.py          # Run full pipeline
├── api/
│   ├── main.py             # App, CORS, media mount, router includes
│   ├── models.py           # Every shape the API accepts or returns
│   ├── queries.py          # Every SQL string
│   ├── gate.py             # row -> Memory, redacted unless you are near
│   ├── read.py             # The read endpoints
│   ├── write.py            # Unlock, media, submissions, reports
│   ├── accounts.py         # /v1/me and /v1/auth/*
│   ├── auth.py             # Google and Apple token verification
│   ├── media.py            # What an upload may be, and where it lands
│   ├── privacy.py          # The policy both app stores require
│   ├── card.py             # The server-rendered card
│   └── embed.py            # The embeddable map
├── mobile/                 # The Expo app. Read mobile/UI.md first
├── loop/                   # verify.sh (the gate), TASKS.yaml, STATE.md
├── docs/                   # This directory
└── tests/
```

## Startup Commands

```bash
# Start database
docker compose up -d

# Verify database is ready
docker compose exec db pg_isready -U memorylane

# Setup Python environment (first time only)
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Run pipeline stages (with venv activated)
python -m pipeline.ingest       # Load content URLs from config
python -m pipeline.transcripts  # Fetch YouTube transcripts
python -m pipeline.extract      # Extract memories with coordinates

# Score the summaries - run before and after any prompt change
python -m pipeline.quality

# Or run all stages
python -m pipeline.run_all

# Start API
uvicorn api.main:app --reload --port 8000
```
