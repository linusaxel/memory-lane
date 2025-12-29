# Setup

## Prerequisites

- Docker and Docker Compose
- Python 3.11+ (tested with 3.14)
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
| `ANTHROPIC_API_KEY` | Yes | Claude API key |
| `LOG_LEVEL` | No | Logging level (default: INFO) |
| `EXTRACTION_MODEL` | No | Claude model (default: claude-sonnet-4-20250514) |
| `CHUNK_MINUTES` | No | Transcript chunk size (default: 4) |
| `CHUNK_OVERLAP_SECONDS` | No | Chunk overlap (default: 30) |

Note: Geocoding is handled directly by Claude during extraction - no external geocoding API required.

## Database

### Container
- Image: `postgis/postgis:16-3.4`
- Extensions: PostGIS for geographic queries

### Schema

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
| geocode_response | JSONB | Raw API response |

#### `memories` table
Stores extracted memories.

| Column | Type | Description |
|--------|------|-------------|
| id | SERIAL | Primary key |
| place_id | INTEGER | FK to places |
| content_id | INTEGER | FK to content |
| timestamp_start | REAL | Start time in video |
| timestamp_end | REAL | End time in video |
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
│   └── yt_crawler.py       # YouTube channel scraper utility
├── db/
│   └── schema.sql          # Database schema (auto-applied on first run)
├── pipeline/
│   ├── __init__.py
│   ├── db.py               # Database connection
│   ├── ingest.py           # Load content from config
│   ├── transcripts.py      # Fetch YouTube transcripts
│   ├── extract.py          # LLM memory extraction (includes geocoding)
│   ├── geocode.py          # Geocoding utilities (stats, manual fixes)
│   └── run_all.py          # Run full pipeline
├── api/
│   └── main.py             # FastAPI query endpoint
├── examples/
│   └── content.yaml        # Example content configuration
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

# Check geocoding status (optional - coordinates come from LLM)
python -m pipeline.geocode

# Or run all stages
python -m pipeline.run_all

# Start API
uvicorn api.main:app --reload --port 8000
```
