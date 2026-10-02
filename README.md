# Memory Lane

**A walk planner with memories along the way.** One free walk a day past real
stories pinned to the places they happened, from travel shows, podcasts and
people who were there. A story only opens on the walk, standing on its spot.

**Shape:** a Python pipeline and a FastAPI server over PostGIS, plus an Expo app,
in one repo with no other services ([architecture](docs/architecture.md)).
Four things a newcomer must not break:

- A memory is gated: you read it by standing there, on a walk ([why](docs/10-decisions.md#the-gate))
- The self-issued device UUID is the only credential ([why](docs/10-decisions.md#no-session-tokens-signed-in-or-not))
- Sign-in is Google and Apple only ([why](docs/10-decisions.md#google-and-apple-only))
- The summary is the product, and it is measured ([why](docs/10-decisions.md#summary-quality-is-measured-not-asserted))

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

See **[AGENTS.md](AGENTS.md)**. `CLAUDE.md` just points there.

## What's here

See [docs/repository-map.md](docs/repository-map.md). Run the tests with `./loop/verify.sh`.

## Documentation

| Doc | Description |
|-----|-------------|
| [00-spec.md](docs/00-spec.md) | Project specification and data model |
| [architecture.md](docs/architecture.md) | How the parts talk, who owns which table, security, deployment |
| [repository-map.md](docs/repository-map.md) | Every directory and key file, one line each |
| [coding-standards.md](docs/coding-standards.md) | The rules the gate and reviews enforce, and [examples](docs/examples/) |
| [01-setup.md](docs/01-setup.md) | Environment variables, database schema, common tasks |
| [02-ingest.md](docs/02-ingest.md) | Content sources, channel discovery, URL handling |
| [03-transcripts.md](docs/03-transcripts.md) | Transcript fetching and failure handling |
| [04-extract.md](docs/04-extract.md) | The extraction prompt, its output contract, and the quality baseline |
| [05-scaling-and-api.md](docs/05-scaling-and-api.md) | Queue architecture and API design notes (historical) |
| [06-api.md](docs/06-api.md) | Every endpoint |
| [07-testing.md](docs/07-testing.md) | What the suite covers and how to run it |
| [08-ux-flows.md](docs/08-ux-flows.md) | What a person actually does, start to finish |
| [09-visual-design.md](docs/09-visual-design.md) | Why the app looks the way it does, and what was rejected |
| [10-decisions.md](docs/10-decisions.md) | The calls where the obvious alternative is wrong |
| [11-memory-types.md](docs/11-memory-types.md) | What a memory is and isn't: layer vs. tag vs. confidence |
| [mobile/UI.md](mobile/UI.md) | Design tokens and app constraints |

The API's endpoint list lives in [06-api.md](docs/06-api.md).
