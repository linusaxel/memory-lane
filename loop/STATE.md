# LOOP STATE — rewritten every tick. Trust this file over your instincts.

```
tick:     4
updated:  2026-09-20
branch:   loop/autopilot   (9 commits ahead of main, NEVER PUSHED)
gate:     GREEN — 43 passed, 2 deselected (live) in 2.6s (~4s wall, incl. Docker db)
head:     d79700c "W1-04: a channel: source feeds the existing ingest stage"
```

## What this project is

**Memory Lane** turns YouTube transcripts into location-tagged "memories" and serves them
by geographic proximity: transcripts → LLM extraction with coordinates → PostGIS →
FastAPI → (soon) an Expo map app. See `CLAUDE.md` only if a task's `touches:` says so.

## Where I am

**LAST DONE: W1-04** — a `channel:` source now discovers videos and inserts them through
the existing ingest path. `pipeline/run_all.py` needed **no change**. 10 tests against a
real PostGIS database.

**NEXT TASK: W1-05** — declare a real channel source in `config/content.yaml`.

**NEXT CONCRETE ACTION:** append a source to `config/content.yaml`:

```yaml
  - name: "<channel name>"
    platform: youtube
    channel: "https://www.youtube.com/@<handle>"
    limit: 25
```

Then verify with the task's command. **The handle must actually resolve** —
`@TheMountainDispatch`, the channel the old crawler hardcoded, returns 404. A known-good
handle is `@veritasium` (used by the live tests), but prefer a channel whose videos suit
this project: Memory Lane wants **location-rich storytelling** (travel, food, city
history), not science explainers. `config/content.yaml` currently holds
"Tuesdays with Stories"; a comedy/story podcast channel is a better fit than @veritasium.

Keep `limit: 25` so the first real crawl is bounded. Removing the key ingests everything.

**Do not run extraction.** Ingest and transcripts are free; `pipeline/extract.py` spends
Anthropic credits and is parked as W1-09 for a human.

## Do not redo — already done, leave alone

- **W0-01** the loop harness (`loop/`, `tests/test_loop_contract.py`,
  `tests/test_harness.py`, `tests/conftest.py`, `tests/fakes.py`,
  `.claude/commands/ml-tick.md`). Commit `b7fc77b`.
- **W1-01** yt-dlp declared + installed. Commit `4a36a4b`. Do not re-install it.
- **W1-02** crawler rewritten as discovery-only. Commit `099a12c`. The deletions are
  deliberate and `tests/test_crawler.py::test_transcript_handling_is_gone` guards them —
  if you find yourself re-adding transcript code here, stop and read that test.
- **W1-03** live discovery tests. Commit `2b2f5c5`. They are marked `live` so the gate
  deselects them; that is deliberate, do not "fix" it by removing the marker.
- **W1-04** channel→ingest wiring. Commit `d79700c`. `ingest_content(config=None)` is
  backwards compatible and both existing callers still pass no argument. Do not add a
  separate crawl stage or a second dedup — Stage 1 already does it.
- **The venv was rebuilt on Python 3.12.12** and every dependency reinstalled. Do not
  "fix" it again — see *Rejected approaches*.

## Rejected approaches — do NOT retry these

- **Scraping channel HTML for `"videoId":"..."`** (the original crawler). Measured
  2026-09-20: **0 videos for every channel tested** — `@TheMountainDispatch` 404s (the
  hardcoded channel is gone), `@veritasium` 302s with an empty body, `@mkbhd` yields 0
  ids. YouTube no longer serves that markup to a plain client. This is not a regex to fix.
- **Reimplementing discovery on stdlib** via the internal `youtubei/v1/browse` endpoint:
  ~120 lines of undocumented JSON walking that fails silently by returning a short list.
- **Homebrew Python 3.14 for the venv.** Its `pyexpat` links a too-old `/usr/lib/libexpat`,
  which breaks `pip` *and* `platform.mac_ver()`, so nothing installs at all. That is why
  `redis`/`rq` were missing. The venv now runs uv-managed **Python 3.12.12** (matching the
  `python:3.12-slim` Docker target in W2-02). The broken one sits at `venv.broken-py314/`
  (76MB, a human may delete it). Install with
  `uv pip install --python venv/bin/python ...` — **never** `venv/bin/pip`.
- **A second dedup or a new crawl stage.** The `SELECT id FROM content WHERE url = :url`
  in ingest already makes discovery idempotent, including a video that appears both in
  `videos:` and on the channel. Adding another would be two sources of truth.
- **Shelling out to `pytest --collect-only` from inside a test** (first draft of
  `test_loop_contract.py`). The child re-imports the module and spawns another child —
  a fork bomb. It now reads the file instead, which proves the same thing.

## PARKED — needs a human. The loop must never attempt these.

| Task | Gate | One-line ask |
|---|---|---|
| W1-09 | `API_CREDITS` | Run real extraction once and eyeball 20 memories for quality |
| W2-08 | `DEPLOY` | Railway: PostGIS service + API service, note the HTTPS domain |
| W3-13 | `NEEDS_DECISION` | Look at the app on the iOS Simulator — needs human eyes, not an exit code |
| W3-14 | `EAS_BUILD` | Real bundle ID, Maps API key, `eas credentials`, `eas build` |
| W3-15 | `STORE_ACCOUNT` | Apple Developer ($99/yr) + Play Console ($25); **12 testers × 14 days** for Play |

Full instructions live in each task's `note:` in `loop/TASKS.yaml`.

## Progress

```
W0 harness    1/1  done
W1 crawler    4/9   — 4 todo, 1 parked (API_CREDITS)
W2 backend    0/8   — 7 todo, 1 parked (DEPLOY)
W3 app        0/15  — 12 todo, 3 parked
              ----
              5/33 done, 5 parked, 23 to build
```
