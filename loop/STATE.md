# LOOP STATE — rewritten every tick. Trust this file over your instincts.

```
tick:     2
updated:  2026-09-20
branch:   loop/autopilot   (5 commits ahead of main, NEVER PUSHED)
gate:     GREEN — 31 passed in 0.15s
head:     099a12c "W1-02: rewrite the crawler as pure discovery"
```

## What this project is

**Memory Lane** turns YouTube transcripts into location-tagged "memories" and serves them
by geographic proximity: transcripts → LLM extraction with coordinates → PostGIS →
FastAPI → (soon) an Expo map app. See `CLAUDE.md` only if a task's `touches:` says so.

## Where I am

**LAST DONE: W1-02** — `crawler/yt_crawler.py` is now pure discovery: 139 lines down to
85, one public function `list_channel_videos()`, 12 offline tests green.

**NEXT TASK: W1-03** — prove discovery works against a real channel (the `live` test).

**NEXT CONCRETE ACTION:** add a test to `tests/test_crawler.py` marked
`@pytest.mark.live` that calls `list_channel_videos()` against a real, busy channel and
asserts (a) it returns **well over 30** videos — the number that proves the old
single-page truncation is gone, against a measured baseline of **0** — and (b) every id
in the returned URLs matches `^[A-Za-z0-9_-]{11}$`.

Run it with `venv/bin/python -m pytest -q -m live tests/test_crawler.py`. It needs
network but costs nothing. It is marked `live` so the gate keeps deselecting it — do not
remove that marker, and do not put a network call in an unmarked test.

**Pick a channel that still exists.** `@TheMountainDispatch` (the old hardcoded one)
returns 404. Verify the handle resolves before asserting against it.

## Do not redo — already done, leave alone

- **W0-01** the loop harness (`loop/`, `tests/test_loop_contract.py`,
  `tests/test_harness.py`, `tests/conftest.py`, `tests/fakes.py`,
  `.claude/commands/ml-tick.md`). Commit `b7fc77b`.
- **W1-01** yt-dlp declared + installed. Commit `4a36a4b`. Do not re-install it.
- **W1-02** crawler rewritten as discovery-only. Commit `099a12c`. The deletions are
  deliberate and `tests/test_crawler.py::test_transcript_handling_is_gone` guards them —
  if you find yourself re-adding transcript code here, stop and read that test.
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
W1 crawler    2/9   — 6 todo, 1 parked (API_CREDITS)
W2 backend    0/8   — 7 todo, 1 parked (DEPLOY)
W3 app        0/15  — 12 todo, 3 parked
              ----
              3/33 done, 5 parked, 25 to build
```
