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

## Coverage

Measured, not targeted. Baseline on 2026-09-24, gate selection
(`-m "not credits and not live"`):

```bash
venv/bin/python -m pytest -q -m "not credits and not live" --cov=api --cov=pipeline --cov=crawler
```

| Package | Statements | Covered |
|---|---|---|
| `api/` | 1205 | 98% |
| `pipeline/` | 1622 | 55% |
| `crawler/` | 41 | 68% |
| **Total** | 2868 | **73%** |

The pipeline's gap is its CLIs (`run_all`, `enqueue`, `worker`, `perf`, `route_bench` at
0–28%) and the paths that bill (`tasks`, `quality`, `classifier_audit`). The gate
enforces no floor. Add one only if a number starts to slide.

## Running a subset

```bash
venv/bin/python -m pytest tests/test_extract_places.py -v
venv/bin/python -m pytest -m db          # just the database-backed ones
venv/bin/python -m ruff check .          # style only
```

## Watching the flows, on a simulator

The gate answers "is each rule right". It cannot answer "does the product
work", because the one mechanic everything is built around — walk into range,
hold the ring, a memory arrives — needs a map, a moving position and a finger.

`./e2e/run.sh` supplies all three. Maestro drives the native app on an iOS
simulator against a throwaway `memorylane_e2e` database seeded by
`pipeline/seed_dev.py`; `--record` leaves an mp4. Flows live in `.maestro/`,
one per id in `docs/08-ux-flows.md`. Full instructions, and the four
non-obvious rules for writing a flow, are in `e2e/README.md`.

Three layers, and only two of them run in CI:

| | Where | In the gate | Answers |
|---|---|---|---|
| Rules | `tests/test_api_*.py` | yes | is each rule right |
| Flows, headless | `tests/test_flows.py` | yes | do the rules compose into a journey |
| Flows, watchable | `.maestro/*.yml` | **no** | does the product work |

The simulator layer is deliberately outside `loop/verify.sh`: the gate's budget
is under a minute, and `ubuntu-latest` has no iOS simulator. What the gate does
keep is `tests/test_flows.py` — the headless twin of the same six journeys — so
a red Maestro flow can be attributed. If `test_flows.py` is green, the API is
fine and the app moved.

It also keeps a parity check. The YAML hardcodes coordinates and place names
that live in `pipeline/seed_dev.py`, and when they drift nothing errors — the
simulator just shows an empty map, which reads as "the app is broken".
`test_maestro_flows_still_point_at_the_seed` fails instead.

The first run of this suite found two crashes-or-worse in the app — a Fabric
mounting crash in react-native-maps and an F19 that never rendered at all.
Both are fixed; `e2e/README.md` keeps the diagnosis, because the second one is
the kind of thing that comes back.

## Spending a few cents on purpose

- **There is no `--limit` flag.** `python -m pipeline.extract` runs
  `extract_all_pending()` and bills every pending video. To spend a few cents
  instead, extract one video through the queue path:
  `python -m pipeline.enqueue --video <content_id>` (then `--status <id>`).
- The extraction prompt is in `extract.py:SYSTEM_PROMPT` - tweak for better results
- Check `geocode_status` column: 'llm' means coordinates from extraction, 'dawa' means a Danish address DAWA placed, 'pending' means missing
