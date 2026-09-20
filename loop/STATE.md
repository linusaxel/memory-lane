# LOOP STATE — rewritten every tick. Trust this file over your instincts.

```
tick:     5
updated:  2026-09-20
branch:   loop/autopilot   (11 commits ahead of main, NEVER PUSHED)
gate:     GREEN — 44 passed, 2 deselected (live) in 2.5s (~4s wall, incl. Docker db)
head:     d429e33 "W1-05: auto-discover the Tuesdays with Stories channel"
```

## What this project is

**Memory Lane** turns YouTube transcripts into location-tagged "memories" and serves them
by geographic proximity: transcripts → LLM extraction with coordinates → PostGIS →
FastAPI → (soon) an Expo map app. See `CLAUDE.md` only if a task's `touches:` says so.

## Where I am

**LAST DONE: W1-05** — `config/content.yaml` now auto-discovers
`@TuesdayswithStories` (25 newest), merged into the same source as the ten
hand-listed episodes. Verified the handle resolves and returns 25 videos.

**NEXT TASK: W1-06** — the transcript root-cause fix. This is the most valuable
remaining crawler task; read the reasoning before editing.

**NEXT CONCRETE ACTION:** write `tests/test_transcripts.py` (offline — no DB, no
network, monkeypatch `pipeline.transcripts.YouTubeTranscriptApi`), then make two edits
to `pipeline/transcripts.py`:

1. **Delete the bare `except Exception` at lines 48-50.** It returns `None`, which is
   indistinguishable from "this video genuinely has no captions", so the caller at
   lines ~107-113 sets `transcript_failed = TRUE` **permanently**. One network blip,
   one IP block, one age gate, and that video is black-holed forever.
2. In `fetch_pending_transcripts()`, wrap the `fetch_transcript(video_id)` call:
   ```python
   try:
       result = fetch_transcript(video_id)
   except Exception as e:
       logger.warning(f"Transient error for {video_id}, will retry: {e}")
       failed += 1
       continue          # <- leaves the row PENDING, no flag set
   ```

Keep the three specific handlers (`TranscriptsDisabled`, `VideoUnavailable`,
`NoTranscriptFound`) returning `None` — those are genuinely permanent.

**The retry mechanism already exists.** `fetch_pending_transcripts` selects
`WHERE transcript_failed = FALSE`, so a row left pending is retried on the next run.
Do not add a retry counter, a backoff scheduler, or an error-reason column.

The regression guard is the test asserting **`TimeoutError` propagates** out of
`fetch_transcript`. That test fails the moment anyone reintroduces a bare
`except Exception`. Write it first.

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
- **W1-05** channel declared in `config/content.yaml`. Commit `d429e33`.
  `@TheMountainDispatch` is dead (404); `@TuesdayswithStories` is the right channel —
  it is where the ten hand-listed videos came from.
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
W1 crawler    5/9   — 3 todo, 1 parked (API_CREDITS)
W2 backend    0/8   — 7 todo, 1 parked (DEPLOY)
W3 app        0/15  — 12 todo, 3 parked
              ----
              6/33 done, 5 parked, 22 to build
```
