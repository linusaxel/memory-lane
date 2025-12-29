# Memory Lane

Extract location-based memories from video transcripts and make them queryable by geographic proximity.

## Quick Start

```bash
# 1. Start database
docker compose up -d

# 2. Setup Python environment
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

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

## Documentation

| Doc | Description |
|-----|-------------|
| [00-spec.md](docs/00-spec.md) | Project specification and data model |
| [01-setup.md](docs/01-setup.md) | Environment, database schema, project structure |
