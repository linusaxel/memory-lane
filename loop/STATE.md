# LOOP STATE — rewritten every tick. Trust this file over your instincts.

```
tick:     3
updated:  2026-09-20
branch:   loop/autopilot   (7 commits ahead of main, NEVER PUSHED)
gate:     GREEN — 32 passed, 2 deselected (live) in 0.15s
head:     2b2f5c5 "W1-03: prove channel discovery against a real channel"
```

## What this project is

**Memory Lane** turns YouTube transcripts into location-tagged "memories" and serves them
by geographic proximity: transcripts → LLM extraction with coordinates → PostGIS →
FastAPI → (soon) an Expo map app. See `CLAUDE.md` only if a task's `touches:` says so.

## Where I am

**LAST DONE: W1-03** — discovery proven against a real channel. Measured: 150 requested
from `@veritasium`, **150 returned**, every id an 11-char match, every title populated.
Baseline before the rewrite was **zero**. The crawler now genuinely works.

**NEXT TASK: W1-04** — wire discovery into the existing ingest stage.

**NEXT CONCRETE ACTION:** write `tests/test_ingest.py`, then make two small edits to
`pipeline/ingest.py`:

1. Inside the existing `for source in sources:` loop, right after
   `videos = source.get("videos", [])` (around line 56), add:
   ```python
   if source.get("channel"):
       from crawler.yt_crawler import list_channel_videos
       videos = videos + list_channel_videos(source["channel"], limit=source.get("limit"))
   ```
   The import is local on purpose so `yt_dlp` stays off the import path for
   yaml-only runs.
2. Add `published_at` to the INSERT at ~line 85 (the column already exists in
   `db/schema.sql` and is unused) with `"published_at": video.get("published_at")`
   in the params dict. YAML-sourced videos pass `None`, exactly as today.

**Reuse, do not rewrite.** The dedup `SELECT id FROM content WHERE url = :url`
(line ~73) and the INSERT (line ~85) already exist and already make this idempotent —
including a video that appears in both `videos:` and `channel:`, because the SELECT sees
uncommitted inserts in the same transaction. `pipeline/run_all.py` needs **no change at
all**: discovery rides the existing Stage 1.

Keep the test offline — fake `list_channel_videos`, do not hit the network. Anything
needing a real DB must be marked `@pytest.mark.db`.

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
W1 crawler    3/9   — 5 todo, 1 parked (API_CREDITS)
W2 backend    0/8   — 7 todo, 1 parked (DEPLOY)
W3 app        0/15  — 12 todo, 3 parked
              ----
              4/33 done, 5 parked, 24 to build
```
