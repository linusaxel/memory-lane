# LOOP STATE — rewritten every tick. Trust this file over your instincts.

```
tick:     0  (bootstrap, written by hand — the loop did not author its own contract)
updated:  2026-09-20
branch:   loop/autopilot   (1 commit ahead of main, NEVER PUSHED)
gate:     see `./loop/verify.sh`
```

## What this project is

**Memory Lane** turns YouTube transcripts into location-tagged "memories" and serves them
by geographic proximity: transcripts → LLM extraction with coordinates → PostGIS →
FastAPI → (soon) an Expo map app. See `CLAUDE.md` only if a task's `touches:` says so.

## Where I am

**CURRENT TASK: none yet. Start at W1-01.**

The bootstrap session built the loop machinery itself (W0-01) and repaired the Python
environment. No project work has started.

**NEXT CONCRETE ACTION:** pick up `W1-01` — add `yt-dlp>=2026.8.19` to
`requirements.txt` under a `# Crawler` heading, install it with
`uv pip install --python venv/bin/python -r requirements.txt`, then verify with
`venv/bin/python -c 'import yt_dlp; print(yt_dlp.version.__version__)'`.

## Do not redo — already done, leave alone

- **W0-01** the loop harness: `loop/TASKS.yaml`, `loop/verify.sh`,
  `tests/test_loop_contract.py`, `tests/test_harness.py`, `tests/conftest.py`,
  `tests/fakes.py`, `.claude/commands/ml-tick.md`.
- **The venv was rebuilt on Python 3.12.12** and every dependency reinstalled. Do not
  "fix" it again. See *Rejected approaches* for why.

## Rejected approaches — do NOT retry these

- **Scraping channel HTML for `"videoId":"..."`** (the original `crawler/yt_crawler.py`).
  Measured 2026-09-20: returns **0 videos for every channel tested** —
  `@TheMountainDispatch` 404s (the hardcoded channel is gone), `@veritasium` 302s with an
  empty body, `@mkbhd` yields 0 ids. This is not a pagination bug to patch; YouTube no
  longer serves that markup to a plain client. Do not try to "fix the regex".
- **Reimplementing discovery on stdlib** via the internal `youtubei/v1/browse` endpoint.
  ~120 lines of undocumented JSON walking that breaks silently by returning a short list.
  `yt-dlp` is that parser, maintained weekly, with **zero hard dependencies** (verified
  on PyPI). W1-01 adopts it.
- **Homebrew Python 3.14 for the venv.** Its `pyexpat` links against a `/usr/lib/libexpat`
  that is too old, which breaks `pip` *and* `platform.mac_ver()`, so nothing can be
  installed at all. That is why `redis` and `rq` were missing from the old venv. The venv
  now runs uv-managed **Python 3.12.12** (matching the `python:3.12-slim` Docker target in
  W2-02). The broken one is parked at `venv.broken-py314/` — a human can delete it.
  Use `uv pip install --python venv/bin/python ...`, **not** `venv/bin/pip`.

## PARKED — needs a human. The loop must never attempt these.

| Task | Gate | One-line ask |
|---|---|---|
| W1-09 | `API_CREDITS` | Run real extraction once and eyeball 20 memories for quality |
| W2-08 | `DEPLOY` | Railway: PostGIS service + API service, note the HTTPS domain |
| W3-13 | `NEEDS_DECISION` | Look at the app on the iOS Simulator — needs human eyes, not an exit code |
| W3-14 | `EAS_BUILD` | Real bundle ID, Maps API key, `eas credentials`, `eas build` |
| W3-15 | `STORE_ACCOUNT` | Apple Developer ($99/yr) + Play Console ($25); **12 testers × 14 days** for Play |

Full instructions live in each task's `note:` in `loop/TASKS.yaml`. Read them there
rather than duplicating them here.

## Progress

```
W0 harness    1/1  done
W1 crawler    0/9   — 8 todo, 1 parked (API_CREDITS)
W2 backend    0/8   — 7 todo, 1 parked (DEPLOY)
W3 app        0/15  — 12 todo, 3 parked (NEEDS_DECISION, EAS_BUILD, STORE_ACCOUNT)
              ----
              1/33 done, 5 parked, 27 to build
```
