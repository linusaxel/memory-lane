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

- [ ] **Layers** — no `layer` column, no concept. Everything is one
      undifferentiated feed, which the brief forbids.
- [ ] **Contrast scoring** — every query orders by `distance ASC`. There is no
      score, and no source of "what is at this place now" to compute one from.
- [ ] **Non-video ingestion** — `ingest_content()` warns and skips any
      `platform != "youtube"`. Archives, newspapers and setlists have no path in.
- [ ] **When it happened** — `memories` stores `timestamp_start`, a position in
      a video. A 1978 gig has nowhere to record 1978.
- [ ] **Attribution per memory** — only a join to `content`. The legal posture
      needs per-memory credit and a deep link that survives on a shared card.
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

### Known defects, unowned

- [ ] **Semantic place duplicates.** The unique index catches exact repeats, but
      near-matches still land as two pins. Live right now: *Gotham Comedy Club
      New York City* (6 memories) and *Gotham Comedy Club Chelsea New York City*
      (1 memory) are one venue on two pins. This blocks both contrast scoring
      and map clustering — it is a Phase 1 item, not a cleanup nicety.
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
- [ ] **`published_at` is always NULL** — yt-dlp flat extraction returns no
      timestamp for this channel. Nothing serves it, so it blocks nothing.

---

## Design questions — cross-cutting, sequencing NOT ratified

**Provenance:** seeded 2026-09-20 by the cleanup session, which proposed running
this *before* Phase 1 as a "Phase 0". The findings below are real and stay. The
reordering does not stand on an agent's say-so — the brief reserves build-order
changes for the user, and Phase 1 remains the approved next phase. Raised in
Open questions; until it is answered, treat these as cross-cutting items to
resolve *during* Phase 1, not a gate in front of it.

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
- [ ] **D.4 Design the empty state, and make it distinguishable from failure.**
      Confirmed live: `fetchNearby` accepts an `AbortSignal`, `App.tsx` never
      passes one, so an unreachable API hangs instead of rejecting and the
      banner shows "0 memories here" with a spinner indefinitely. The error path
      that exists never fires. The realistic Copenhagen case before the
      historical corpus lands is zero memories nearby — and right now that looks
      identical to the app being broken.
- [ ] **0.5 Write F3 properly** once the historical source is chosen (W4-00).
      F3 is the product; it should not be specified by whatever the ingestion
      happens to produce.

---

## Phase 1 — Historical layer, one neighborhood

Copenhagen. Non-video ingestion, contrast scoring, proximity query, card design.
The goal is a map that is never empty in one neighborhood, ranked so the top
card is the one worth screenshotting.

- [ ] **1.1 Schema, additive.** Reuse the existing four tables; no new entity
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
      - Verify: schema applies clean to an empty DB *and* migrates the live one
        without changing `SELECT count(*) FROM memories` (currently 224).
- [ ] **1.2 Semantic place dedup.** Normalise `place_query` (casefold, strip
      venue-type stopwords) and collapse places whose coordinates fall within
      their combined `precision_meters`. Ground truth to fix: the two *Gotham
      Comedy Club* rows must become one. Follow the pattern
      `001_places_unique.sql` already established: merge coordinates onto the
      keeper first, repoint `memories.place_id`, then delete orphans guarded by
      `NOT EXISTS` — `memories.place_id` is `ON DELETE CASCADE` and an unguarded
      delete eats memory rows. No embeddings until this measurably falls short.
- [ ] **1.3 Source-agnostic ingestion.** A second entry point beside
      `ingest_content()` taking already-fetched records
      `{text, source_url, attribution, happened_at, address?}`, writing `content`
      with `source_type != 'video'` and bypassing `transcripts` entirely.
      Reuses `save_memories()` unchanged. **The concrete source adapter is not
      chosen yet** — see Open questions. Ship the path plus one hand-loaded
      Copenhagen fixture so 1.4–1.8 are unblocked.
- [ ] **1.4 A second extraction prompt, for archival text.** The existing
      `SYSTEM_PROMPT` is tuned for personal anecdote ("WHO / WHAT HAPPENED /
      THE VIBE") and is wrong for third-party material. The historical prompt
      must emit `happened_at`, and must reject static description ("this
      building was constructed in 1902") and Wikipedia-grade fact as hard as the
      current one rejects hypotheticals. Same JSON contract, same tag vocabulary.
- [ ] **1.5 Contrast scoring.** Scored once at extraction and stored, never
      recomputed — extraction is a one-time cost per place, amortized across
      everyone who stands there. The extractor emits `then` (what stood there)
      and a 0–1 `contrast_score` with a one-line `contrast_note`. Present-day
      place identity comes from OSM/Overpass (free, no key) as an enrichment
      pass; if that proves noisy, the score stays LLM-only and we say so here.
      A jazz club that is now a bank lobby must outrank a cathedral's founding.
- [ ] **1.6 Query.** `/v1/memories/nearby` gains a `layer` filter and orders by
      `contrast_score DESC, distance ASC` within the radius. Fix `meta.total` to
      respect active filters while in there.
- [ ] **1.7 Card.** `GET /v1/memories/{id}/card`, server-rendered. One template,
      three consumers: the app sheet, the Phase 2 widget, and any pasted link.
      Place name and attribution always visible, legible at thumbnail size,
      correct in light and dark. Attribution cannot be stripped by a client.
- [ ] **1.8 Tests.** A behavioural `/v1/memories/nearby` test covering radius,
      layer filter and contrast order — `test_api_sql.py` only proves the SQL
      parses.

**Phase 1 is done when** standing anywhere in the chosen Copenhagen
neighborhood returns at least one historical card, the top card is the highest-
contrast one rather than the nearest, and the card is worth screenshotting.

---

## Phase 2 — Embeddable map widget

First revenue surface. Same corpus, different rendering. Tourism boards,
audio-guide companies, city archives.

- [ ] **2.1** One `<script>` snippet + an `/embed` route. MapLibre over free
      tiles; no Google Maps key on the web side.
- [ ] **2.2** Reads the same `/v1/memories/nearby` and renders the Phase 1 card.
      If the widget needs a different shape, change the card, not the data.
- [ ] **2.3** Per-customer `CORS_ORIGINS` and a per-embed key. This is the first
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

- **Should the design questions run before Phase 1?** The cleanup session
  proposed it as a "Phase 0" and makes a fair case: three backends behind an
  undesigned surface gets you three backends and no product. But the brief
  reserves build-order changes, so this is the user's call, not an agent's.
  Unanswered, Phase 1 proceeds and the design items ride alongside it.
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
