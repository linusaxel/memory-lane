# Memory Lane — TODO

This file is the source of truth. `loop/TASKS.yaml` is the executable contract
the `/ml-tick` loop runs against; it gets repopulated from whichever phase here
is active. If the two disagree, this file wins and TASKS.yaml is wrong.

---

## Current state

Audited 2026-09-20 against the running system, not the docs. Where the brief and
the code disagreed, the code won and it is called out below.

### The spine works, end to end

- [x] **Ingest** — `pipeline/ingest.py` reads `config/content.yaml` into
      `content`. Idempotent, dedups on normalized URL. A `channel:` source
      auto-discovers a back catalogue through `crawler/yt_crawler.py` (yt-dlp).
      Covered by tests against real PostGIS.
- [x] **Transcripts** — `pipeline/transcripts.py`, youtube-transcript-api into
      JSONB segments. Permanent failures (disabled / unavailable / no English)
      are distinguished from transient ones, which propagate and leave the row
      retryable.
- [x] **Extraction** — `pipeline/extract.py`. 4-minute chunks, 30s overlap,
      timestamps preserved. Claude returns place, summary, tags, confidence
      **and lat/lng directly**. Merge-within-60s, low confidence dropped.
      `pipeline/tasks.py` adds a Haiku pre-filter over RQ for parallel runs.
- [x] **Proximity API** — `api/main.py`, FastAPI + PostGIS `ST_DWithin`.
      Containerized, CORS lockable via `CORS_ORIGINS`, `/privacy` served,
      `railway.json` ready.
- [x] **Mobile app** — `mobile/`, Expo. One map screen, one sheet, one endpoint.
      Bundles clean for both platforms. Parked (see *Blocked on you*).
- [x] **Gate** — `loop/verify.sh`, tri-state GREEN/RED/INFRA. Runs compileall,
      ruff check + format check, pytest, and the app typecheck.
- [x] **Cross-video place dedup, exact match** — `db/migrations/001_places_unique.sql`
      plus a unique index on `places(place_query)`, so the `ON CONFLICT` in
      `save_memories()` finally fires. Verified on the live DB: 224 places
      collapsed to 194, all 224 memories intact — the `ON DELETE CASCADE` did
      not eat rows.
- [x] **One place for env knobs** — `pipeline/config.py`. Add new settings there.

### The data

59 content rows: 29 extracted, 25 pending extraction, 4 transcript-failed.
224 memories across 194 places, 186 with coordinates. 143 high confidence,
81 medium.

**All of it is a US comedy podcast.** Density is Manhattan, New Orleans and LA.
**Zero places within 20km of Copenhagen.** This corpus stays as end-to-end test
data under its existing `source_name`; it is not the launch corpus and nothing
in the roadmap builds on it.

### Against the brief — what does not exist

The brief's core concepts are absent from the codebase entirely. A full-text
grep for `contrast|historical|friend|stranger|arkiv|setlist|mediestream|copenhagen`
returns four incidental hits: a prompt saying "like you're telling a friend",
Docker build layers, and two pipeline-stage headings. Nothing to refactor.

- [x] **Layers, `happened_at`, per-memory attribution, contrast columns** —
      added in `722fd68` (W4-01). Columns only: nothing reads or writes them yet.
- [x] **Non-video ingestion** — `ingest_records()` in `0c9d699` (W4-03).
      Still no real source behind it; the adapter choice is W4-00, blocked.
- [ ] **Contrast scoring** — every query still orders by `distance ASC`. There
      is a column now but nothing fills it, and no source of "what is at this
      place now" to compute it from.
- [ ] **Screenshot-native cards** — the app sheet is functional, not designed to
      survive as a screenshot.
- [ ] Embeddable widget, auth, rate limiting, ingestion cost caps.

### Where the brief's "known v1 shape" is wrong

- **There is no geocoding stage.** The brief lists `… → LLM extraction →
  Geocoding → Query API`. Coordinates come straight out of the extraction call
  (`geocode_status = 'llm'`). `pipeline/geocode.py` is a stats script, not a
  stage, and its name misleads. `docs/05-geocode.md` documented a Google Places
  integration that was never built; it has been deleted, as has `docs/06-api.md`,
  which documented routes that never existed.
- **Precision and confidence match the brief exactly** — exact 50m / street 200m
  / neighborhood 1km / city 10km, and low confidence is filtered at extraction.

### The coordinates are mostly guesses, and they do not admit it

Found while building W4-02; every figure below re-verified independently
against the live database. This is the largest single problem in the corpus and
it reshapes several Phase 1 items.

**111 of 186 placed places — 60% — sit on just 34 distinct coordinate points.**

| Point | Places | Memories | What it actually is |
|---|---|---|---|
| `POINT(-73.9851 40.7589)` | 14 | 23 | Duffy Square, Times Square |
| `POINT(-90.0715 29.9511)` | 11 | 11 | New Orleans centroid |
| `POINT(-77.0369 38.9072)` | 5 | 6 | Washington DC centroid |
| `POINT(46.6753 24.7136)` | 5 | 6 | Riyadh centroid |

Fourteen unrelated venues share the Times Square point — Gotham Comedy Club,
Caroline's, New York Comedy Club, a radio studio, someone's apartment. The model
emits a city centroid whenever it does not know an address.

**It does not confess to doing so: 35 of those stacked places claim
`precision_meters = 50`.** "Exact" and "I guessed the city" are the same value in
this data, so `location_precision` is unusable as a confidence signal by anything
that filters or ranks on it.

Four consequences:

1. **Distance is anti-correlated with identity here.** Two places on an identical
   centroid are usually *different venues*, while one venue appears at two
   different points. This is the deeper reason W4-02 is blocked, beyond the
   name-matching failure.
2. **Structured venue/locality/region fixes matching but not placement.** After a
   perfect dedup, 60% of pins are still at a centroid. Putting a pin on the right
   building needs a real geocoder — the thing `docs/05-geocode.md` described and
   which was deleted as dead because it had never been built. Whether to build it
   is now a live question rather than a closed one.
3. **Contrast scoring (1.5) is undermined at the root.** "The gap between this
   memory and what is here now" cannot be computed for a point that is not where
   the memory happened. A jazz club that is now a bank lobby is the whole product;
   a jazz club pinned to Times Square is noise.
4. **Clustering is mandatory, not polish.** Neither answer to D.3 helps when 14
   places share a point — place-level pins turn 14 stacked memory-pins into 14
   stacked place-pins. Without clustering, Times Square is one unreadable dot.

Reproduce: `SELECT ST_AsText(coordinates), count(*) FROM places WHERE coordinates
IS NOT NULL GROUP BY 1 HAVING count(*) > 1 ORDER BY 2 DESC;`

### Known defects, unowned

- [~] **Semantic place duplicates.** Tool shipped, merge withheld — see 1.2.
      *Gotham Comedy Club New York City* (6 memories) and *Gotham Comedy Club
      Chelsea New York City* (1) are still one venue on two pins.
- [ ] **`meta.total` is wrong** on `/v1/memories/nearby`, `/v1/memories/search`
      and `/v1/places/nearby` — the count queries ignore active filters, and the
      places one returns page length.
- [ ] **Search cannot be indexed as written.** `to_tsvector(m.summary || p.name)`
      spans two tables, so no expression index can serve it and every search is
      a sequential scan. The predicate must be split into an `OR` first.
- [ ] **8 of 9 endpoints have no consumer.** `mobile/src/api.ts` calls only
      `/v1/memories/nearby`. Decided per endpoint in Phase 2.
- [ ] **No behavioural test of `/v1/memories/nearby`** — the single endpoint the
      app depends on. `tests/test_api_sql.py` proves every SQL constant is valid
      SQL; nothing asserts radius, ordering or filter semantics.
- [ ] **`tests/test_app_config.py` PLACEHOLDER tripwire cannot fail** —
      `assert isinstance(unresolved, list)` is a no-op.
- [ ] **`EXTRACTION_MODEL` is pinned to a deprecated model**
      (`claude-sonnet-4-20250514`). `CLASSIFIER_MODEL` has been corrected to
      `claude-haiku-4-5`; the extraction one has not.
- [ ] **`redis` / `rq` declared but not installed** in the venv, so
      `pipeline/worker.py` ImportErrors. The parallel path is untested locally.
- [ ] **`ruff format` corrupts single-line tuple `except` clauses in this
      repo.** It rewrites `except (TypeError, ValueError):` into
      `except TypeError, ValueError:` — Python 2, does not compile. The gate then
      fails at `compileall`, which is step 1, so it reports `GATE=RED syntax
      error` and never reaches the tests; a "GREEN, 176 passed" from before the
      save looks identical to a tree that now cannot import.

      Reproduce: write that snippet to any `.py` file under the repo root and run
      `venv/bin/python -m ruff format <file>`. **Not** reproducible in `/tmp`
      with this same `pyproject.toml` copied in, not the `.ruff_cache`, and not a
      stray config — something about this directory. ruff 0.16.8. Root cause not
      found and the search was called off as too expensive.

      Workaround, used in `_contrast_score`: keep the tuple exploded across lines
      with a magic trailing comma, which ruff preserves.
      `pipeline/tasks.py:73` already had that shape and was never affected.
      Two agents each "fixing" this file while the other saved cost real time —
      if the gate says syntax error at a line you did not touch, check this first.
- [ ] **The queue path would use the wrong prompt.** `pipeline/tasks.py` calls
      `extract_memories_from_chunk` with no prompt argument, so archival content
      run through the workers gets the personal "WHO / THE VIBE" prompt — an
      invitation to invent, on exactly the material that must not get one.
      Harmless while redis/rq are missing and nothing reaches it; `source_type`
      must be threaded down from `task_enqueue_chunks` before that path is used
      for anything but video. Marked at the call site.
- [ ] **`published_at` is always NULL** — yt-dlp flat extraction returns no
      timestamp for this channel. Nothing serves it, so it blocks nothing.

---

## Phase 0 — Design questions, ahead of Phase 1

**Provenance:** seeded 2026-09-20 by the cleanup session. The sequencing was
briefly reverted on the grounds that build-order is the user's call, which is
the right rule — but in this case the user had already made the call. Verbatim
instruction to that session: *"i wanna document some user experience flows and
build towards that, add to the todo if not already there - top of list."*

That is the ratification. Phase 0 sits ahead of Phase 1 because the user put it
there, not because an agent argued for it. D.1 and D.2 are delivered; D.3–D.5
are open and the user has not yet said whether Phase 1 waits on them — so treat
them as *first in line*, not as a hard gate that blocks W4-02 from proceeding in
parallel.

**The argument for doing them early, which is a good one:** every phase changes
what a person sees, and the repo had no written UI guidance at all — no tokens,
no flows, no note that a blank map fails store review. Phases 1, 3 and 4 each
add a *layer*, and nobody has decided how a layer is chosen on the map.

Seeded 2026-09-20:

- [x] **D.1 `mobile/UI.md`** — the tokens already in the code (zinc neutrals,
      `#dc2626` for the watch action only), the seven load-bearing rules, and a
      working recipe for seeing the app on a booted simulator with the location
      pre-granted. Linked from CLAUDE.md and README.
- [x] **D.2 `docs/08-ux-flows.md`** — F1 (discover nearby) and F2 (read a
      memory, open its source) documented as-built. F3–F6 stubbed as Proposed
      against the phases they belong to.

Open, and blocking a clean Phase 1:

- [ ] **D.3 Answer the four open questions** at the bottom of
      `docs/08-ux-flows.md`. The one that blocks the most: **does a pin
      represent a place or a memory?** Today it is a memory, so Gotham Comedy
      Club is six overlapping pins at one address. Place-level pins fix that but
      change what tapping means, and the answer shapes the layer UI in 1.x.
- [x] **D.4 Empty state is distinguishable from failure.** Was: `fetchNearby`
      accepted an `AbortSignal` that `App.tsx` never passed, so with no fetch
      timeout an unreachable API hung and the banner sat on "0 memories here"
      with a spinner forever — the error path never fired. Now an 8s timeout
      plus three states: "Finding memories…", "No memories here yet", and
      "Can't reach Memory Lane" with a Try again button. A failed refresh keeps
      the last good pins. Verified on the simulator in all four conditions,
      including Copenhagen, which correctly reads empty rather than broken.
- [x] **D.6 Stacked pins are reachable.** 23 memories at the Times Square
      centroid drew as one marker that opened an arbitrary one of them.
      `mobile/src/cluster.ts` groups by rounded coordinate, the marker shows a
      count, and the sheet pages through the stack. Mitigation, not a fix — the
      coordinates are still wrong; see the centroid section above.
- [ ] **D.5 Write F3 properly** once the historical source is chosen (W4-00).
      F3 is the product; it should not be specified by whatever the ingestion
      happens to produce.

---

## Phase 1 — Historical layer, one neighborhood

Copenhagen. Non-video ingestion, contrast scoring, proximity query, card design.
The goal is a map that is never empty in one neighborhood, ranked so the top
card is the one worth screenshotting.

- [x] **1.1 Schema, additive.** Reuse the existing four tables; no new entity
      model. `db/schema.sql` plus a migration under `db/migrations/`.
      - `memories.layer` — `historical | friend | stranger`, NOT NULL, default
        `historical`. Backfill the podcast rows.
      - `memories.happened_at` (DATE, null) + `happened_precision`
        (`day | month | year | decade`) — when it happened, distinct from where
        it sits in a video.
      - `memories.attribution` TEXT + `memories.source_url` TEXT — per-memory
        credit and a deep link, for the card and the legal posture.
      - `memories.contrast_score` REAL + `memories.contrast_note` TEXT.
      - `content.source_type` — `video | archive | newspaper | registry | …`, so
        the transcript flags stop being load-bearing for non-video rows.
      - Done in `722fd68`: `db/migrations/002_layers.sql`, applied to the live
        DB twice, 224 memories before and after. `tests/test_schema_layers.py`
        guards schema.sql/migration drift and was mutation-checked to confirm it
        actually fails.
- [~] **1.2 Semantic place dedup.** *Tool shipped, auto-merge deliberately
      withheld — `pipeline/dedup.py`, W4-02 is `blocked / NEEDS_DECISION`.*

      Two premises in the original plan turned out to be wrong, both measured
      against live data rather than argued:

      1. **Coordinates cannot be the signal.** The two *Gotham Comedy Club* rows
         sit **1.8km apart** while both claim 50m precision. "Collapse places
         whose coordinates fall within their combined `precision_meters`" would
         never have fired. The model disagrees with itself about where a venue
         is, so names are the reliable signal and distance is only a sanity
         bound.
      2. **Frequency cannot separate a venue from a location.** The rule needs
         to know which tokens name a place and which name an area, and the cheap
         way is "rare tokens are names, common tokens are locations". In a comedy
         corpus the *Comedy Store* recurs constantly, so `store` is classified a
         location and stripped — leaving `sunset boulevard`, which the Andaz
         hotel on the same street also has. The two then look like one venue.
         This is not tunable; it is the premise failing.

      Successive rules, measured on the 194-place corpus: naive token subset
      proposes **148** merges (absurd — it absorbs *"New Orleans Louisiana"* into
      the first venue it meets); adding frequency-based distinctiveness gives
      **39**; adding a city-level guard and a chain guard gives **25**, of which
      roughly a third are still wrong. Good enough to hand a human 25 pairs
      instead of 18,721 comparisons; not good enough to run unattended, and
      `--apply` has **not** been run against the live database.

      **Recommended fix, needs a decision:** stop parsing one `place_query`
      blob. Have extraction emit structured fields — venue name, locality,
      region — so dedup is an exact match on venue+locality instead of a string
      heuristic. That is a prompt and schema change in 1.4, not a better
      regex. Alternatively D.3 (place-level vs memory-level pins) may reduce how
      much this matters.

      Merge mechanics, when it is unblocked, follow `001_places_unique.sql`:
      repoint `memories.place_id` first, then delete orphans guarded by
      `NOT EXISTS` — `memories.place_id` is `ON DELETE CASCADE` and an unguarded
      delete eats memory rows.
- [x] **1.3 Source-agnostic ingestion.** `ingest_records()` in
      `pipeline/ingest.py` — a second entry point beside `ingest_content()`
      taking already-fetched records `{source_url, text, title?, happened_at?}`
      and writing `content` with `source_type != 'video'`. Callers fetch; this
      only writes. `source_url` becomes `content.url`, so the UNIQUE constraint
      there makes re-ingesting a no-op exactly as it does for videos.

      **Deviation from this plan, deliberate:** it does *not* bypass
      `transcripts` as written above. The body is stored as one transcript
      segment at `t=0`, which reads oddly for a newspaper clipping but means
      `chunk_transcript`, extraction and `save_memories` all work unchanged on a
      source with no timings. The alternative — a `content.body` column — needs
      a branch in the core extraction query for no gain. `transcripts` is really
      "source text, timings optional"; rename it if a source ever arrives that
      it genuinely cannot hold.

      The fixture is `tests/fixtures/copenhagen_synthetic.yaml`, invented and
      deliberately **not** in `config/`: once extracted, a memory row carries no
      marker saying it was made up, and invented history is the one thing this
      product must not ship. **The concrete source adapter is still not chosen**
      — see Open questions.
- [x] **1.4 A second extraction prompt, for archival text.** The existing
      `SYSTEM_PROMPT` is tuned for personal anecdote ("WHO / WHAT HAPPENED /
      THE VIBE") and is wrong for third-party material. The historical prompt
      must emit `happened_at`, and must reject static description ("this
      building was constructed in 1902") and Wikipedia-grade fact as hard as the
      current one rejects hypotheticals. Same JSON contract, same tag vocabulary.
- [x] **1.5 Contrast scoring.** `730b786`. A 0–1 `contrast_score` on a banded
      rubric plus a one-line `contrast_note` naming both sides of the gap. The
      prompt says **fame is not contrast** and uses the cathedral as the worked
      low-scoring example. `then` got no column — `contrast_note` carries both
      sides, so W4-01's schema stands. Scores clamp to [0,1]; anything
      unparseable stores NULL, and bool is rejected so `True` cannot become 1.0.

      **The OSM/Overpass enrichment pass is deliberately NOT built.** It assumes
      the coordinates point at the place, and 60% of them are city centroids, so
      it would confidently describe the wrong street corner. The score is
      LLM-only, from the source text. Revisit once geocoding is settled.
- [x] **1.6 Query.** `c4c60be`. Optional `layer`
      (`historical|friend|stranger`, **422** on anything else — a typo must not
      quietly serve friend memories to everyone), ordered by
      `contrast_score DESC NULLS LAST, distance_meters ASC`. `LAYER_FILTER` is a
      no-op when absent, so one query serves both cases. The response now carries
      `layer`, `happened_at`, `attribution`, `source_url`, `contrast_score` and
      `contrast_note`. `meta.total` respects the layer filter; the other count
      fixes landed in `b3a9189`.
- [x] **1.7 Card.** `fff53de`, built by the cleanup session.
      `GET /v1/memories/{id}/card`, server-rendered so a client cannot strip the
      attribution the legal posture depends on. One template for the app sheet,
      the Phase 2 widget and any pasted link.
- [x] **1.8 Tests.** `tests/test_api_nearby.py` in `c4c60be` — the first
      behavioural coverage this endpoint has ever had, despite being the only one
      the app calls. Radius exclusion, contrast beating distance, unscored
      sorting last, layer filtering and its effect on `meta.total`, 422 on a bad
      layer, and the card fields being served. The NULLS LAST assertion was
      mutation-checked: remove `NULLS LAST` and it fails.

**Phase 1 is done when** standing anywhere in the chosen Copenhagen
neighborhood returns at least one historical card, the top card is the highest-
contrast one rather than the nearest, and the card is worth screenshotting.

---

## Phase 2 — Embeddable map widget

First revenue surface. Same corpus, different rendering. Tourism boards,
audio-guide companies, city archives.

- [x] **2.1** `api/embed.py`. `/embed.js` is the paste-in snippet; it writes an
      `<iframe>` pointing at `/embed` and resolves the URL against its own
      `script.src`, so a customer pastes one tag and configures nothing. An
      iframe rather than DOM injection: their CSS cannot reach our map, ours
      cannot reach their article, and their CSP gets one origin to allow.
      **Leaflet, not MapLibre** — raster tiles need no style JSON and no vector
      tile provider, which is one fewer paid dependency before there is a
      customer. No Google Maps key on the web side either way.
- [x] **2.2** Reads `/v1/memories/nearby` and points the card iframe at
      `/v1/memories/{id}/card`, so the embed renders **no card of its own** —
      the credit cannot be dropped by the page hosting it, which is the reason
      the card is server-rendered at all. It opens the first result on load:
      that list is in contrast order, so the best card is the one a screenshot
      catches.
- [ ] **2.3** Per-customer `CORS_ORIGINS` and a per-embed key. **Blocked in
      practice on `DEPLOY`** — there is no public origin to allow yet.
      Also open: `TILE_URL` points at OpenStreetMap's public tiles, which their
      usage policy forbids for a customer's traffic. Swap for a paid or
      self-hosted tile source before anyone embeds this for real; it is one
      constant in `api/embed.py`. This is the first
      thing in the product with a customer attached, so it is also the first
      thing that needs a usage bound.
- [ ] **2.4** Settle the 8 consumerless endpoints: whatever the widget does not
      use gets deleted rather than maintained.
- [ ] **2.5** Delivered-corpus export for a customer who wants the data rather
      than the embed. Never the raw extracted corpus — snippets, attribution and
      deep links only.

---

## Phase 3 — Friend layer

The retention bet. Only after the map has content — a proximity app that
returns nothing is dead, and a friend layer on an empty map returns nothing.

- [ ] **3.1** Identity. The first time this product needs accounts at all.
- [ ] **3.2** Write path for user-created memories, with the brief's hard cap on
      user-submitted ingestion enforced server-side.
- [ ] **3.3** Proximity unlock enforced **server-side** — a friend memory outside
      the radius is never serialized, never sent, not merely hidden. A
      client-side gate is not a gate.
- [ ] **3.4** Rendering separation. Friend content takes precedence wherever it
      exists and never renders at equal weight with historical cards in one feed.
- [ ] Same neighborhood only. No second city.

---

## Phase 4 — Stranger notes

Density fix for the friend layer's sparsity, and the only layer that makes
people create rather than consume.

- [ ] **4.1** One note per place, visible to the next visitor only.
- [ ] **4.2** ~7-day decay, enforced at read time so an expired note cannot leak.
- [ ] **4.3** Moderation from day one, not bolted on: a pre-publish classifier
      pass and a report path that works before the first note exists.

---

## Phase 5 — Retention mechanics

- [ ] **5.1** Anniversary resurfacing.
- [ ] **5.2** Time-locked memories.

---

## Blocked on you

Not in the brief's structure, but these are real, they cost money or need an
account, and they must survive a context reset. Nothing in Phases 1–5 depends
on them. Full detail in `loop/STATE.md`.

- [ ] **`API_CREDITS`** — the extraction path has never been quality-checked
      against a real API; every test uses `FakeAnthropic`. **There is no
      `--limit` flag** — `python -m pipeline.extract` bills every pending video.
      To spend cents instead: `python -m pipeline.enqueue --video <content_id>`,
      then `--status <id>`. Eyeball 20 summaries for vividness. While in there,
      `EXTRACTION_MODEL` is still a deprecated ID and the system prompt is
      resent for every chunk with no `cache_control`.
- [ ] **`DEPLOY`** — Railway, ~$5/mo. Not Fly: Fly's managed Postgres has no
      PostGIS. **Also unblocks Phase 2**, which needs a public HTTPS origin.
- [ ] **`W3-13`** — look at the app in the iOS Simulator. Free, ~5 min. The
      old blocker is gone: the iOS 26.5 runtime is now installed and a simulator
      is booted. **Partially observed, not done.** The app has been run in Expo
      Go, which exercises the JS layer — map, pins, sheet, fetch — but Expo Go
      shows *its own* permission-prompt copy, not ours, and exercises no native
      manifest. Closing this needs a real build:
      `cd mobile && rm -rf ios && npx expo run:ios`.
- [ ] **`EAS_BUILD`** — three `PLACEHOLDER` tripwires to replace first; the
      bundle id is irreversible once submitted.
- [ ] **`STORE_ACCOUNT`** — Apple $99/yr, Play $25. If the Play account is
      personal rather than an organization, production access is gated behind
      **closed testing with 12 testers for 14 continuous days**. Start that the
      day EAS produces an `.aab`, not after everything else.

---

## Open questions

- ~~**Should the design questions run before Phase 1?**~~ **Answered.** The
  user asked for it at the top of the list in so many words. Phase 0 is first.
  What is *still* open is narrower: does Phase 1 **wait** on D.3–D.5, or run
  alongside them? Nobody has asked that, and the two are compatible — W4-02
  (semantic dedup) is backend work that D.3 informs but does not block.
- **Does a pin represent a place or a memory?** Today a memory, so Gotham Comedy
  Club is six overlapping pins at one address. Place-level pins fix that but
  change what tapping means. Shapes both W4-02 and the layer UI.
- **Which historical source first?** Deliberately undecided. The brief's
  priority order puts arkiv.dk / Københavns Stadsarkiv at #1, but it has no
  public API and would mean scraping; setlist.fm at #3 is a documented REST API
  with dense Copenhagen venue coverage and is the strongest contrast material
  available. Phase 1 builds the source-agnostic path so this can be answered
  late, but **items 1.3–1.6 cannot finish without an answer** — a hand-loaded
  fixture only carries them so far.
- **Reuse terms for arkiv.dk and Mediestream.** Unknown. The legal posture
  (short snippets, prominent attribution, deep links, behave like a search
  engine) assumes we may quote at all. Confirm before ingesting either.
- **Where does "what is there now" come from?** Contrast scoring needs
  present-day place identity. Working assumption is OSM/Overpass; unvalidated.
- **Which Copenhagen neighborhood?** "Saturate one neighborhood completely"
  needs a boundary drawn before density can be measured.
- **Identity system for Phase 3.** Nothing in the codebase has auth today.
- **Does the podcast corpus eventually get pruned?** It stays for now as test
  data. It is US comedy anecdote in a product about Copenhagen history, and at
  some point it stops being useful and starts being noise.
- **`pipeline/geocode.py` is misnamed** — a stats script, not a pipeline stage.
  Rename or fold into a CLI.

---

## Decided — do not revisit

Copied so they survive context resets.

**Non-goals — do not build:**
- Consumer subscription (converts at 1–3% on social apps)
- Ad product (needs millions of DAU)
- Multi-city launch
- Personal video archives as a source (GPS is already in EXIF, and people film
  the thing rather than narrating what happened there)
- Unmarked sponsored placement
- Generic Wikipedia-grade facts as primary content

**Design rules that are core, not polish:**
- **Contrast scoring** decides whether the product is interesting or wallpaper.
  Rank by the gap between the memory and what the user is looking at now, not
  by historical importance.
- **Screenshot-native cards** are the only distribution channel geo-gated
  content has. Place name and attribution visible, readable at thumbnail size.
- **Layer separation** — friend content is intimate and ephemeral, historical is
  public and permanent. Never equal weight in one feed; friend takes precedence.
- **Density over coverage** — saturate one neighborhood before adding a second.
- **Never re-extract** — extraction is a one-time, cached, amortized cost per
  place. Hard cap on any user-submitted ingestion.
- **Legal posture** — snippets, attribution, deep links to the source at the
  right timestamp. Behave like a search engine. Never sell the raw corpus.

**Monetization context** (not a build target): revenue comes from the historical
layer — embeddable maps and delivered corpora for tourism boards, audio-guide
companies, city archives. The social layer earns nothing for years, if ever.
Local business seeded memories are a later option and must be clearly marked.

**Decisions taken 2026-09-20:**
- TODO.md is the roadmap; `loop/TASKS.yaml` stays the executable contract and is
  repopulated from the active phase.
- Copenhagen is the launch area. The 224 US podcast memories stay as test data.
- The app track is parked; the human checklist above is preserved but no phase
  depends on it.
- Cards are server-rendered, one template, shared by every client.
- The first historical source is deliberately deferred.

**Rejected approaches — do not retry** (from `loop/STATE.md`): scraping channel
HTML for `"videoId"` (returns 0 for every channel; YouTube stopped serving it),
Homebrew Python 3.14 (broken `pyexpat`), expo-router / bottom-sheet / react-query
for a one-screen app, and shelling out to `pytest --collect-only` inside a test.
