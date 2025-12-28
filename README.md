# Memory Lane

Extract location-based memories from video transcripts and make them queryable by geographic proximity.

## Quick Start

```bash
# 1. Start database
docker compose up -d

# 2. Install dependencies
pip install -r requirements.txt

# 3. Run pipeline
python -m pipeline.run_all

# 4. Start API
uvicorn api.main:app --reload --port 8000
```

## Documentation

| Doc | Description |
|-----|-------------|
| [00-spec.md](docs/00-spec.md) | High-level project overview |
| [01-setup.md](docs/01-setup.md) | Environment, Docker, database schema |
| [02-ingest.md](docs/02-ingest.md) | Content ingestion from config |
| [03-transcripts.md](docs/03-transcripts.md) | Transcript fetching |
| [04-extract.md](docs/04-extract.md) | LLM memory extraction |
| [05-geocode.md](docs/05-geocode.md) | Place geocoding |
| [06-api.md](docs/06-api.md) | Query API |
| [07-testing.md](docs/07-testing.md) | Validation strategy |

## Examples

- [content.yaml](examples/content.yaml) - Sample content configuration
- [transcript.json](examples/transcript.json) - Sample transcript format
- [extraction-examples.md](examples/extraction-examples.md) - Input/output extraction pairs
