# LOOP STATE — rewritten every tick. Trust this file over your instincts.

```
tick:     1
updated:  2026-09-20
branch:   loop/autopilot   (3 commits ahead of main, NEVER PUSHED)
gate:     GREEN — 18 passed in 0.06s
head:     4a36a4b "W1-01: declare yt-dlp for channel discovery"
```

## What this project is

**Memory Lane** turns YouTube transcripts into location-tagged "memories" and serves them
by geographic proximity: transcripts → LLM extraction with coordinates → PostGIS →
FastAPI → (soon) an Expo map app. See `CLAUDE.md` only if a task's `touches:` says so.

## Where I am

**LAST DONE: W1-01** — `yt-dlp>=2026.8.19` declared in `requirements.txt` and installed
(resolved to 2026.08.19). Verify passes.

**NEXT TASK: W1-02** — rewrite `crawler/yt_crawler.py` as pure discovery.

**NEXT CONCRETE ACTION:** write `tests/test_crawler.py` first. It must fake `YoutubeDL`
(no network — the live check is W1-03, which is marked `live` and deselected by the gate)
and assert the entry→dict mapping:

- URL is built from `entry["id"]`, not from `entry["url"]`
- `timestamp` → timezone-aware `datetime`; missing timestamp → `None`
- an entry with no `id` is dropped
- `limit` is forwarded to yt-dlp as `playlistend`
- `/videos` is appended exactly once (`.../@x/videos` must not become `/videos/videos`)

Then rewrite the module to satisfy it. **Most of this task is deletion**: remove
`fetch_transcript`, `save_transcript_txt`, `crawl_channel_transcripts`, the hardcoded
`__main__` channel, and `extract_video_id`. Keep one public function
`list_channel_videos(channel_url, limit) -> [{url, title, published_at}]` plus an
argparse `__main__`. Use `extract_flat: "in_playlist"` so it stays metadata-only.

Two constraints that are easy to get wrong:
- `crawler` must **not** import `pipeline` — W1-04 makes `pipeline.ingest` import
  `crawler`, and the cycle would bite.
- `pipeline/ingest.py:extract_youtube_id` (line 18) becomes the repo's **only** video-id
  parser. Do not write a second one.

## Do not redo — already done, leave alone

- **W0-01** the loop harness (`loop/`, `tests/test_loop_contract.py`,
  `tests/test_harness.py`, `tests/conftest.py`, `tests/fakes.py`,
  `.claude/commands/ml-tick.md`). Commit `b7fc77b`.
- **W1-01** yt-dlp declared + installed. Commit `4a36a4b`. Do not re-install it.
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
W1 crawler    1/9   — 7 todo, 1 parked (API_CREDITS)
W2 backend    0/8   — 7 todo, 1 parked (DEPLOY)
W3 app        0/15  — 12 todo, 3 parked
              ----
              2/33 done, 5 parked, 26 to build
```
