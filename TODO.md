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
224 memories across 176 places (194 before the 1.2 merge). 168 of those places
have coordinates, carrying 215 memories. 143 high confidence, 81 medium.
**Measured 2026-09-20**, not carried forward — the figures below had drifted
into four different denominators.

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

**92 of the 168 placed places sit on just 28 shared coordinate points**, and
121 of the 215 placed memories are on them.

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
4. ~~**Clustering is mandatory, not polish.**~~ **Done.** `groupByLocation`
   collapses a shared coordinate, and `precisionFor` loosens the grid with the
   zoom so Times Square is one countable cluster rather than 34 stacked dots.
   Past `CLUSTER_SPAN_M` a tap zooms instead of opening a sheet. This does not
   fix D.3 — the coordinates are still centroids — it only stops them being
   unreadable.

Reproduce: `SELECT ST_AsText(coordinates), count(*) FROM places WHERE coordinates
IS NOT NULL GROUP BY 1 HAVING count(*) > 1 ORDER BY 2 DESC;`

### Known defects, unowned

**Audited 2026-09-20.** Six of the nine entries here were already fixed and the
list was still claiming them, which is worse than having no list: an agent
reading it spends its afternoon re-fixing solved problems, and the one entry
that was outright false would have sent it hunting a ruff bug that does not
exist. Verify before trusting, and strike entries when you fix them.

- [x] **Semantic place duplicates** — 18 of 25 proposals reviewed and applied,
      194 places → 176, memories unchanged at 224. Gotham Comedy Club is one pin
      with 7 memories. The 7 rejected pairs and the reasoning are in 1.2.
- [ ] **Search is a sequential scan by construction**, and the obvious fix is
      not one. `to_tsvector(m.summary || ' ' || p.name)` spans two tables so no
      expression index can serve it — but rewriting it as
      `to_tsvector(m.summary) @@ q OR to_tsvector(p.name) @@ q` and indexing
      both does not help either: an OR across two tables still cannot use either
      index, because a row can qualify from the other side. That was built,
      measured against the live database, and reverted; the planner kept
      scanning.

      The two designs that would actually work:
      1. **UNION of two indexable branches**, one per table. Pure SQL, but
         ranking, `meta.total` and pagination all have to be rebuilt around it.
      2. **A `search_vector` column on `memories`**, trigger-maintained from the
         summary and the place name. One predicate, one GIN index, cross-field
         matching preserved — at the cost of keeping it in sync when a place is
         renamed.

      Neither is worth it yet: 224 memories scan in microseconds and no client
      calls this endpoint. `tests/test_api_search.py` came out of the attempt
      and is worth keeping either way — it pins the cross-field matching that
      both designs above would change.
- [x] **Endpoints with no consumer.** Settled by deletion: `/v1/places/{id}`,
      `/v1/places/{id}/memories` and `/v1/content/{id}/memories` had no app
      caller and no pytest, and were reached only by `api/test_api.sh` — which
      the gate never runs. The app now calls ten of the fourteen that remain.
- [ ] **`published_at` is always NULL** — yt-dlp flat extraction returns no
      timestamp for this channel (59 of 59 rows). Nothing serves it, so it
      blocks nothing.

#### Struck on audit — fixed, do not re-fix

- [x] **`meta.total` was wrong** on three endpoints. Fixed: `COUNT_WITH_TAGS_QUERY`,
      `SEARCH_COUNT_WITH_LOCATION_QUERY` and `PLACES_COUNT_QUERY` now mirror
      their result queries, and `tests/test_api_nearby.py` asserts it.
- [x] **No behavioural test of `/v1/memories/nearby`.** `tests/test_api_nearby.py`
      covers radius, contrast ordering, NULLS LAST, layer filtering and the card
      fields.
- [x] **`tests/test_app_config.py` PLACEHOLDER tripwire cannot fail.** It
      collects the unresolved placeholders and asserts the list is empty, under
      a strict xfail that carries the fact that today it is not.
- [x] **`EXTRACTION_MODEL` pinned to a deprecated model.** `pipeline/config.py`
      defaults to `claude-sonnet-5`.
- [x] **`redis` / `rq` declared but not installed.** Both import from the venv.
- [x] **The queue path would use the wrong prompt.** `pipeline/tasks.py` reads
      `source_type` from the Redis hash and passes `prompt_for(source_type)` and
      `layer_for(source_type)`.
- [x] **~~`ruff format` corrupts single-line tuple `except` clauses~~ — this was
      never ruff.** The rewrites to `except TypeError, ValueError:` were
      reproduced while running only `cp`, `sleep` and `md5`, with ruff nowhere
      near the tree, and traced to an editor watching the directory. No
      corruption ever reached a commit; the gate caught every instance at
      `compileall`. The entry is kept struck rather than deleted because the
      original was detailed and convincing, and somebody will otherwise rediscover
      the symptom and re-blame the formatter.

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

## Phase 1.5 — Proximity unlock

Asked for directly by the user, 2026-09-20: *"we need a unlock memory mechanism
- only nearby memories should be viewable. the unlock button should be pretty
and should be fun to press, like a game almost."*

Full flow in `docs/08-ux-flows.md` F7; button spec in `mobile/UI.md`. This
generalises 3.3, which scoped server-side proximity unlock to the friend layer
— the rule there (*a client-side gate is not a gate*) now governs every layer.

- [x] **1.5a Server-side gate.** The redaction is in `row_to_memory`, so
      search and `/v1/places/nearby`'s `sample_memory` are gated too — gating
      only the endpoint the app calls would have left two side doors.
- [x] **1.5b Unlock read.** `GET /v1/memories/{id}?at_lat=&at_lng=`. A refusal
      reports the distance, so the app can say how much further to walk.
- [x] **1.5c The control.** `mobile/src/UnlockButton.tsx`.
- [x] **1.5d Locked pins read as locked.** Grey out of reach, amber in reach,
      measured from the person and never from the map centre.
- [x] **1.5e Unlocks persist.** On the device, in `mobile/src/unlocked.ts`:
      the server re-locks you when you walk away, and the product must not.
      Readable from the **Unlocked** tab with no network and no position.
      "Forever" is a device promise — a new phone starts empty, and making it
      portable needs accounts. **Superseded:** unlocks are on the server now,
      keyed on the keychain device id, so clearing the app's data no longer
      undoes the walking. A new phone still starts empty.
- [x] **1.5f DECIDE the radius.** Option 3: only a coordinate no other place
      shares is gated, at 150m. That locks 94 of 215 placed memories across 76 places
      and leaves the centroid stacks open, because locking those would ask
      somebody to walk to a fiction. Full reasoning in F7.

Left for when the coordinates improve:

- [ ] **Re-gate on `precision_meters`** once extraction tells the truth about
      it (option 1 in F7). The uniqueness rule is a proxy for trustworthy
      coordinates; `precision_meters` is the direct measure, and nothing has
      re-run since W4-04 changed the prompt.
- [ ] **The position is self-reported.** This stops `curl`, not a determined
      spoofer. Attestation needs accounts — Phase 3, alongside 3.3. It now cuts
      both ways: a submission is also filed at a position nobody verified.

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

      **Merged 2026-09-20, by review rather than by rule.** `--only` was added
      so a human verdict can be executed: it takes `keeper:loser` pairs and
      refuses anything the current run did not propose, so the flag cannot be
      used to merge two rows the tool never suggested. 18 of the 25 were
      accepted; **194 places → 176, memories unchanged at 224, 0 orphans**, and
      6 keepers were flagged `geocode_status = 'conflict'` where the two rows'
      coordinates disagreed by more than 100m.

      The 7 rejected, which is the useful half — none of them is a tuning
      problem:

      | Proposal | Why not |
      |---|---|
      | bar French Quarter ← upscale restaurant French Quarter | two venues on one block |
      | Manhattan apartment building ← Manhattan apartment | generic; two stories, plausibly two apartments |
      | Irvine California ← Irvine California comedy club | a city and a venue inside it are different granularities |
      | New Jersey residential area ← airport gate boarding area | unrelated; the matcher simply failed |
      | Barry Park City Hudson River ← Hudson River New York City | a park is not the river |
      | Andaz West Hollywood ← Comedy Store Sunset Boulevard | the documented failure: two venues, one street |
      | Halifax comedy venue ← Lobster Pier 7 Halifax | two venues, one city |

      Four of the seven are the same shape: **two real venues that share a
      street or a neighbourhood**. No amount of token weighting separates those,
      because the distinguishing token is exactly the one the heuristic treats
      as rare-and-therefore-the-name.

      **Recommended fix, still needs a decision:** stop parsing one
      `place_query` blob. Have extraction emit structured fields — venue name,
      locality, region — so dedup is an exact match on venue+locality instead of
      a string heuristic. That is a prompt and schema change, not a better
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

- [ ] **2.0 Tiles, before this is public.** `api/embed.py` serves OSM's public
      tiles, which the OSMF policy forbids for this and which they can block
      without notice. Not fixed yet on purpose — the embed has no users and no
      public API host, so tiles are step four of a four-step problem. Options
      compared in `docs/09-visual-design.md`: Stadia Maps (one URL + a key, free
      tier, $20/mo per 1M credits) or Protomaps/PMTiles (~$3/mo on R2, no
      vendor). `TILE_URL` is one constant so either is a one-line change.
      **Blocks deploying the embed anywhere public.**

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
- [x] **2.4** Settle the consumerless endpoints. Three deleted; `/v1/memories/search`
      and `/v1/places/nearby` stay — search is the one the widget would want and
      both are tested.
- [ ] **2.5** Delivered-corpus export for a customer who wants the data rather
      than the embed. Never the raw extracted corpus — snippets, attribution and
      deep links only.

---

## Phase 3 — Friend layer

The retention bet. Only after the map has content — a proximity app that
returns nothing is dead, and a friend layer on an empty map returns nothing.

- [x] **3.1** Identity. `users` is a display name and a uuid claimed by a
      device; `identities` is Google and Apple sign-in on top of it. No
      passwords, no session tokens — the device id stays the only credential and
      signing in binds `devices.user_id`, so a second phone is a second device
      on one person. `api/auth.py` verifies signature, audience and issuer, and
      answers 503 rather than verifying against nothing when unconfigured.
      **Not exercisable yet:** needs real client ids and a development build —
      neither button works in Expo Go.
- [x] **3.2** Write path for user-created memories. `POST /v1/memories` plus
      `POST /v1/media` for a photo or a recording; `mobile/src/Submit.tsx` is
      the screen. Files where you are standing and nowhere else. No ingestion
      cap yet — see below.
- [x] **3.3** Proximity unlock enforced **server-side**, including for
      submissions: a memory somebody filed is gated the moment it exists,
      because their phone was at the coordinate. Never serialized, never sent.
- [ ] **3.4** Rendering separation. Friend and stranger content takes precedence
      wherever it exists and never renders at equal weight with historical cards
      in one feed. **Now urgent** — `stranger` stopped being hypothetical with
      3.2, and a dense point can hold both with no way to choose. See F4.
- [ ] **3.5** Rate limit the write path. Nothing caps how many memories one
      device can file, or how much it can upload. The brief asks for a hard cap
      on user-submitted ingestion and there is none; a loop fills the disk.
- [x] **3.6** **A dev seed, so the unlock can be exercised at all.**
      `pipeline/seed_dev.py`; `--clear` removes it. Before this it could not be,
      and setting the Simulator's location did not fix it.

      **Why it is broken.** The documented dev coordinate `40.7484,-73.9857`
      sits ~1.2km from the Duffy Square stack, the densest thing in the corpus —
      and that stack, like the other three big ones (~46 memories between them),
      is *deliberately* ungated, because they are model-guessed centroids and F7
      refuses to make anybody walk to a fiction. The 94 memories that are gated
      are by construction the scattered ones, on coordinates no other place
      shares, which is to say never near a round-number coordinate. So the sheet
      says "4.6 km" under "Get within 150 m" and there is nothing to be done
      about it from the Simulator.

      **Where to seed.** At `FALLBACK_REGION` — `mobile/App.tsx`, the same
      `40.7484,-73.9857` — which is already the no-permission map centre and
      already the coordinate every doc says to set. Three paths converge on one
      pair and there is no fourth place to write a coordinate down. Guard it
      with a parity test that reads the constant out of `App.tsx`, like the tag
      vocabulary test does.

      **How.** `pipeline/seed_dev.py` calling
      `pipeline.extract.save_memories(session, content_id, [dicts], layer=...)`
      — no network, no API key, and it writes `places` and `memories` correctly
      including tag cleaning — plus one `INSERT INTO content`. Idempotent on a
      fixed `content.url` of `memorylane://dev-seed` and places marked
      `place_query LIKE 'dev-seed:%'`; `--clear` removes both and stops.

      **What.** Six memories, one per branch the app can render: unlockable at
      ~40m; locked but walkable at ~400m; open-to-everyone by sharing a grid
      cell with a second place; stacked; submitted (`user_id` set, for the
      byline and the Report control); and one with a photo and a recording.

      **Two traps.** `is_gated` is true when `user_id IS NOT NULL` *or* no other
      place shares the 0.0001° grid cell — which is ~11m of latitude and ~8m of
      longitude at 40.7°N, so distinct gated coordinates need ≥ ~0.0002° of
      separation and must miss the existing 34 stacks. And *stacked but still
      gated* is *one place with three memories*: the app groups pins by
      coordinate while the gate counts places, so three places at one point
      would stack the pin and silently ungate all three. `save_memories` does
      `ON CONFLICT (place_query)`, so one place is the same `place_query` thrice.

      **Media with no new dependency.** The photo is a PNG written with `zlib` +
      `struct` at a few hundred pixels and the 4:3 aspect `MemoryMedia` renders
      — a 1×1 proves nothing about layout. The recording is macOS `say` piped
      through `afconvert` to real AAC, so the player has something that plays;
      there is no ffmpeg here. Skip the audio where those are absent.
- [x] **3.7** `EXPO_PUBLIC_DEV_LOCATION`, read only under `__DEV__`, so the
      Simulator's location stops mattering and a physical device can be told
      where it is too. `remember()` in `mobile/App.tsx` is the single chokepoint
      every position flows through, so the override goes there and
      `watchPositionAsync` is skipped when it is set. There is no `__DEV__`
      anywhere in `mobile/` today.

      It weakens nothing: the position is already self-reported — see
      `docs/10-decisions.md#the-position-is-self-reported` — so this makes lying
      convenient locally, not possible.
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
- ~~**Identity system for Phase 3.**~~ **Decided and built: OAuth only, Google
      and Apple.** No passwords to store, reset or leak, and Apple is required by
      App Store review once any third-party sign-in exists. What is left is
      operational, not a decision: register the OAuth clients, fill
      `GOOGLE_CLIENT_IDS` / `APPLE_CLIENT_IDS`, and make a development build.
- **Does the podcast corpus eventually get pruned?** It stays for now as test
  data. It is US comedy anecdote in a product about Copenhagen history, and at
  some point it stops being useful and starts being noise.
- ~~**`pipeline/geocode.py` is misnamed**~~ **Deleted.** Nothing imported it and
  it geocoded nothing; its one query is in CLAUDE.md's key queries now.
- ~~**Two tag vocabularies share one column.**~~ **Settled.** `pipeline/tags.py`
  is the single list; both write paths filter against it, the prompt reads it,
  and `008_one_tag_vocabulary.sql` renamed the four stored `sports`. The app's
  chips are a deliberate subset and a test holds them to it. Still open: four
  off-vocabulary tags the model invented before the filter existed
  (`entertainment`, `celebrity`, `theater`, `festival`, 15 rows) are harmless
  but unfilterable — decide on a mapping if a filter UI ever ships.
- **`api/test_api.sh` is not run by the gate.** It was the sole caller of the
  three endpoints deleted above, which is how they went unnoticed. Either wire
  it in behind a live-server check or accept that it is a manual tool.

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
