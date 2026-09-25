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
The rules for adding to it are in AGENTS.md, "Then log the friction". Newest first;
delete an entry when its fix lands.

- [ ] **A broad sweep of the whole test suite.** (checked 2026-09-24) Now
      75 s for 660 tests. 10 s of the old 85 s was eight `test_ingest.py`
      tests asking real YouTube about `@test`, because `fake_channel` missed
      `channel_metadata`; fixed, and `conftest._no_network` now fails any
      unmarked test that leaves localhost. What is left is per-test overhead
      (no single test dominates) and duplicate coverage.
- [ ] **One route change is a 4-minute bench to judge.** (checked 2026-09-24)
      `route_bench --scenario all --runs 40` is ~4 min, ~1 s a plan, nearly all
      OSRM `/table`. Six tweaks cost ~25 min of waiting, and 40 runs is noisy
      enough that the same code moved bimodal's spur rate 40% → 45%. A bench
      also holds a transaction, so a migration on the same DB waits behind it.
      **Fix:** cache `/table` per point set inside a bench run, and print a
      spread (or run two seeds) so a 5-point move reads as noise or not.

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
- [ ] **Rate limiting on the API.** (checked 2026-09-24) None exists;
      `CORS_ORIGINS` and `REPORT_THRESHOLD` are the only abuse controls. Waits
      on a public launch.

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

