# LOOP STATE — every buildable task is done. What is left needs a person.

```
updated:  2026-09-21
branch:   loop/autopilot   — NOT pushed. `main` is behind by this session's commits.
gate:     GREEN, 453 tests
status:   TASKS.yaml has no `todo` and no `doing` left. Eight items are parked,
          each on a named gate, each with the exact command a human would run.
```

**`TODO.md` is the roadmap and the source of truth.** This file is the loop's
orientation doc and does not compete with it. Where they disagree, TODO.md wins
and this file is stale.

## What this session added

| | |
|---|---|
| `7210834` | **P3-05** the write path is capped: 20 memories and 64 MB per person per rolling day. Per *user*, not per device, so a second phone on one account is not a second allowance |
| `e59a227` | **P3-04** layer precedence leads the nearby ORDER BY — friend, stranger, historical — ahead of contrast. The sheet pager inherits it |
| `10a0624` | **P2-05** `pipeline/export.py`, the delivered-corpus export. Snippets, historical only, no row without both an attribution and a link |
| `6826298` | **P1-09** the credit is pinned out of the ScrollView, so a screenshot keeps the attribution |
| `315cbae` | **P5-01** anniversary resurfacing: `happened_at` matching today's day-and-month sorts above contrast |
| `9642dba` | **P5-02** time-locked memories. `not_yet_open` at the top of `is_locked`, ahead of position |
| `ed86332` | **W3-16** the first *native* build. Found expo-location declaring always-on location and motion; added `EXPO_PUBLIC_DEV_OPEN_MEMORY` and a sealed dev seed |

Plus a TODO.md accuracy pass: four bullets were still claiming work that had
shipped, which is the failure that file explicitly warns about.

## What works right now

```bash
docker compose up -d --build              # API + PostGIS
./api/test_api.sh http://localhost:8080   # 11 checks
./loop/verify.sh                          # 450 tests, GREEN
python -m pipeline.seed_dev               # memories you can actually reach
cd mobile && npx expo start               # the app
```

## The next concrete action

**There is no next task the loop may take.** Every remaining item is parked on a
gate the loop is forbidden to open — money, an account, a push, or a product
decision that is not an agent's to make. Written for somebody with no memory of
this session, cheapest first:

1. **`P4-01`, free, needs a decision.** Read the note on that task. Phase 4 was
   written before user submissions existed and 3.2 answered the same question
   differently; three ways out are laid out there and all three are defensible.
2. **`W4-02` / semantic dedup, free, needs a decision.** The recommendation is
   in TODO.md 1.2: have extraction emit venue / locality / region as separate
   fields instead of one `place_query` blob. That is a prompt and schema change.
3. **`API_CREDITS`.** The extraction path has never run against a real API; every
   test uses `FakeAnthropic`. `python -m pipeline.enqueue --video <content_id>`
   then `--status <id>` spends cents rather than the whole corpus — there is
   **no `--limit` flag** and `python -m pipeline.extract` bills every pending
   video. Eyeball 20 summaries against the four failure modes in CLAUDE.md.
4. **`DEPLOY`.** Railway, ~$5/mo. Not Fly — its managed Postgres has no PostGIS.
   Unblocks `P2-00` (tiles) and 2.3 (per-customer CORS and an embed key).
5. **`EAS_BUILD`**, then **`STORE_ACCOUNT`**. Three `PLACEHOLDER` tripwires go
   first; the bundle id is irreversible once submitted. If the Play account is
   personal rather than an organization, production access is gated behind
   closed testing with 12 testers for 14 continuous days — start that the day
   EAS produces an `.aab`, not after everything else.

## Parked, and what each one needs

| Task | Gate | What a human has to do |
|---|---|---|
| `W1-09` | API_CREDITS | one video through the queue path, then read 20 summaries |
| `W4-02` | NEEDS_DECISION | structured venue/locality/region from extraction, or accept 25 pairs by review |
| `P4-01` | NEEDS_DECISION | decide what a stranger note *is*, now that 3.2 shipped a permanent one |
| `P2-00` | DEPLOY | a tile account. Stadia key, or Protomaps on R2. `TILE_URL` is one constant |
| `D-05` | NEEDS_DECISION | choose the historical source (arkiv.dk scraping vs setlist.fm's REST API), and confirm reuse terms |
| `EAS_BUILD` | EAS_BUILD | replace the three PLACEHOLDERs, then build |
| `STORE_ACCOUNT` | STORE_ACCOUNT | Apple $99/yr, Play $25 |

**`W3-13` is discharged, not parked.** It was performed on 2026-09-21 against a
real `npx expo run:ios` build and four states were screenshotted. It stays
`blocked` in `TASKS.yaml` only because its `verify` is `MANUAL` and the contract
reserves `done` for machine-checked proof — a screenshot is not an exit code,
and that rule is not worth bending for the one task it was written about.
`W3-16` carries everything from it that a test can hold.

## Do not redo

- **Contrast scoring, the layer filter, `meta.total`, the tag vocabulary, the
  palette, cross-video place dedup, the proximity unlock, submissions with photo
  and audio, Google/Apple sign-in, the dev seed, rate limiting, the corpus
  export, the pinned credit, anniversaries and time locks** are all in. TODO.md
  carries the commit for each; four of its bullets were still claiming otherwise
  until this session and it cost nothing only because nobody read them.
- **The `ruff format` corruption was never ruff.** Traced to an editor watching
  the directory. `compileall` catches it every time and nothing ever landed.
- **The OSM/Overpass enrichment pass for contrast** is deliberately not built:
  60% of the coordinates are city centroids, so it would confidently describe
  the wrong street corner.

## Rejected approaches — do not retry

- Scraping channel HTML for `"videoId"` — returns 0 for every channel now.
- Homebrew Python 3.14 — broken `pyexpat`.
- expo-router, bottom-sheet or react-query for a one-screen app.
- Shelling out to `pytest --collect-only` inside a test.
- An OR-split full-text predicate for `/v1/memories/search` — built, measured
  against the live database, reverted. An OR across two tables cannot use either
  index. Two designs that *would* work are in TODO.md; neither is worth it at
  224 memories with no caller.
- **`npx prettier` on `mobile/`** — there is no config, so it rewrites every
  file to double quotes at 80 columns. Match the file by hand.
- **Opening the `com.PLACEHOLDER.memorylane://` URL by hand** to point the dev
  client at Metro. It raises an "Open in Memory Lane?" system alert that cannot
  be dismissed without a tap, and it then sits over every screenshot until the
  simulator is rebooted. Start Metro with `REACT_NATIVE_PACKAGER_HOSTNAME=localhost`
  and use `xcrun simctl launch`; the dev client remembers the last URL.
