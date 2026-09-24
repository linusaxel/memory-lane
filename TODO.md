# Memory Lane — TODO

This file is the source of truth for open work. `loop/TASKS.yaml` is the
executable contract the `/ml-tick` loop runs against; it gets repopulated from
whichever phase here is active. If the two disagree, this file wins and
TASKS.yaml is wrong.

**Open work only.** A finished entry is deleted, not ticked: `git log -p
TODO.md` keeps its history, and a decision it carried goes to
`docs/10-decisions.md` first. Everything done before 2026-09-24 is in the
history of this file at `c4703b4`.

**Every entry says when it was last checked** against the code, as
`checked YYYY-MM-DD`. More than a few days old means verify before acting on
it: a stale entry once sent a session to rebuild search, which had shipped a
week earlier.

---

## Friction

What slowed a session down or nearly shipped something wrong, and would again.
The rules for adding to it are in CLAUDE.md, "Before you finish". Newest first;
delete an entry when its fix lands.

- [ ] **A broad sweep of the whole test suite.** (checked 2026-09-24) Now
      75 s for 660 tests. 10 s of the old 85 s was eight `test_ingest.py`
      tests asking real YouTube about `@test`, because `fake_channel` missed
      `channel_metadata`; fixed, and `conftest._no_network` now fails any
      unmarked test that leaves localhost. What is left is per-test overhead
      (no single test dominates) and duplicate coverage.
- [ ] **Implemented flows with no journey at all.** (checked 2026-09-24) No
      `.maestro` flow mentions a heart or a streak. F26 heart is a tap in an
      open sheet and cheap to add to the walk, after stop 1's unlock: fill,
      count, and no heart on a locked pin (its Done-when). F27's streak line is
      never asserted, since the walk-done card shows it only above one day; a
      seeded yesterday's unlock in `run.sh` would reach it. F2 (opens a
      browser), F10/F16 (network; by-hand recipe in e2e/README.md), F22 (real
      sign-in) and F28 (background geofence) cannot be scripted on a
      simulator. Say so in e2e/README.md, not by silence.
- [ ] **Nothing records which migrations a database has.** (checked
      2026-09-24) The dev DB had 011-024 but not 010, so `/v1/memories/search`
      500'd locally and nothing said so; found only by running EXPLAIN by
      hand. Tests build from `db/schema.sql`, so the gate cannot see it either.
      **Fix:** a `schema_migrations` table and a `db/migrate.sh` that applies
      what is missing, or at least a check in `verify.sh` that the dev DB's
      columns match `schema.sql`.
- [ ] **One route change is a 4-minute bench to judge.** (checked 2026-09-24)
      `route_bench --scenario all --runs 40` is ~4 min, ~1 s a plan, nearly all
      OSRM `/table`. Six tweaks cost ~25 min of waiting, and 40 runs is noisy
      enough that the same code moved bimodal's spur rate 40% → 45%. A bench
      also holds a transaction, so a migration on the same DB waits behind it.
      **Fix:** cache `/table` per point set inside a bench run, and print a
      spread (or run two seeds) so a 5-point move reads as noise or not.
- [ ] **The route solver lives in the read router.** (checked 2026-09-24)
      `api/read.py` is 1,077 lines, ~450 of them `_choose_walks` /
      `_plan_route` with nested closures, and the ranking is split between
      `_choose_walks.score` and `_plan_route.judge`, so it takes two readings
      to know what a walk is ranked by. **Fix:** move the solver to
      `api/route_solver.py` with the endpoints staying in `read.py`, and give
      the two rankings one docstring.

---

## Known defects

- [ ] **`published_at` is always NULL.** (checked 2026-09-24: nothing in `api/`
      reads it) yt-dlp flat extraction returns no timestamp for this channel.
      A real date needs a per-video fetch or the channel RSS feed (newest 15
      only). Once the video filter runs first, the fetch is only paid for
      videos that will be extracted. Blocks nothing until something serves it.

---

## Phase 0 — Design questions

- [ ] **D.5 Write F3 properly** once the historical source is chosen (W4-00).
      (checked 2026-09-24: F3 is still Proposed in docs/08) F3 is the product;
      it should not be specified by whatever the ingestion happens to produce.

---

## Phase 1 — Historical layer, one neighborhood

Copenhagen. The schema, source-agnostic ingestion, the archival prompt,
contrast scoring, the query and the card are all built (`git log`). What is
missing is a source.

- [ ] **Phase 1 is done when** standing anywhere in the chosen Copenhagen
      neighborhood returns at least one historical card, the top card is the
      highest-contrast one rather than the nearest, and the card is worth
      screenshotting. (checked 2026-09-20) Blocked on *Which historical source
      first?* and *Which neighborhood?* below.

---

## Phase 1.5 — Proximity unlock, left for when the coordinates improve

- [ ] **Re-gate on `precision_meters`** once extraction tells the truth about
      it (option 1 in F7). (checked 2026-09-20) The uniqueness rule is a proxy
      for trustworthy coordinates; see docs/10, "The coordinates are mostly
      guesses". Nothing has re-run since W4-04 changed the prompt.
- [ ] **The position is self-reported.** (checked 2026-09-20) This stops
      `curl`, not a determined spoofer. Attestation needs more than accounts.
      It cuts both ways: a submission is also filed at a position nobody
      verified.

---

## Phase 2 — Embeddable map widget

- [ ] **2.0 Tiles, before this is public.** (checked 2026-09-24: `TILE_URL` in
      `api/embed.py` is still OSM's public tiles) OSMF policy forbids this use
      and they can block it without notice. Options in
      `docs/09-visual-design.md`: Stadia Maps (one URL + a key) or
      Protomaps/PMTiles (~$3/mo on R2). `TILE_URL` is one constant.
      **Blocks deploying the embed anywhere public.**
- [ ] **2.3** Per-customer `CORS_ORIGINS` and a per-embed key. (checked
      2026-09-20) **Blocked on `DEPLOY`**: there is no public origin to allow
      yet. The first thing with a customer attached, so the first that needs a
      usage bound.

---

## Phase 4 — Stranger notes

A submission lands in the `stranger` layer and is **permanent**, which is not
what 4.1 and 4.2 assume. Both are parked on that; `P4-01` in `loop/TASKS.yaml`
has the three ways out and why each is a person's call.

- [ ] **4.1** One note per place, visible to the next visitor only. (checked
      2026-09-21) **Parked:** stranger rows are kept, not consumed.
- [ ] **4.2** ~7-day decay, enforced at read time. (checked 2026-09-21)
      **Parked:** expiring a stranger memory deletes, from its author's own
      collection, the thing they walked somewhere to write.
- [~] **4.3** Moderation. (checked 2026-09-21) The report path hides a memory
      at `REPORT_THRESHOLD` distinct devices. The missing half is a
      pre-publish classifier, which spends credits on every submission
      (`API_CREDITS`) and is not obviously worth it while three reports take
      something down in minutes.

---

## Routes

- [ ] **Authored walks: the rest of `routes` + `route_stops`.** (checked
      2026-09-24) Migration 023 and `GET /v1/routes/{id}` exist, published
      only, kept to `title, status, is_loop`. No author, theme, source, budget
      or geometry until something writes a route (the generated job below, or
      an editor). `daily_routes.route_id` waits for the app to walk one.
- [ ] **Generated themed routes, reviewed before publishing.** (checked
      2026-09-23) An offline job: for each hotspot cluster × each tag, solve
      the same OP from the centroid, write `status='draft'`, then accept or
      reject in the style of `pipeline/review.py`. **First step:** none until
      one area has ≥3 tags with ≥5 walkable stops each. Write that check as a
      query first.
- [ ] **Customise by one swap, not a route editor.** (checked 2026-09-24) The
      length slider, loop toggle and theme chip shipped. Left: (1) "Swap this
      stop", remove it and re-insert the next-best candidate; (3)
      drag-to-reorder, last, since stops unlock in any order anyway. **Decided
      2026-09-23:** one accepted walk per device per day, so a swap needs that
      reopened first.
- [ ] **An end point per request, never stored.** (checked 2026-09-23) "End at
      the subway" is a one-way OP. ⚠️ Storing it would bring back the stored
      home that docs/10 § Routes decided against. Skip until someone asks.

---

## Copenhagen journeys

- [ ] **Walk-and-unlock from three random starts.** (checked 2026-09-24) Was
      "walk 10x faster": walk-and-unlock ran out of its 300 s `FLOW_TIMEOUT`
      at stop 4 from 55.682454,12.585062. `eea45ed` replaced `travel` with
      one `setLocation` per street point (walk flow 204 s → 143 s), so the
      speed knob is gone. **Done when:** `./e2e/run.sh` passes all three flows
      from three random starts; not yet run.
- [ ] **A Copenhagen journey in Maestro.** (checked 2026-09-24: no such flow in
      `.maestro/`) e.g. `.maestro/lakes-loop.yml`: `setLocation` on Olufsvej,
      set the slider to the measured loop (~9.1 km), preview, and assert a
      loop that reaches Sankt Jørgens Sø and reads `.* loop`. Then "Show me
      another" and assert the stops changed. `e2e/travel.py` needs its START
      and budget made arguments.
- [ ] **Seed walks already walked.** (checked 2026-09-24) For that journey: a
      few past `daily_routes` rows on the lakes, dated before today, with the
      unlocks that earned them (one 5 of 5, one abandoned 2 of 5), so the
      Walks tab opens on a history. Also seeds F27's streak (see Friction).
- [ ] **Under each walk, the memories it unlocked.** (checked 2026-09-24:
      `Memories.tsx` shows one row, `earned of size`) List the memories each
      walk earned under its row: place name and the start of the summary, each
      opening its sheet like a collection row. `/v1/routes/walked` already
      returns every stop with earned ones open, so client only. Locked stops
      stay out, or show as a count ("3 not reached"). **Done when:** the
      Maestro journey above asserts one and tapping it opens the sheet.

---

## Parked

Each waits on something named; none is worth building before it.

- [ ] **Retrieve few-shot examples instead of hard-coding three.** (checked
      2026-09-23) Waits on ~50 rows reviewed through `pipeline/review.py`.
- [ ] **Revealed-preference report.** (checked 2026-09-23) A `quality.py
      --signals` view: do the regex flags predict hearts and reports? Waits on
      hearts and reports from real people (3 unlocks, 0 hearts, 0 reports).
- [ ] **Incremental channel re-crawl, tiered.** (checked 2026-09-23) One
      channel with `limit: 25` is one request, and there is no scheduler.
      Stopping at the first known id would also break backfilling by dropping
      `limit`. Waits on several channels and a scheduled ingest.

---

## Blocked on you

They cost money or need an account. Full detail in `loop/STATE.md`.

- [ ] **`API_CREDITS`** (checked 2026-09-23) — the extraction path has never
      met the real API; every test uses `FakeAnthropic`. **There is no
      `--limit` flag**: `python -m pipeline.extract` bills every pending
      video. To spend cents: `python -m pipeline.enqueue --video <content_id>`,
      then `--status <id>`. What has never been sent is the structured-output
      schema (`MEMORY_SCHEMA`), so a rejection shows on the first chunk. Once
      funded: one video, `quality --compare` against the old prompt, the
      pending episodes, `review`, then `classifier_audit`. The 22 clips
      extracted before the video filter probably duplicate their episodes'
      memories; look at them in `review` or `dedup`.
- [ ] **`DEPLOY`** (checked 2026-09-20) — Railway, ~$5/mo. Not Fly: Fly's
      managed Postgres has no PostGIS. Unblocks Phase 2 and an OSRM sidecar
      (~1.6 GB RAM to build).
- [ ] **`EAS_BUILD`** (checked 2026-09-20) — three `PLACEHOLDER` tripwires to
      replace first; the bundle id is irreversible once submitted. Sign-in
      needs this too: neither button works in Expo Go, and
      `GOOGLE_CLIENT_IDS` / `APPLE_CLIENT_IDS` need real client ids.
- [ ] **`STORE_ACCOUNT`** (checked 2026-09-20) — Apple $99/yr, Play $25. A
      personal Play account gates production behind **closed testing with 12
      testers for 14 continuous days**. Start that the day EAS produces an
      `.aab`. F28's background location also needs the App Store Connect and
      Play privacy disclosures updated, and a real device confirming
      delivery.

---

## Open questions

- **Which historical source first?** (checked 2026-09-22) Deliberately
  undecided. arkiv.dk / Københavns Stadsarkiv is the brief's #1 but has no
  public API; setlist.fm is a documented REST API with dense Copenhagen venue
  coverage and the strongest contrast material; Mediestream sits between.
  Founder candidates: x/Twitter, Reddit (both meter API access), free
  literature such as Project Gutenberg (no per-venue coordinates). Check
  reuse terms before ingesting any of them.
- **Reuse terms for arkiv.dk and Mediestream.** (checked 2026-09-20) Unknown.
  The legal posture assumes we may quote at all.
- **Where does "what is there now" come from?** (checked 2026-09-20) Contrast
  needs present-day place identity. Working assumption is OSM/Overpass,
  unvalidated, and useless on centroid coordinates.
- **Which Copenhagen neighborhood?** (checked 2026-09-20) "Saturate one
  neighborhood" needs a boundary before density can be measured.
- **Does the podcast corpus eventually get pruned?** (checked 2026-09-20) It is
  US comedy anecdote in a product about Copenhagen history.
- **Which screen shows too much?** (checked 2026-09-22) The founder asked that
  memories hold only picture, date, description and a source link. The data
  model can't shrink to that: layer and contrast are core (docs/10,
  *Core, not polish*). If one card or screen shows more than those four, name
  it and it is a display fix.
- **Four off-vocabulary tags.** (checked 2026-09-22) `entertainment`,
  `celebrity`, `theater`, `festival` (15 rows) predate the filter and are
  unfilterable. Map them if a filter ever needs them.
- **`api/test_api.sh` is not run by the gate.** (checked 2026-09-24) It was the
  sole caller of three endpoints that went unnoticed and were deleted. Wire it
  in behind a live-server check, or accept it is a manual tool.

---

## Repo legibility — from Suyog Joshi's "How I structure repositories so AI can understand them" (2026-09-24)

Every concept in the article, mapped to what already exists here. Each item
names the gap, not the idea. All checked 2026-09-24: none of `AGENTS.md`,
`docs/architecture.md`, `docs/repository-map.md`, `docs/coding-standards.md`
or `docs/examples/` exists, and no coverage tool is installed.

#### Layer 1 — README states the purpose
- [ ] **README: add the constraints and the architecture style.** Purpose is
      there (two sentences). Missing: the style ("Python pipeline + FastAPI over
      PostGIS + Expo app, one repo, no services"), and the handful of invariants
      a newcomer must not break: memories are gated by standing there; the
      device UUID is the only credential; Google/Apple only; the summary is
      the product. One line each, each linking to its decision.
- [ ] **README: fix the stale facts.** "366 tests" (count it with
      `pytest --collect-only -q`, or drop the number); the docs table is missing
      `11-memory-types.md`; it says `api/main.py` holds the endpoints, but it is
      60 lines now and the routes live in `read.py`/`write.py`/`accounts.py`.

#### Layer 2 — docs/architecture.md
- [ ] **Write `docs/architecture.md`.** Today it is spread across CLAUDE.md
      "Architecture Notes", `02-scaling-and-api.md` and `01-setup.md`. Use the
      article's headings: Style, Communication (sync: REST/JSON from the app;
      async: RQ over Redis for classify → extract → aggregate; outbound: Anthropic,
      YouTube, OSRM), Data ownership (who writes which table: the pipeline writes
      content/transcripts/places/memories; the API writes unlocks/submissions/
      media/reports/routes; nothing else writes to the DB), Security (self-issued
      device id, provider ID tokens, the gate, upload rules), Deployment
      (Railway via `railway.json` + `start.sh`, docker compose locally, the media
      volume). Move content rather than copying it; leave pointers behind.
- [ ] **Add two Mermaid diagrams to it.** (a) the pipeline, from content.yaml
      through Haiku, Sonnet and the aggregator to the DB; (b) the request path, from
      the app through the API and gate to PostGIS, with OSRM on the side. The
      ASCII one in CLAUDE.md moves there.

#### Layer 3 — ADRs as decision memory
- [ ] **Decide the ADR shape, then apply it.** `docs/10-decisions.md` is already
      an ADR log (~45 entries, anchored from code as `#the-gate`) but has no
      Status, Options or Consequences, and it lives in one file. The article's
      form is `docs/adr/NNN-title.md` with Title / Status / Context / Options /
      Decision / Consequences. Option A: split it into `docs/adr/`, one file per
      entry, and rewrite every `docs/10-decisions.md#anchor` reference in the code
      (grep for them). Option B: keep one file and give each entry a
      `Status:` line, an explicit "Options considered", and a "Consequences". B
      keeps the anchors. Pick one; do not half-do both.
- [ ] **Record superseded decisions as Superseded, not deleted.** For example,
      "glass was tried and reverted" is already one; give it that status.

#### Layer 4 — coding standards plus examples
- [ ] **Write `docs/coding-standards.md`.** It collects the rules that live today
      in CLAUDE.md, memory and reviews: ruff/pyproject decides style (never
      hand-align); every SQL string lives in `api/queries.py` and is EXPLAINed by
      `tests/test_api_sql.py`; every env knob goes in `pipeline/config.py`; every
      memory-shaped response goes through `api/gate.py` (and anything that emits a
      summary gates itself, as `api/card.py` does); comments only when
      load-bearing, with the reasoning in `docs/10-decisions.md`; one tag
      vocabulary in `pipeline/tags.py`; the app follows `mobile/UI.md`. Link it,
      don't restate it.
- [ ] **Coverage: measure it, don't pick 80%.** Add `pytest-cov` to
      `requirements-dev.txt`, record the baseline in `docs/07-testing.md`, and
      only then decide whether the gate enforces a floor.
- [ ] **Create `docs/examples/` with three good examples** from real code, not
      invented code: `good-endpoint.md` (a gated read in `api/read.py`: model in
      `models.py`, SQL in `queries.py`, row through `gate.py`), `good-sql-test.md`
      (the EXPLAIN pattern in `tests/test_api_sql.py`), and `good-flow-test.md`
      (one journey in `tests/test_flows.py` using `tests/fakes.py`). Each one is a
      pointer with the "why", so it cannot drift from the code.

#### Layer 5 — repository map
- [ ] **Write `docs/repository-map.md`.** Every top-level directory with one
      line each (`api/ crawler/ config/ db/ docs/ e2e/ loop/ media/ mobile/ osrm/
      pipeline/ tests/ .maestro/`), then a breakdown of `mobile/src/` and `api/`.
      The "Key Files" table in CLAUDE.md moves here, and CLAUDE.md keeps a link.
      README's "What's here" table becomes a link too.
- [ ] **Delete the project-structure tree in `docs/01-setup.md`** once the map
      exists, or else it drifts (check first whether it is already stale).
- [ ] **Doc numbering: two `02-*` files and no 05/06.** Renumber, or drop the
      numbers. They look like an order that isn't one.

#### Layer 6 — AGENTS.md
- [ ] **Add `AGENTS.md` at the root, and make CLAUDE.md a pointer to it**
      (`@AGENTS.md`), so Codex, Cursor and others read the same file. One source
      of truth.
- [ ] **Give it the article's sections, which CLAUDE.md lacks as sections:**
      "Before making changes" (read architecture.md, the ADRs,
      coding-standards.md, and `mobile/UI.md` for the app); Architecture
      constraints; Development rules (run the gate, check `$?`, log friction);
      **Forbidden actions**, collected from the never-rules scattered through
      CLAUDE.md today (never run `pipeline.extract` casually, because it bills every
      pending video; never serve a summary without the gate; never match accounts
      on email; never issue a session token; never add a password sign-in; never
      hand-format); and a PR / commit checklist (gate green, friction logged,
      docs updated if a decision changed).
- [ ] **Shrink it.** CLAUDE.md is 469 lines. Once architecture, map, standards and
      the endpoint list (which goes to `docs/api.md` or `/docs`) have moved out,
      AGENTS.md should fit on a screen or two and link out.

#### Target tree and principle
- [ ] **Check the tree against the article's:** README.md, AGENTS.md,
      docs/{architecture,repository-map,coding-standards}.md, docs/adr/,
      docs/examples/, src (here: api/ pipeline/ mobile/), tests/, scripts (here:
      loop/, e2e/). Note the deliberate differences in the repo map instead of
      moving code.
- [ ] **Write for both readers.** Add one check to the gate or to
      `tests/test_harness.py`: every relative path and `#anchor` linked from
      AGENTS.md and docs/*.md exists. This is what stops the new docs going stale,
      which is the failure mode `10-decisions.md` itself was written to fix.
