# Testing

## One command

```bash
./loop/verify.sh
```

That is the whole quality bar. It exits:

| Exit | Meaning |
|------|---------|
| `0` GREEN | everything passes |
| `1` RED | something is broken; fixing it outranks other work |
| `2` INFRA | the environment needs a human (Docker down, venv or ruff missing, `mobile/node_modules` absent) |

The INFRA/RED split matters: it keeps an agent from "fixing code" when the real
answer is `npm ci`.

In order, the gate runs `compileall`, `ruff check` + `ruff format --check`,
Postgres (only if a test is marked `db`), pytest, then `tsc --noEmit` and
`node --test` for the app. Budget is 60s warm; it currently runs in about 15.

## Markers

Declared in `pytest.ini`, enforced with `--strict-markers`:

- `db` — needs the Docker Postgres service. `tests/conftest.py` builds a real
  ephemeral PostGIS database from `db/schema.sql` per session and truncates
  between tests, because most of what's under test *is* PostGIS
  (`ST_DWithin`, the GIST index, a unique index) and a mock would prove nothing.
- `live` — needs the network. Deselected by the gate for determinism.
- `credits` — would spend real Anthropic money. **The gate never runs these.**

The gate selects `-m "not credits and not live"`.

## What the suite covers

| File | Covers |
|------|--------|
| `test_api_sql.py` | EXPLAINs every query constant in `api.main` against real PostGIS. Nothing else executes those strings. |
| `test_api_cors.py` / `test_api_privacy.py` | CORS headers, the `/` health shape Railway probes, the `/privacy` page |
| `test_extract_places.py` | The same place saved twice is one row, not two |
| `test_classifier.py` | An unusable `CLASSIFIER_MODEL` raises; transient errors still fail open |
| `test_transcripts.py` | Permanent failures mark the row, transient ones propagate for retry |
| `test_ingest.py` | Channel discovery, dedup, idempotent re-ingest |
| `test_crawler.py` | yt-dlp mapping, canonical URLs, no `pipeline` import cycle |
| `test_app_config.py` / `test_app_assets.py` / `test_store_copy.py` | Store-review constraints on `mobile/` |
| `test_harness.py` / `test_loop_contract.py` | The loop's own machinery |

## No credits, ever

`tests/fakes.py` provides `FakeAnthropic`, a drop-in that records the requests
it would have sent and returns a canned payload. It proves chunking, prompt
assembly, parsing and DB writes. It does **not** prove extraction quality —
that needs a human with an API key.

## Running a subset

```bash
venv/bin/python -m pytest tests/test_extract_places.py -v
venv/bin/python -m pytest -m db          # just the database-backed ones
venv/bin/python -m ruff check .          # style only
```

## Against a running API

```bash
docker compose up -d --build
./api/test_api.sh                        # 14 curl checks, defaults to :8080
```

This one is data-dependent: it expects a seeded database and reports failures
against an empty one. It is not part of the gate.
