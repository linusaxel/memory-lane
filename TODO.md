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

The podcast (`Tuesdays with Stories`): 55 content rows, 224 memories, 215 of
them placed. Across everything: 60 content rows - 30 extracted, 4
transcript-failed, 9 episodes pending extraction, and 16 pending clips the video
filter skips (under `MIN_VIDEO_MINUTES`). 22 clips were extracted before that
filter existed and probably duplicate their episodes' memories. 185 places, 177
with coordinates. The other 11 memories are the dev seed (7) and user
submissions (4). Extracted confidence: 150 high, 81 medium.
**Measured 2026-09-23**, not carried forward — the figures below had drifted
into four different denominators once already.

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
- [x] **Contrast scoring** — done in 1.5 (`730b786`) and ordered on in 1.6
      (`c4c60be`). This bullet went on saying "every query still orders by
      `distance ASC`" after it stopped being true, which is the exact failure
      the *Known defects* section below warns about. The remaining gap is not
      the score but what feeds it: there is still no source of "what is at this
      place now", so the score is LLM-only, from the source text.
- [x] **Screenshot-native cards.** The web card was done in the palette pass
      (`docs/09-visual-design.md`); the app sheet was the half still open, and
      the defect was structural rather than cosmetic: the place name sat above
      the scroll and the credit sat *inside* it, so any story long enough to
      scroll pushed the attribution out of frame. A screenshot is the only way
      geo-gated content travels, so that lost both the distribution channel and
      the legal posture at once. The credit is now a pinned strip above the
      actions (`styles.credit`), it owns the single hairline the three variants
      used to each carry, and it is skipped when there is nothing to credit.
      Rule 11 in `mobile/UI.md`.
- [x] Embeddable widget (2.1/2.2 — tiles still parked on `DEPLOY`), auth (3.1,
      Google and Apple), rate limiting and ingestion cost caps (3.5 — 20
      memories and 64 MB per person per day). Four things on one line, all four
      shipped; the only piece still open is the tile source, which needs an
      account rather than an afternoon.

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

      **Partially addressed, 2026-09-22.** `SEARCH_MEMORIES_QUERY` was joining
      `content`/`users` before the `LIMIT`, building a full page of wide rows to
      throw almost all of them away after the sort. A CTE now ranks a page of
      ids first and joins only for the survivors — 245ms→59ms measured at
      200k rows (`pipeline/perf.py`). This does not touch the seq-scan-for-
      ranking problem above; `ts_rank` still has to visit every matching row,
      which is what the two designs above actually fix. It just stopped paying
      the join cost for rows the scan was about to discard.

      **And still no client calls this endpoint, on purpose.** Traced this
      session: the search endpoint's `row_to_memory` call passes no viewer
      position, so it structurally cannot unlock anything, and the only
      memories it *could* surface unlocked are the vaguest, centroid-placed
      ones — the 121 of 215 the gate already treats as untrustworthy. Building
      search UI on top of it would be a feature that returns the corpus's worst
      data. See *Decided* below.
- [x] **Endpoints with no consumer.** Settled by deletion: `/v1/places/{id}`,
      `/v1/places/{id}/memories` and `/v1/content/{id}/memories` had no app
      caller and no pytest, and were reached only by `api/test_api.sh` — which
      the gate never runs. The app now calls ten of the fourteen that remain.
- [ ] **`published_at` is always NULL** — yt-dlp flat extraction returns no
      timestamp for this channel (59 of 59 rows). The INSERT path handles NULL
      fine; getting a real date needs either a per-video fetch (25 extra
      requests) or the channel RSS feed (newest 15 only). Nothing serves it, so
      it blocks nothing.
#### Struck on audit — fixed, do not re-fix

- [x] **`meta.total` was wrong** on three endpoints. Fixed: `COUNT_WITH_TAGS_QUERY`,
      `SEARCH_COUNT_WITH_LOCATION_QUERY` and `PLACES_COUNT_QUERY` now mirror
      their result queries, and `tests/test_api_nearby.py` asserts it.

- [x] **Memories tab had no ceiling.** Filed 2026-09-22 while splitting
      `mobile/src/Memories.tsx`'s Unlocked/My memories into subtabs; fixed the
      same day. Both subtabs now render through one `FlatList` instead of
      `ScrollView` + `.map()`, so a row only mounts once it scrolls into view.
      `/v1/me/memories` now takes `offset` alongside `limit` and answers with
      `meta.total` (mirroring `/v1/memories/nearby`'s shape), and the My
      memories subtab pages through it on `onEndReached` instead of stopping
      at whatever the first `limit` returned —
      `test_offset_pages_past_the_limit_instead_of_dropping_the_rest` covers
      it. `mobile/src/unlocked.ts` no longer keeps the collection as one
      growing JSON blob: each memory lives under its own `AsyncStorage` key,
      indexed by a small id list, so a normal unlock or edit writes one item
      key instead of rewriting everything ever earned; a one-time migration
      moves an existing install off the old blob key. Verified with
      `./e2e/run.sh f24` and `./loop/verify.sh`.
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
- [x] **~~The reach circle lags the person~~** (reported 2026-09-24). The blue dot
      moves smoothly; the circle around it jumps late, behind it. Likely causes,
      not yet measured:
      1. `watchPositionAsync` in `mobile/App.tsx` asks for
         `distanceInterval: 25` at `Accuracy.Balanced`, so the circle moves at
         most once every 25m - more than the 20m radius it draws. Its comment
         still argues from a 150m radius. The blue dot is MapKit's own and
         ignores all of this.
      2. On iOS any `Circle` prop change is `removeOverlay` + `addOverlay`
         (`AIRMapCircle.m`, `update`), the same thing that made the dashed
         route line stutter (docs/09 §3a), so even a finer interval redraws
         rather than slides.
      Try a finer interval (~5m, `BestForNavigation` while a route is active)
      first and see whether (2) is visible; if it is, the circle has to become a
      Marker-hosted view that can animate, or go. Battery cost of (1) is
      foreground-only, per UI.md rule 2.
      *Fixed 2026-09-24:* (1) - 5m at `BestForNavigation`, one setting rather
      than switching by stage. Watched on the simulator (Maestro `travel`,
      40m at 1.4 m/s, zoomed in): the circle stays within one 5m step of the
      dot, well inside the ring. (2) was not visible in still frames; reopen if
      it flickers on a real phone.

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

- [x] **D.3 Answer the four open questions** at the bottom of
      `docs/08-ux-flows.md`. All five are answered now, four of them by
      implementation rather than by argument: layers stack and are told apart by
      pin shape (F4); an empty area says so and no longer looks like a failure;
      contribution is in v1 (F5); **a pin is a *point*, not a place and not a
      memory** — neither original option survived the data, because one venue
      spans several place rows and several venues share one coordinate; and the
      app sheet duplicates the card rather than embedding it, because F16 has to
      work with no network, the unlock is native animation, and the attribution
      argument was met by the pinned credit strip instead.
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
- [x] **1.2 Semantic place dedup.** *Decided 2026-09-23: structured extraction
      fields. `pipeline/dedup.py`'s string heuristic (below) stays exactly as
      shipped, serving only places written before this change.*

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

      **Shipped 2026-09-23:** extraction now emits `venue`/`locality`/`region`
      instead of one `place_query` blob (`pipeline/extract.py`'s prompts), and
      `save_memories` keys its `ON CONFLICT` on an exact, case-folded match of
      `(venue, locality)` — `idx_places_venue_locality`,
      `db/migrations/016_structured_place_fields.sql`. New rows self-dedup at
      insert time; `pipeline/dedup.py` is unchanged and still serves the places
      written before this migration (not re-extracted — that costs API
      credits). `merge_nearby_memories` (in-process, pre-`save_memories`) was
      repointed at the same key since it also read `place_query`. See
      `docs/10-decisions.md`'s "Place dedup matches on names, not coordinates"
      2026-09-23 follow-up, and `loop/TASKS.yaml`'s W4-02.

      Merge mechanics for `pipeline/dedup.py`'s legacy path are unchanged, and
      still follow `001_places_unique.sql`: repoint `memories.place_id` first,
      then delete orphans guarded by `NOT EXISTS` — `memories.place_id` is
      `ON DELETE CASCADE` and an unguarded delete eats memory rows.
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
- [x] **2.5** Delivered-corpus export. `pipeline/export.py`, a CLI and not an
      endpoint — there is no customer and no public host, and an
      unauthenticated bulk route is the one thing the legal posture forbids.
      Three rules are enforced in the module rather than left to the caller:
      **snippets** (180 chars or the first sentence, always marked when cut),
      **historical only** (a memory somebody filed is theirs, and nothing in the
      submit flow consents to selling it), and **no row without both an
      attribution and a link** — a row that cannot say where it came from is not
      ours to hand over. The deep link is imported from `api/card.py` rather
      than reimplemented, because two copies of the attribution link is the
      drift this posture cannot afford.

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
- [x] **3.4** Rendering separation, both halves. The *map* half was F4's pin
      shapes (`layerOf` in `cluster.ts`); the *list* half was still flat —
      `/v1/memories/nearby` ordered by contrast alone, so a well-scored podcast
      anecdote sorted ahead of a note somebody left at the same point.
      `LAYER_ORDER` now leads the ORDER BY: friend, stranger, historical, ahead
      of contrast, and the sheet pager inherits it because the pager is the
      API's order. Contrast still decides within a layer, asserted both ways.
      `/v1/memories/search` stays on rank — somebody who typed a word asked for
      that word.
- [x] **3.5** Rate limit the write path. 20 memories and 64 MB of upload per
      rolling day (`DAILY_MEMORY_LIMIT`, `DAILY_UPLOAD_BYTES`), counted per
      **user** rather than per device so a second phone on one account is not a
      second allowance. The check runs in its own transaction, so a refusal
      rolls nothing back. It is a bound and not a defence — the device id is
      self-issued, so a determined loop mints a fresh identity per request; this
      stops the stuck client that fills the disk, which is the failure that
      actually happens.
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
- [ ] Same neighborhood only. No second city. *Not a task — a standing rule,
      left unticked on purpose. It is only satisfiable by not doing something,
      and it stops being true the day somebody adds a source outside Copenhagen.*

---

## Phase 4 — Stranger notes

Density fix for the friend layer's sparsity, and the only layer that makes
people create rather than consume.

**Read 3.2 before this section.** Phase 4 was written before user submissions
existed, and 3.2 answered the same question differently: a submission lands in
the `stranger` layer and is **permanent**. That is not a tuning difference. 4.1
and 4.2 are parked on it rather than attempted — see `P4-01` in
`loop/TASKS.yaml` for the three ways out and why each is a person's call, not an
agent's.

- [ ] **4.1** One note per place, visible to the next visitor only. **Parked:**
      the stranger layer already exists and its rows are kept, not consumed.
- [ ] **4.2** ~7-day decay, enforced at read time so an expired note cannot
      leak. **Parked:** expiring a stranger memory would delete, from its
      author's own collection, the thing they walked somewhere to write — and
      1.5e calls that collection a promise. The read-time half of the design is
      right and survives whichever way the product question is answered.
- [~] **4.3** Moderation from day one, not bolted on. **Half shipped with 3.2:**
      the report path exists, works before anything is posted, and hides a
      memory from every endpoint at `REPORT_THRESHOLD` distinct devices. The
      pre-publish classifier is the missing half, and it spends credits on every
      submission — `API_CREDITS`, and not obviously worth it while three reports
      take something down in minutes.

---

## Phase 5 — Retention mechanics

- [x] **5.1** Anniversary resurfacing. `ANNIVERSARY` in `api/queries.py` marks
      a memory whose `happened_at` shares today's day-and-month, and it sorts
      above contrast and below layer. That ordering *is* the feature: there are
      no notifications in this product, so the only way a date can surface
      anything is by putting it at the top of the list somebody is already
      looking at. The flag travels on locked memories too, like `media_count` —
      it is a reason to walk over and gives away nothing the pin did not. The
      sheet says "on this day" in the meta row, with no accent, because the
      seal means openable and nothing else gets it.
      **Nothing in the corpus has a `happened_at` yet**, so this is live code
      over empty data until an extraction run happens (API_CREDITS) or somebody
      files a submission with a date.
- [x] **5.2** Time-locked memories. `memories.opens_at` (DATE,
      `009_time_locked.sql`), `not_yet_open` at the **top** of `is_locked`, and
      "Who can read it → Nobody until <year>" on the submit sheet. Full flow in
      `docs/08-ux-flows.md` F23.

      The gate is checked ahead of position because every existing way of
      opening a memory is a way this could have leaked: standing on the spot,
      the collection (which forces a memory open by handing it its own
      coordinates), the unlock endpoint, and the card (which keeps its own copy
      of the query and needed the column adding). Four doors, one check, and a
      fifth inherits it. `tests/test_api_timelock.py` walks all four, and the
      check was mutation-tested — remove it and exactly those four fail.

      A DATE and not a timestamp: "opens on 3 May 2031" is what a person means,
      and a time of day would invite a timezone argument nobody needs. The app
      parses the ISO string by hand rather than through `new Date`, which reads
      a bare date as UTC midnight and prints the day before it west of
      Greenwich.

---

## Blocked on you

Not in the brief's structure, but these are real, they cost money or need an
account, and they must survive a context reset. Nothing in Phases 1–5 depends
on them. Full detail in `loop/STATE.md`.

- [ ] **`API_CREDITS`** — the extraction path has never been quality-checked
      against a real API; every test uses `FakeAnthropic`. **There is no
      `--limit` flag** — `python -m pipeline.extract` bills every pending video.
      To spend cents instead: `python -m pipeline.enqueue --video <content_id>`,
      then `--status <id>`. Eyeball 20 summaries for vividness. The model ID
      (`claude-sonnet-5`) and prompt caching are already fixed; what has never
      met the real API is the structured-output schema (`MEMORY_SCHEMA`), so a
      rejection shows up on the first chunk. Suggested order once funded: one
      video, `quality --compare` against the old prompt, the 9 pending
      episodes, `review`, then `classifier_audit`.
- [ ] **`DEPLOY`** — Railway, ~$5/mo. Not Fly: Fly's managed Postgres has no
      PostGIS. **Also unblocks Phase 2**, which needs a public HTTPS origin.
- [x] **`W3-13`** — **done 2026-09-21, natively.** `npx expo run:ios` built,
      installed and launched the real app on an iPhone 16 Pro, and four states
      were screenshotted: our own permission primer (not Expo Go's), the pinned
      credit strip with a byline, the same strip with a `SourceLine`, and the
      sealed composition refusing to open at 128m — inside the unlock radius,
      which is the whole of what F23 claims.

      **It found a real defect that only a native build could.** See the iOS
      half of rule 2 in `mobile/UI.md`: expo-location was injecting always-on
      location and motion purpose strings, in its own boilerplate, into an app
      that asks for neither. Fixed and tested.

      Two things came out of making it repeatable, and both stay:
      `EXPO_PUBLIC_DEV_OPEN_MEMORY` opens one memory's sheet on launch (there is
      no tap automation on this simulator, so until now every sheet change was
      verified by `tsc` and nothing else), and the dev seed grew a sealed
      memory so F23 has something to render.

      The task itself stays `blocked` in `loop/TASKS.yaml` on purpose: its
      `verify` is `MANUAL`, and the contract reserves `done` for machine-checked
      proof. A screenshot is not an exit code. `W3-16` carries what is testable.
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
- ~~**Does a pin represent a place or a memory?**~~ **Answered in D.3:** neither
  — a pin is a *point*. One venue spans several place rows and several venues
  share one coordinate, so `cluster.ts` groups by coordinate.
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

## Ideas — founder brainstorm, unvetted

Seeded 2026-09-22 from a founder brainstorm dump, elaborated into small,
buildable increments. **Unvetted** — none of this has been through the
audit/measurement process the rest of this file uses. Three items conflict
with rules already marked *Decided* below; flagged inline rather than dropped
or silently overridden.

- [x] **Static logo mark.** Done: `mobile/assets/logo-mark.svg` (winding path
      + wind-gust accent, ink on paper) rasterized by
      `mobile/scripts/generate-app-icons.mjs` into the app icon, light/dark
      splash (new `expo-splash-screen` config plugin — none existed before),
      Android adaptive-icon layers, and favicon. Also fixed two leftover
      Expo-template colors that contradicted the decided palette while
      touching this config: `android.adaptiveIcon.backgroundColor` and
      `primaryColor`.
- [x] **Animated startup logo.** Done: `mobile/src/StartupLogo.tsx` draws the
      three logo-mark paths on once via `strokeDashoffset` (750ms, JS driver),
      shown while `App.tsx` holds the native splash
      (`SplashScreen.preventAutoHideAsync`) through font loading and the
      animation, then hands off with `hideAsync`. No native splash-hold call
      existed before this — the "while the splash screen holds" premise
      needed it added, not just the animation.
- [x] **Resolved 2026-09-22: warm accent, not a reskin.** Was flagged as
      conflicting with `docs/09-visual-design.md`'s decided muted-parchment
      palette. **Decision:** hybrid, not a reversal — the map-legibility and
      contrast work behind that palette solves real problems (rule 1's map
      pop, accessibility contrast) and stays. The "cozy, peaceful walk"
      feeling moves into the *accent* only: replace `seal` red with a warm
      moss/ochre tone (re-run the same contrast measurement `mobile/UI.md`
      already did for `seal`), and let the logo/splash carry the warmth. No
      change to the map style, card layout, or type system. If this doesn't
      read as warm enough once built, revisit — but don't reopen the whole
      palette to find out.
      **Done 2026-09-23:** `seal`/`sealSoft`/`sealDeep` (`mobile/src/theme.ts`)
      moved from a stamp red to a warm ochre ramp, re-measured against the
      same AA bar `mobile/UI.md` already held `seal` to (every pair holds
      more margin than the red version did). The two places that cannot read
      `theme.ts` directly — `api/card.py`'s `--accent` copy and the two
      hardcoded map-`Circle` colours in `App.tsx` — were updated with it, so
      `tests/test_palette.py`'s drift check still passes. The logo/splash
      "carry the warmth" half needed no new work: `mobile/src/StartupLogo.tsx`
      and the static logo mark are ink-on-paper strokes with no accent color
      in them at all, so their warmth was always in the mark's shape, not a
      hue - already shipped in the earlier logo commits.
      - Parked, not built: a separate "urban/city" theme variant. Speculative
        second theme before the first one has a second neighborhood
        (Copenhagen) — YAGNI until Phase 1 ships.
- [x] **Route polyline on the map.** Stale checkbox — already shipped in
      commit `ba61806` alongside the daily route itself: `App.tsx`'s
      `Polyline` through `routeShown`'s stops, dashed and low-opacity to stay
      quiet under the pins. Found while picking the next item off this list;
      corrected rather than left claiming open work that was already done.
- [x] **Start-route affordance.** Done: the existing route pill in `App.tsx`
      now has two states, purely local (`routeStarted`, nothing server-side).
      Tapping it the first time flies the camera to the nearest not-yet-earned
      stop in route order and flips the pill's label to "Next: {place}";
      tapping again re-centres on the new next stop. Once every stop is
      earned it reverts to the summary label and re-fits the whole route, the
      old behaviour, as a small completion view.
- [x] **Route-complete moment.** Done: `App.tsx`'s `unlock()` fires
      `UnlockButton`'s own success haptic
      (`Haptics.notificationAsync(...Success)`) a second time when the memory
      it just confirmed was the last not-yet-earned stop of a started route -
      same signature, no new mechanic, composes with the start-route
      affordance's `routeStarted`/`nextRouteStop` (commit `1daec1e`) rather
      than tracking route progress a second way.
- [x] **Configurable route distance.** Done: `GET /v1/routes/today` takes an
      optional `radius_meters` (500-20,000, `ROUTE_RADIUS_METERS`'s default
      when omitted), used only on the day's first call and stored on the
      `daily_routes` row (`db/migrations/014_route_radius.sql`) alongside the
      picked stops, so a later call in the same day sees the radius that
      actually produced the route rather than whatever it asks for next. No
      settings screen - a UI control can point at the param later.
      **Superseded 2026-09-23:** the plan page's slider sends `budget_meters`
      and the radius is half of it; `radius_meters` is gone (migration 022).
      - Parked: weighting a route toward "more nature" / "more historical" /
        "more friends' memories". Meaningless until a route has more than one
        layer with real density to choose between (today only the historical
        podcast corpus and dev-seed data exist) — revisit alongside Phase 3/4
        density work.
- [ ] **⚠️ Conflicts with a decided rule, and duplicates existing fields.**
      "Memories should only contain picture / date / description / link to
      source." The schema already carries less than the brainstorm assumes on
      the display side (the card is one template, `api/card.py`, already
      minimal — see 1.7) but the *data* model — `layer`, `tags`,
      `contrast_score`, moderation (`hidden`, `reports`) — is called out under
      "Decided — do not revisit" as **core, not polish**. Reducing the model to
      four fields would mean dropping layer separation and contrast ranking,
      the two things that section says decide whether the product is
      interesting at all. If the actual complaint is that a *specific* card
      or screen shows more than picture/date/description/link, name which one
      — that's a display fix, not a schema change.
- [ ] **Mass-sourcing candidates.** x/Twitter, Reddit, free books/literature —
      these are candidate answers to the existing open question "Which
      historical source first?" (`TODO.md` Open questions, above), not a new
      question. Added there as options alongside arkiv.dk/Mediestream/
      setlist.fm rather than duplicated here. Same caveat already written for
      that question applies to each: check reuse/ToS terms before ingesting
      (Reddit and X both meter or restrict API access; free-literature sources
      like Project Gutenberg have no per-venue coordinates, so a source
      contributing to *this* product still needs a place attached to each
      excerpt).
- [ ] **Onboarding stays minimal — verify, don't build.** Sign-up is already
      about as small as this gets: no forms, no passwords — a device id is
      minted locally and Google/Apple sign-in (3.1) is optional, only needed
      to survive a new phone. The one real onboarding moment is the location
      permission primer (`docs/08-ux-flows.md` F8/F9,
      `mobile/UI.md` "Asking for location"), already built and reasoned about.
      Nothing to add here unless a specific step in that flow is the
      complaint — name it and it becomes a normal bug, not a todo.
- [x] **Heart/favorite a memory.** Done: `memory_hearts(memory_id, device_id)`
      (`db/migrations/015_memory_hearts.sql`), a join table rather than a
      counter column so a device can't inflate a count by re-hearting.
      `POST /v1/memories/{id}/heart` (`api/write.py`) is one-way like unlocks
      and reports — no un-hearting, no DELETE. `heart_count` threads through
      `MEMORY_COLUMNS` into every memory-shaped read, locked included, same
      as `media_count`/`anniversary`. Mobile: a heart control in
      `MemorySheet.tsx`'s action bar, shown only once a memory is open, with
      a local `hearted.ts` cache so the glyph starts filled on relaunch.
      Ordering unchanged — `contrast_score`/`layer` stay the sort keys
      (Decided, above); heart count as a ranking signal is still a later
      decision, not this one.
- [x] **Resolved 2026-09-22: subscription is a second track, not a
      replacement.** Was flagged against the Non-goal ruling out consumer
      subscription. **Decision:** both are monetization goals — B2B
      (historical-layer embeds/corpora) stays the near-term plan Phase 2
      builds toward; a consumer subscription is added as a later goal once
      there's a userbase worth charging, not a reason to re-scope Phase 2.
      Non-goals list updated below. No build work implied yet — there is no
      userbase and no priced feature to gate; revisit once Phase 3 has real
      usage to look at.
- [x] **Resolved 2026-09-22: streak + proximity notification, reopened.**
      Was flagged against `docs/11-memory-types.md`'s "no notifications, no
      streaks, no gamification chrome" rule and `mobile/UI.md`'s
      foreground-only location constraint. **Decision:** build both. Both done:
      - [x] **Streak.** Done, and cheaper than planned: no stored counter,
        so there is no `users.streak_count`/`streak_date` to keep in sync
        across a device's siblings. `api.accounts.current_streak` counts the
        distinct calendar days `unlocks` has a row for this account, back
        from today, stopping at the first gap. Filing a memory or finishing a
        route already write an unlock, so both extend it for free. Surfaced
        in `Settings.tsx`'s stat row once above zero, same convention as
        "filed". See F27, `docs/08-ux-flows.md`.
      - [x] **Proximity notification.** Done: on-device geofencing
        (`geofence.ts`, `expo-location`'s `startGeofencingAsync` +
        `expo-task-manager`) firing a **local** notification
        (`expo-notifications`, no APNs/FCM, no push server) when a still-locked
        stop on today's route comes into range. Off by default — a new
        "Notify me when a memory is nearby" toggle in Settings, which is what
        asks for background location, not app launch. `mobile/UI.md` rule 2,
        `app.json` (`isAndroidBackgroundLocationEnabled`, a real
        `NSLocationAlwaysAndWhenInUseUsageDescription` string),
        `tests/test_app_config.py`, and both privacy-policy copies
        (`api/privacy.py`, `mobile/store/privacy.md`) all updated together.
        See F28, `docs/08-ux-flows.md`.
        - Not done: a real device confirming background delivery end to end,
          and the human-side App Store Connect / Play Console privacy
          disclosure updates that go with a new background permission — see
          `mobile/UI.md` rule 2 and `loop/STATE.md`'s parked table.
      `docs/11-memory-types.md`, `docs/10-decisions.md` and `mobile/UI.md`
      updated to mark the old rule superseded rather than left contradicting
      this.
- [x] **Tab bar delimiters.** Done: `mobile/src/TabBar.tsx` gets a `color.rule`
      hairline between each pair of tabs (1×24, centred) — the same token the
      bar's own top border already uses, so no new colour and no new
      dependency.

---

## Ideas — from the Ghostpost write-up (2026-09-23)

Sourced from Divya Venn's Ghostpost post-mortem
(https://divyavenn.com/about/ghostpost): a scraping + LLM pipeline that
learned from what users skipped and edited. **Unvetted**, but every entry was
checked against the code, not only the post. Its social-platform-specific
parts (prompt baking, cookie export, burner-account pools, a CDP desktop
daemon) have no analogue here and are left out.

#### Defects found while mapping — do these first

- [x] **A transient API error silently deletes a chunk, and the video is still
      marked extracted.** `extract_memories_from_chunk` (`pipeline/extract.py`)
      catches every `Exception` and returns `[]`, so a `RateLimitError`, a 529
      Overloaded or a dropped connection is indistinguishable from "this chunk
      has no memories". Both the sequential and the queue path then set
      `memories_extracted = TRUE`, and *Never re-extract* makes the loss
      permanent. Fix: let `RateLimitError`, `APIConnectionError` and 5xx
      `APIStatusError` propagate so the video stays pending; keep `[]` only for
      an unparseable reply. Check: a stub client raising 529 must leave the
      row pending.
      **Done 2026-09-23:** `TransientAPIError` (`is_transient`: connection,
      429, 5xx) is raised instead of `[]`; `extract_all_pending` leaves the
      video pending and moves on, and the queue path's extract job gets an RQ
      `Retry` so it still aggregates. `tests/test_extract_errors.py`.
- [x] **One crash rolls back a whole run's paid extractions.** `get_session()`
      (`pipeline/db.py`) commits once, on exit, and `extract_all_pending` and
      `fetch_pending_transcripts` each run their entire loop inside one
      session. Ctrl-C on video 50 of 55 throws away 49 videos of billed output.
      Commit per video — the post's "progress had to survive partially".
      **Done 2026-09-23:** both loops commit per row, and a failed video rolls
      back only itself. `test_a_crash_keeps_the_videos_already_extracted`.

#### LLM output

- [x] **Keep every chunk's raw model output.** Something like
      `extraction_chunks(content_id, chunk_index, prompt_hash, model, response)`,
      written as each chunk returns. The queue path already holds this in
      Redis and `redis.delete`s it after aggregation (`pipeline/tasks.py`).
      Kept, it makes re-merging, re-filtering and prompt comparison free, and
      it is the dataset the next four entries need.
      **Done 2026-09-23:** `extraction_chunks` (`db/migrations/017_extraction_chunks.sql`),
      written by `extract_chunk_stored` on both paths and committed per chunk,
      keyed on sha256(video, model, system prompt, user message), with
      `prompt_hash` for grouping by variant. A retried video only pays for the
      chunk it lost: `test_a_retried_video_only_pays_for_the_chunk_it_lost`.
- [x] **Structured output instead of `json.loads` + fence stripping**, for the
      extractor and the Haiku classifier both (tool use with an input schema).
      Removes the extractor's silent `[]` on malformed JSON and the
      classifier's "can't parse → assume yes".
      **Done 2026-09-23:** native structured outputs (`output_config.format`,
      JSON schema) rather than tool use, so replies stay JSON text and
      `extraction_chunks` keeps its shape. One `MEMORY_SCHEMA` serves both
      prompts (archive-only fields optional), `CLASSIFIER_SCHEMA` for Haiku;
      fence stripping deleted. A non-billing 400 now stops the run
      (`ModelUnusableError`) instead of returning `[]`, because an unsupported
      schema would be rejected on every chunk. **Not yet sent to the real
      API** — the balance is empty — so the first funded run is the schema's
      real test. `tests/test_extract_schema.py`.
- [x] **Log the classifier's verdicts** (chunk, has_memories, reason). Today a
      skipped chunk leaves no trace (`classify_chunk`, `pipeline/tasks.py`), so
      the pre-filter's false-negative rate is unknowable. Then run the
      extractor over a small sample of rejected chunks and count what it
      dropped. The post's lesson: what gets ignored is as informative as what
      gets used.
      **Done 2026-09-23:** `classifier_verdicts`
      (`db/migrations/018_classifier_verdicts.sql`), written by
      `task_classify_chunk` via `record_verdict`, chunk text included.
      `classify_chunk` now returns `(verdict, reason)`; a fail-open is
      `True` with a `fail-open:` reason so it is never read as a judgement.
      `python -m pipeline.classifier_audit --sample N` re-extracts a stable
      sample of rejections through `extract_chunk_stored` and reports how many
      held a memory the pipeline keeps. Not run: nothing has been classified
      on this database yet, and it bills.
- [x] **A review loop that turns extractions into a golden set.**
      Accept / reject / edit over new memories, same propose → `--only` shape
      as `pipeline/dedup.py`. An edit is a before/after pair, a reject a
      negative, and the edit rate over time is the quality number (the post's
      answer to "how do you know it improved"). `pipeline/quality.py`'s
      regexes stay as the cheap first pass.
      **Done 2026-09-23:** `python -m pipeline.review` lists unreviewed
      extracted memories with their `quality.py` flags; `--accept`,
      `--reject` (also hides it) and `--edit ID "text"` record verdicts in
      `memory_reviews` (`db/migrations/019_memory_reviews.sql`); `--stats`
      is the changed-share by extraction month. Reviews are `ON DELETE SET
      NULL`, so reprocessing a video keeps them, and a re-review keeps the
      model's original `before`. `tests/test_review.py`. Nothing reviewed yet:
      the ~50 rows the parked few-shot entry below waits for are a human's
      afternoon.
- [x] **Candidate generation for prompt changes.** `pipeline/quality.py
      --compare` runs two prompt variants over a fixed sample of stored chunks,
      scores both with `quality.report()`, and shows them side by side for a
      human to pick — instead of one-shot prompt edits. Blocked on credits
      (the balance is empty).
      **Built 2026-09-23, not yet run:** `python -m pipeline.quality --compare
      candidate.txt [--baseline old.txt] [--sample 10]`. The sample is rebuilt
      from `transcripts` with `chunk_transcript` (`extraction_chunks` holds
      replies, not chunk text) and ordered by a hash, so it is the same chunks
      every run. Both sides go through `extract_chunk_stored`: a rerun costs
      nothing, and so does a baseline the pipeline has already extracted
      under the same prompt. Picking a winner is left to the person reading it.
      `tests/test_quality_compare.py`.
- [ ] **Parked: retrieve few-shot examples instead of hard-coding three.**
      Pick examples from the golden set by source type and topic rather than
      the fixed ones in `SYSTEM_PROMPT`. Not worth it until the review loop
      has ~50 reviewed rows.
- [ ] **Revealed-preference report.** `unlocks`, `memory_hearts` and `reports`
      are already per-memory behavioural signals. A `quality.py --signals` view
      that checks whether the regex flags predict hearts and reports. Means
      little before there are real users, but it is one query.
      **Parked 2026-09-23:** the local DB has 3 unlocks, 0 hearts, 0 reports -
      nothing to correlate. Build it once hearts and reports come from people.

#### Scraping / ingestion

- [x] **Filter at the video level before fetching a transcript.** The Haiku
      filter runs per chunk, after the transcript is fetched and chunked.
      yt-dlp's flat listing (`crawler/yt_crawler.py`) already has title and
      duration — skip Shorts, trailers and compilations there. Cheap work
      first, expensive work only for survivors.
      **Done 2026-09-23, and the premise was wrong:** `/videos` carries no
      Shorts. What it does carry is clips — two thirds of the listing, all
      under 17 minutes, each re-telling a story from an episode that runs
      60+. `content.duration_seconds` (`db/migrations/020_content_duration.sql`)
      from the flat listing, and both pending queries skip anything under
      `MIN_VIDEO_MINUTES` (20); unknown durations are never filtered.
      `--refresh-sources` backfills it: on the live DB 16 pending clips are now
      skipped and 10 episodes remain. **22 clips were extracted before this**
      and their memories likely duplicate their episodes' — not touched; worth
      a look through `pipeline/review.py` or `pipeline/dedup.py`.
      `tests/test_video_filter.py`.
- [x] **Transcripts: stop on an IP block, and allow a proxy.** The existing
      `ponytail:` note in `pipeline/transcripts.py` names the ceiling: once
      YouTube blocks the IP, every run re-hits every pending row. Detect
      `RequestBlocked`/`IpBlocked` and abort the run, add a small jittered
      delay between fetches, and an optional `TRANSCRIPT_PROXY` in
      `pipeline/config.py` (youtube-transcript-api takes a `proxy_config`).
      The post's rule: don't concentrate traffic on one IP.
      **Done 2026-09-23:** `RequestBlocked` (and its `IpBlocked` subclass)
      stops `fetch_pending_transcripts` on the first hit with
      `error: "blocked"`, every row left pending; `run_all` reports it on the
      Transcripts line and still runs extraction, which never touches YouTube.
      `TRANSCRIPT_PROXY` becomes a `GenericProxyConfig`;
      `TRANSCRIPT_DELAY_SECONDS` (1.5) is the mean of a uniform jitter between
      fetches. The old `ponytail:` note is gone with the problem it named.
- [x] **One rate-limit bucket per external service.** YouTube transcripts,
      yt-dlp, Anthropic extract and Anthropic classify each get their own
      limit: set the Anthropic client's `max_retries` explicitly and give each
      RQ queue its own worker concurrency, so a throttled classifier cannot
      stall extraction. **Done 2026-09-23:** the actual coupling was the
      classifier failing open on a 429, which billed every chunk to Sonnet. It
      now raises, and the classify job retries on its own queue (same schedule
      as extract); only the last attempt fails open. Per-queue concurrency
      already worked (`python -m pipeline.worker classify`), now documented.
      `max_retries` left at the SDK default of 2: RQ's retries sit on top.
      Transcripts already have their own delay (the IP-block item); yt-dlp
      is one listing per channel.
- [ ] **Incremental channel re-crawl, tiered.** Re-list a channel and stop at
      the first `platform_id` already in `content`; check recently active
      channels often ("warm") and dormant ones rarely ("cold"). Today ingest
      is manual and re-lists the whole back catalogue.
      **Parked 2026-09-23:** one channel, listed with `limit: 25`, costs about
      one request, and there is no scheduler for tiers to feed. Stopping at
      the first known id would also break "drop `limit` to backfill the whole
      channel". Revisit with several channels and a scheduled ingest.
- [ ] **`published_at` for survivors only.** Resolves the *Known defects*
      entry above: once videos are filtered at the video level, the per-video
      yt-dlp fetch is only paid for videos that will actually be extracted.
      **Parked 2026-09-23:** the video filter exists now, but nothing reads
      `published_at` (see the defect entry), so the fetch buys nothing yet.

---

## Ideas — routes: curated, customizable, testable (2026-09-23)

Researched 2026-09-23 against `api/read.py`, `api/queries.py`, migrations
013/014, F25 and `docs/10-decisions.md` § Routes. **Unvetted.** Why the route
feels clunky, from the code: `ROUTE_CANDIDATES_QUERY` takes the 20 *nearest*
candidates, `_mix_layers` alternates layers, and `_walking_order` puts them in
greedy nearest-neighbour order as an open path, drawn crow-flies. So the stops
are picked with no idea of the walk between them, the order can cross itself
and double back, it never returns to where you started, and the line goes
through buildings. In the literature this is an **Orienteering Problem** (OP):
pick a subset of stops and an order that together collect the most "prize"
within a length budget. Tourist apps build on it as the **Tourist Trip Design
Problem** (TTDP). Items that conflict with rules already written in F1/F25 are
flagged ⚠️ inline, not overridden.

#### Fix the walk we already have — do these first

- [x] **Order the stops exactly. Five stops is 120 orderings.** Done
      2026-09-23: `_walking_order` tries every ordering up to 8 stops
      (`tests/test_route_order.py`); greedy above that. Nearest-neighbour
      is the weakest tour heuristic there is. Trying every ordering of ≤5 stops
      (≤8 is 40,320) costs less than the SQL round trip. Past that, use
      Held–Karp DP, which is exact and practical up to ~15–20 points.
      2-opt/Or-opt only earn their place once n gets bigger than that.
      **First step:** replace `_walking_order`'s body with
      `min(itertools.permutations(...))` over path length from the anchor.
      [Held–Karp](https://en.wikipedia.org/wiki/Held%E2%80%93Karp_algorithm) ·
      [Johnson & McGeoch, TSP local search](https://www.cs.ubc.ca/~hutter/previous-earg/EmpAlgReadingGroup/TSP-JohMcg97.pdf)
- [x] **Choose stops for the walk, not for being nearby.** Done 2026-09-23:
      `_choose_stops` is cheapest insertion plus 50 seeded drop-and-reinsert
      rounds, ~2 ms on 20 candidates. It replaces `_mix_layers`; each layer is
      guaranteed min(available, size // 2) stops. Prizes are still uniform, so
      it only minimises metres (`tests/test_route_order.py`). Today a stop 300 m
      *behind* you beats a tight cluster 500 m ahead. Choosing and ordering are
      one problem. The practical, well-proven heuristic is **ILS**: insert the
      stop with the best prize per metre until the budget is full, then shake
      (remove a few, re-insert). GRASP-PR, ALNS and EA4OP are for hundreds to
      thousands of nodes; this is ≤20 candidates per request.
      **First step:** greedy ratio insertion plus ~50 ILS iterations in pure
      Python, seeded from `(device, route_date)` so it's reproducible. No new
      dependency.
      **Upgrade:** OR-Tools routing with `AddDisjunction(node, prize)` per stop
      (prize-collecting out of the box), once time windows or several routes a
      day arrive.
      [Gunawan, Lau & Vansteenwegen 2016 survey](https://www.sciencedirect.com/science/article/abs/pii/S037722171630296X) ·
      [Vansteenwegen et al. 2009, ILS for TOPTW](https://www.sciencedirect.com/science/article/abs/pii/S030505480900080X) ·
      [Gavalas et al. 2014, TTDP survey](https://link.springer.com/article/10.1007/s10732-014-9242-5) ·
      [Santini 2019, ALNS](https://santini.in/files/papers/santini-2019.pdf) ·
      [Kobeaga et al. 2018, EA4OP](https://www.sciencedirect.com/science/article/abs/pii/S0305054817302241) ·
      [OR-Tools penalties](https://developers.google.com/optimization/routing/penalties)
- [x] **Budget in metres of walk, not a search radius.** Done 2026-09-23:
      `ROUTE_BUDGET_METERS` (4000) against crow-flies × `ROUTE_CIRCUITY` 1.3.
      `_choose_stops` takes as many stops as fit, then the shortest walk. The
      budget beats the layer mix. Server knob only; the length chip is below.
      **Superseded 2026-09-23:** the budget is the plan page's slider, sent per
      request; `ROUTE_BUDGET_METERS` is gone.
      `radius_meters` limits
      *where candidates come from*, not *how long the walk is*: a 4 km radius
      can produce an 11 km route. Keep the radius as a prefilter and add
      `budget_meters` as the real constraint. Crow-flies underestimates walking;
      measured urban circuity is ~1.2–1.3.
      **First step:** check the budget against `haversine × 1.3`. ⚠️ F25 rules
      out showing minutes until street routing backs them; this keeps to that.
      [Boeing 2019, circuity of walk vs drive networks](https://arxiv.org/pdf/1708.00836)
- [x] **Loop or one-way, as one flag.** Done 2026-09-23: `ROUTE_LOOP`, on by
      default. The leg home counts in choosing, ordering and the budget, and
      `meta.loop` tells the app. The app keeps the day's first position next
      to its cached route and draws the line back to it; the server still
      stores none. The e2e walk now covers all five stops of the loop.
      A loop is the same OP with start = end,
      and it's the default in tools people already use for walks (Komoot round
      trips; GraphHopper's `algorithm=round_trip` takes a target distance and a
      seed). For a daily walk from wherever you are, a loop is likely the right
      default: it accounts for the walk home.
      **First step:** count the last leg back to the anchor in the objective,
      and draw it.
      [Komoot round trips](https://support.komoot.com/hc/en-us/articles/360024590552-Planning-round-trips) ·
      [GraphHopper round_trip](https://github.com/graphhopper/graphhopper/blob/master/docs/web/api-doc.md)

#### Walking distances instead of crow-flies

- [x] **Street distances: a circuity factor now, a routing sidecar later.**
      Done 2026-09-23: OSRM `foot` (`api/streets.py`, `osrm/build.sh`, the
      `routing` compose profile). One `/table` feeds choosing and ordering.
      Stop-to-stop shapes go on `daily_routes.legs`, never the legs touching
      the start. Crow-flies × 1.3 when `ROUTING_URL` is unset or down. No
      `(place_id, place_id)` cache yet: a local `/table` is milliseconds.
      Railway still has no sidecar; that waits on `DEPLOY` (~1.6 GB RAM to
      build, and the graph ships as files). Lightest option first:
      (a) **pgRouting** inside the PostGIS we already run, via
      `pgr_dijkstraCostMatrix`. No new service, but the import is slow.
      (b) **OSRM** `foot` profile: a `/table` matrix in milliseconds, one
      container per region extract.
      (c) **Valhalla** `pedestrian`: a `sources_to_targets` matrix, tunable
      walking speed, and route shapes for the polyline.
      (d) Hosted APIs such as Mapbox Matrix or Google `computeRouteMatrix`,
      which charge per call.
      **Upgrade:** Valhalla or OSRM in `docker-compose.yml`, NYC extract only.
      Cache matrix cells on `(place_id, place_id)`; places don't move, so it
      never goes stale. Store the `/route` geometry on the `daily_routes` row,
      so `RouteLine` follows the streets.
      [OSRM](https://en.wikipedia.org/wiki/Open_Source_Routing_Machine) ·
      [Valhalla matrix](https://valhalla.github.io/valhalla/api/matrix/) ·
      [pgRouting workshop](https://workshop.pgrouting.org/dev/en/index.html) ·
      [Mapbox Matrix](https://docs.mapbox.com/api/navigation/matrix/) ·
      [Google Route Matrix](https://developers.google.com/maps/documentation/routes/compute_route_matrix)

#### What a stop is worth

- [x] **Give stops a prize; make layer mix a diversity term.** Done
      2026-09-23: prize = 1 + `contrast_score`, insertion by prize per metre,
      walks ranked by count, layer quota, prize, then metres. A shake round
      no longer re-inserts what it dropped. MMR skipped: the layer quota is
      the diversity term, and every `contrast_score` is still NULL. Every candidate
      is worth the same today, so an OP would just minimise distance. Prize
      from signals that already exist: `contrast_score`, heart counts,
      `extraction_confidence`. Replace `_mix_layers`' strict alternation with
      **MMR**: λ·prize − (1−λ)·max similarity (same layer, tag overlap) to the
      stops already picked. That keeps diversity without coming up short when
      one layer runs dry. Scenicness (Quercia's "shortest path to happiness")
      needs street-level data we don't have yet, so it's parked.
      **First step:** prize = `1 + contrast_score`, MMR with λ≈0.7 inside the
      insertion step.
      [Carbonell & Goldstein 1998, MMR](https://www.semanticscholar.org/paper/The-Use-of-MMR-and-Diversity-Based-Reranking-in-and-Carbonell-Goldstein/fb27d922754a8bfb8dee582f0231f55174fd50e3) ·
      [Quercia et al. 2014](https://arxiv.org/abs/1407.1031)

#### Predefined routes

- [ ] **`routes` + `route_stops` for authored walks.** A join table earns its
      place here, where migration 013 rightly refused one for five ints: an
      authored route is long-lived, reordered, shared and edited.
      `routes(id, title, theme_tag, author_user_id, source
      'editorial'|'generated', status 'draft'|'published', is_loop,
      budget_meters, geometry)` and `route_stops(route_id, position,
      memory_id)`. `daily_routes` gets an optional `route_id` for "today I'm
      walking *this* one".
      Prior art: VoiceMap authors a fixed ordered path with a trigger radius
      per stop and matches talk time to walk time. Detour chained ~50 GPS pins
      into one narrated walk. Google Maps Lists are unordered, but shareable,
      collaborative and followable.
      **First step:** the migration, plus `GET /v1/routes/{id}` through
      `row_to_memory`, so stops stay gated.
      [VoiceMap publisher docs](https://docs.voicemap.me/tour-publishers/choosing-locations/) ·
      [Detour](https://www.technologyreview.com/2015/03/06/168961/first-groupon-founder-now-tour-guide/) ·
      [Google Maps lists](https://support.google.com/maps/answer/7280933)
- [ ] **Generated themed routes, reviewed by a person before publishing.** An
      offline job: for each hotspot cluster (`HOTSPOTS_QUERY`) × each tag,
      solve the same OP from the centroid, write `source='generated',
      status='draft'`, then accept or reject in the style of
      `pipeline/review.py`. This is how City Trip Planner and Strava's
      generated routes work: the algorithm proposes, and curation or
      popularity filters.
      **First step:** none until one area has ≥3 tags with ≥5 walkable stops
      each. Write that check as a query first.
      [City Trip Planner, Vansteenwegen et al. 2011](https://www.sciencedirect.com/science/article/abs/pii/S0957417410013230) ·
      [Strava generated routes](https://support.strava.com/en-us/articles/15401756-generated-community-routes) ·
      [Lim et al. 2019, tour recommendation survey](https://link.springer.com/article/10.1007/s10115-018-1297-4)

#### Letting people change the route

- [ ] **Customise by constraints and one swap, not a route editor.** People
      keep using an imperfect algorithm when they can modify its output even
      slightly (Dietvorst et al. 2018). Research planners (City Trip Planner,
      LAPPI) and Komoot/Strava take a few constraints and let the solver do
      the rest. In order:
      (1) **"Swap this stop"**: remove it and re-insert the next-best
      candidate, reusing the insertion step.
      (2) ~~A length chip (short/medium/long → `budget_meters`)~~ **Done
      2026-09-23** as the plan page's slider, 1–10 km (F1). Still open: one
      theme tag and a loop toggle.
      (3) Drag-to-reorder last. Stops already unlock in any order, so it
      mostly changes the line.
      **Decided 2026-09-23:** no regenerating. One accepted walk per device
      per day, locked until tomorrow; a swap would need that reopened first.
      [Dietvorst, Simmons & Massey 2018](https://pubsonline.informs.org/doi/10.1287/mnsc.2016.2643) ·
      [LAPPI](https://arxiv.org/pdf/2512.14138) ·
      [Komoot planner](https://support.komoot.com/hc/en-us/articles/10206792140826-Plan-routes-in-the-app)
- [ ] **An end point per request, never stored.** "End at the subway" is a
      one-way OP; `end_lat/end_lng` is used only on the day's first call.
      ⚠️ Storing it would bring back the stored home location that
      `docs/10-decisions.md` § Routes decided against.
      **First step:** skip it until loop vs one-way ships and someone asks.

#### Mock data and measuring

- [x] **A dense, randomised map, so the route is tested and not staged.**
      Done 2026-09-24: `seed_dev --dense N --seed S` samples
      `pipeline/midtown_ways.json` (3,319 points OSRM-snapped once by
      `--snap-pool`, one per grid cell); `pipeline/route_bench.py` measures.
      Look-around still previews the hand-placed seed: every e2e flow shares
      one database, so the dense map needs its own area or DB first.
      **Measured** (300 memories, seed 1, 150 runs): every walk found 5 stops,
      but **76% have a spur** (retraced p50 32 m, p95 129 m), the walk uses a
      median **28% of the budget** (15% at 6 km: the ranking prefers the
      shortest walk once 5 stops fit, so a long slider still gets a tiny
      loop), and a plan takes **~1 s** p50 (7 `/route` calls per cleanup
      round). So `ROUTE_CLEANUPS` does not reach the bar, and the next step
      is the choice itself: prefer loops (penalise retraced street in the
      score) and aim the walk at the budget, not under it.
      **Done 2026-09-24** (docs/10-decisions.md, "The walk the slider asked
      for"). Same 150 runs, with `retraced_meters` no longer counting the
      stub inside a stop's 20 m gate (93% of what it called a spur):
      walk/budget median **0.28 → 0.84**; spur over 50 m **~10% → 9%**;
      retraced p50/p95 **22/90 → 7/59 m**; latency unchanged, ~1.1 s,
      nearly all of it the MLD `/table` at ~19 ms a point.
      Still open: 6 km fills only 0.63 because the dense seed covers
      ~1.5 km², which is the fixture's edge rather than the solver's. And
      a CH build of the sidecar (`osrm-contract`) would likely take the
      table from ~800 ms to tens.
      Raised 2026-09-24. The dev seed is five stops placed by hand as one clean
      loop (`pipeline/seed_dev.py`), which proves the flow and the street
      walking but games the algorithm: with five candidates there is nothing
      to choose. In the street the map will be full, and the whole job is
      picking which five make a clean loop. So:
      (1) `seed_dev --dense N --seed S`: N memories (hundreds) at random over
      Midtown from a seeded `random.Random`, every one snapped to within the
      20m gate of a walkable way (OSRM `nearest`, then committed as a JSON
      fixture so the gate stays offline), random layers, tags and
      `contrast_score`, all marked `dev-seed:` for `--clear`.
      (2) Measure the solver over it from many random starts and lengths:
      retraced metres (`api/streets.py`, `retraced_meters`), stops found,
      walk vs budget, ms. The bar is "no spur" on a full map, and
      `ROUTE_CLEANUPS` (drop one stop, re-pick) may well not reach it - then
      the choice itself has to prefer loops, not only the cleanup.
      (3) Keep the hand-placed loop for `.maestro/walk-and-unlock.yml`, which
      needs one known walk to name its stops; point look-around's preview at
      the dense map instead.

- [ ] **`seed_dev --routes`: scenarios, not a cluster.** Today's seed puts 7
      points within ~400 m. That's enough to render a route (and
      `.maestro/walk-and-unlock.yml` now walks stops 1→2→3 of it), but it
      can't tell one algorithm from another. Add named scenarios, each marked
      `dev-seed:` and removed by `--clear`:
      - *sparse*: 2 stops.
      - *dense*: 40 stops in 1 km².
      - *bimodal*: two clusters either side of Central Park, where crow-flies
        lies the most.
      - *linear*: along Broadway.
      - *one-layer*.
      - *stack-heavy*.
      Put the points on real sidewalks by sampling an OSMnx `walk` graph of
      Midtown once, and commit the coordinates as a JSON fixture, not OSMnx as
      a dependency.
      [OSMnx, Boeing 2017](https://geoffboeing.com/2016/11/osmnx-python-street-networks/)
- [ ] **`pipeline/route_bench.py`: score and time every solver on the same
      instances.** Shaped like `perf.py` and `quality.py`: run by hand and
      read, not part of the gate. Inputs: the classic OP benchmarks
      (Tsiligirides sets 1–3, Chao 64/66, best-known scores from KU Leuven)
      plus the Manhattan fixtures above. Output per solver (current NN, exact
      order, ILS): prize, % gap to best known, metres, crossings/backtracks,
      and p50/p95 ms. Separately, add `ROUTE_CANDIDATES_QUERY` to `perf.py`,
      which doesn't time it today.
      [KU Leuven OP instances](https://www.mech.kuleuven.be/en/mim/op) ·
      [Tsiligirides 1984](https://www.researchgate.net/publication/230856233_Heuristic_Methods_Applied_to_Orienteering) ·
      [OPLib / op-solver](https://github.com/gkobeaga/op-solver)
- [ ] **Property tests for the solver, next to `tests/test_api_routes.py`.**
      The endpoint tests already cover exclusions. The solver needs
      invariants over random instances:
      - never over budget;
      - no place twice;
      - the same seed gives the same route;
      - prize ≥ the NN baseline;
      - equals brute force when n ≤ 7;
      - a loop starts and ends at the anchor.
      **First step:** a seeded `random.Random(i)` loop over 200 instances in
      one pytest. **Upgrade:** Hypothesis, if a failing case ever needs
      shrinking.
      [Hypothesis](https://hypothesis.readthedocs.io/)

## Walk and Explore (2026-09-24)

Two modes, two tabs, one map. **Walk** is today's route and the only place
anything unlocks; **Explore** is every nearby memory, clustered, never
unlockable. Decided with the founder 2026-09-24:

- Two tabs sharing the one mounted MapView (UI.md rule 9), each with its own
  camera and pins. Not a toggle on the map, not two MapViews.
- "Near me" goes. The slot survives only as "Turn on location" when there is no
  position, because without one no stop can ever open.
- Ungated memories (shared city-centroid coordinates) read normally in Explore,
  as the API already serves them. "Not unlockable" means nothing is *earned*
  there, not that open memories are hidden.

The browse map existed until `c3d5d9c` (2026-09-23) deleted it with
`useNearby.ts`, `region.ts`'s viewport maths, `ReachBanner`, `Elsewhere` and
the hotspots card. `cluster.ts` survived. Recover from `c3d5d9c^` before
rewriting anything.

In build order:

- [x] **Remove "Near me".** The locate button in `mobile/App.tsx` renders only
      while `!position`, as "Turn on location" (keep the `blocked` →
      `Linking.openSettings()` branch). `goToMyLocation` stays - launch, plan
      and + Add still need a fix and the watcher. Recentring moves to the route
      pill: a tap fits you *and* the next stop. `.maestro/walk-and-unlock.yml`
      waits on `visible: "Near me"` as its "has a fix" signal; switch it to the
      pill. Docs: UI.md's screen tree and `locate` shadow row, docs/08 F25
      steps 2-3 and the "Turn on location" lines in F7 and F9.
      **Done 2026-09-24:** the button exists only while `!position`; the pill
      takes its slot and fits you and the next stop.
- [x] **Tabs: Walk · Explore · Memories · You.** `mobile/src/TabBar.tsx`
      (`Tab` gains `'explore'`, `'map'` becomes Walk). The bar shows from
      launch, which reverses "the tabs arrive with the walk" (App.tsx, docs/08
      F25 step 2). Launch lands on Walk: the plan page if nothing is accepted
      today, the walk if it is. A tab switch swaps pins and restores that tab's
      own saved region.
      **Done 2026-09-24:** `selectTab` keeps a region per map tab; Explore is
      the bare map until the next item gives it pins.
- [x] **Explore: every nearby memory, clustered, locked.** Restore the
      viewport fetch and its debounce from `c3d5d9c^` (`useNearby`, the radius
      maths in `region.ts` and its tests) and un-retire UI.md rules 3 and 4.
      Group with `cluster.ts`. `reachOf` never answers `unlockable` here, so no
      pin lights; the sheet opens locked, without `UnlockButton`. First entry
      centres on the person, after that wherever they left it.
      **Done 2026-09-24:** `useNearby` fetches from the camera's region; the
      sheet takes no `onUnlock` there and says memories open on a walk.
- [ ] **Unlocking is Walk-only as a client rule.** `POST
      /v1/memories/{id}/unlock` does not know about modes and should not. Say
      so in docs/10 next to "The position is self-reported", so nobody
      "fixes" it server-side.
- [ ] **The seams - decide each while building:**
      - A route stop seen in Explore: plain pin; its sheet says "Stop N on
        today's walk" with a button that switches to Walk and flies there.
        (Recommended. The client still never names a stop to the server.)
      - Leaving mid-preview and coming back resumes it - the state is in App.
      - + Add in Walk only, or both? Filing is not unlocking. **Open.**
      - Geofence notifications keep tracking the route only. Unchanged; write
        it down.
      - `EXPO_PUBLIC_DEV_OPEN_MEMORY` searches `groups`, so it has to pick a
        tab.
- [ ] **Flows and tests.** New docs/08 flow F29 (Explore) and F25 amended. A
      Maestro journey: pan, clusters, a pin that stays locked while you stand
      on it, the jump to Walk. The same journey headless in
      `tests/test_flows.py`.

---

## Decided — do not revisit

Copied so they survive context resets.

**Non-goals — do not build:**
- ~~Consumer subscription (converts at 1–3% on social apps)~~ **Reopened
  2026-09-22:** now a second monetization track, later and secondary to B2B —
  see "Ideas — founder brainstorm" above and "Monetization context" below.
- Ad product (needs millions of DAU)
- Multi-city launch
- Personal video archives as a source (GPS is already in EXIF, and people film
  the thing rather than narrating what happened there)
- Unmarked sponsored placement
- Generic Wikipedia-grade facts as primary content
- **A search UI.** Asked and answered 2026-09-22: the only way a user should
  unlock a memory is by walking there. `/v1/memories/search` stays as a typed,
  tested endpoint with no client — see the *Known defects* entry above for why
  building a search screen on it would surface the corpus's worst rows.

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

**Monetization context** (not a build target): near-term revenue comes from the
historical layer — embeddable maps and delivered corpora for tourism boards,
audio-guide companies, city archives. **Reopened 2026-09-22:** a consumer
subscription is now a legitimate second track, once there's a userbase — it
does not replace or delay the B2B plan, which stays what Phase 2 builds toward.
The social layer earns nothing on its own for years, if ever, independent of
whether it later carries a subscription. Local business seeded memories are a
later option and must be clearly marked.

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
