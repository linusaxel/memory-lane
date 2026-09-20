# Memory Lane

Extract location-based memories from video transcripts and make them queryable by geographic proximity.

## Quick Start

```bash
# 1. Start database, API and Redis
docker compose up -d

# 2. Setup Python environment
python3 -m venv venv   # 3.12; 3.14's pyexpat breaks pip
source venv/bin/activate
pip install -r requirements.txt -r requirements-dev.txt

# 3. Add your API key
cp .env.example .env
# Edit .env and add ANTHROPIC_API_KEY

# 4. Run pipeline
python -m pipeline.ingest
python -m pipeline.transcripts
python -m pipeline.extract
```

## For AI Agents

See **[CLAUDE.md](CLAUDE.md)** for a quick reference guide optimized for AI coding assistants.

## What's here

| Path | What it is |
|------|------------|
| `pipeline/` | Ingest, transcripts, extraction (sequential and RQ-queued) |
| `crawler/` | Channel discovery via yt-dlp |
| `api/` | FastAPI proximity + search API over PostGIS |
| `mobile/` | Expo app: map, pins, memory sheet |
| `tests/` | 120 tests. Run them with `./loop/verify.sh` |
| `db/` | Schema and one-off migrations |

## Documentation

| Doc | Description |
|-----|-------------|
| [00-spec.md](docs/00-spec.md) | Project specification and data model |
| [01-setup.md](docs/01-setup.md) | Environment, database schema, project structure |
| [02-ingest.md](docs/02-ingest.md) | Content sources, channel discovery, URL handling |
| [02-scaling-and-api.md](docs/02-scaling-and-api.md) | Queue architecture and API design notes |
| [03-transcripts.md](docs/03-transcripts.md) | Transcript fetching and failure handling |
| [04-extract.md](docs/04-extract.md) | The extraction prompt and its output contract |
| [07-testing.md](docs/07-testing.md) | What the suite covers and how to run it |

The API's endpoint list lives in [CLAUDE.md](CLAUDE.md#api-apimainpy).
