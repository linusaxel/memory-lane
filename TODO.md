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

### Data sources

Researched by the founder 2026-09-26; every "verified" below is theirs, from
live requests. Order is priority.

**This week**

- [ ] **Email it@historiskatlas.dk for API access.** (checked 2026-09-26) An
      open-data association of 220+ archives, museums and libraries, seeking
      partners. Say the use and the attribution. Needed because the per-story
      licence ("Geo" in their API) is not on the public pages. Until then the
      sitemap source has title and intro only (`contents` and `tag_geos` null).
      Also a partial competitor: judge their neighbourhood-level content
      before building on it.
- [ ] **Email kbhbilleder@kff.kk.dk.** (checked 2026-09-26) 41,779 historical
      photos, maps and drawings (Copenhagen Museum + City Archives), ~5,000
      out of copyright and commercially usable, many already geotagged by
      users. Bot-protected (HTTP 202, 0 bytes): ask, never scrape. The
      platform is open source with a public APACS API:
      github.com/CopenhagenCityArchives.

**Next**

- [ ] **Kraks Vejviser and older address directories.** (checked 2026-09-26)
      Pre-1900 editions at kb.dk carry a public domain mark (commercial use
      with credit); Copenhagen Libraries host digitised volumes at
      bibliotek.kk.dk/din/bag-om-kobenhavn/kraks-vejviser. OCR'd scans, real
      extraction work. "What stood here" for nearly every address: the
      connective tissue between the interesting cards.

**Blocked or deprioritised**

- [ ] **arkiv.dk.** (checked 2026-09-26) 550+ archives, no public API.
      Institutional conversation only; plan no sprint around it.
- [ ] **setlist.fm: do not scrape.** (checked 2026-09-26) The API is free for
      non-commercial use only; commercial means asking Live Nation /
      Ticketmaster, its owner. 20–30 items a request makes a city backfill
      heavily paginated. Revisit only once a commercial licence clears.

**Validate before building more**

- [ ] **Three streets, counted by hand.** (checked 2026-09-26) In the launch
      neighbourhood, count the *interesting* cards each source yields per
      street, not the records: would this make someone stop walking? The
      prediction to test: newspapers and the sabotage set win, directories are
      filler.

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

## Map first

Decided 2026-09-26 (the founder's ramble): after sign-in the app opens on a
map of what is locked around you, and a walk is how you open any of it. Each
step ships and stands on its own; in order. M1, M2 and M4 shipped 2026-09-26
(F29, docs/10 *A map of what is locked*); M5 and M6 (Walk here plans a walk
through that pin) and M9 (End walk, F34) shipped the same day, then M8 (the route-blue
"On a walk · 2 of 5" bar, F25); M7 went with the day lock (docs/10
*A walk can be ended*).

- [ ] **M3 A direction arrow on the user dot.** (checked 2026-09-26:
      react-native-maps 1.29.8 has no heading or tracking-mode prop, so no code
      can ask for it.) Look on a real phone whether MapKit's own dot draws the
      heading beam with `showsUserLocation` (`mobile/App.tsx`); the simulator
      has no compass. Only if not: `Location.watchHeadingAsync` and a custom
      marker. Needs somebody with a device. The same device can check F28
      with the phone locked and the app killed (`notify-nearby.yml` covers
      only the background).
- [ ] **Authored walks: the rest of `routes` + `route_stops`.** (checked
      2026-09-24) Migration 023 and `GET /v1/routes/{id}` exist, published
      only, kept to `title, status, is_loop`. No author, theme, source, budget
      or geometry until something writes a route (the generated job below, or
      an editor). `daily_routes.route_id` waits for the app to walk one.
- [ ] **Generated themed routes, reviewed before publishing.** (checked
      2026-09-26) An offline job: for each hotspot cluster × each tag, solve
      the same OP from the centroid, write `status='draft'`, then accept or
      reject in the style of `pipeline/review.py`. **Waits on** one area with
      ≥3 tags of ≥5 walkable stops: `python -m pipeline.themed_routes` says
      which. None yet outside the dev seed; New York and West Hollywood have
      two each. The job grows in that file.
- [ ] **One accent, not teal and blue.** (checked 2026-09-26) The founder:
      "Plan a walk" is black, teal works with neither buttons nor the route
      line, and a walk's stops need done, here, next and later told apart.
      Proposed in docs/09 § 7: `ember` red replaces `brand` and `route`,
      `faded` means behind you, `seal` stays "open it now", blue is left to
      the map and the user dot. Waits on the founder's yes and a look on a
      real map; then `theme.ts`, `MemoryMarker.tsx` (needs each stop's opened
      state), `RouteLine` split walked/ahead, `styles.locate`, and UI.md.

---

## Paid map unlock

Decided 2026-09-26 (the founder): a walk is free and opens its stops;
opening a pin from the map with no walk, or a second walk the same day, needs
a subscription. Server side shipped 2026-09-26 (docs/10 *A subscription opens
the map*): the `subscriptions` table, the unlock's `SUBSCRIBED_QUERY` and the
one-free-walk-a-day refusal. Nothing writes `subscriptions` yet, so everybody
is free. What is left is blocked on `EAS_BUILD` and `STORE_ACCOUNT`.

- [ ] **S3 Purchases verified server-side, never a client flag.** (checked
      2026-09-26) A client-side entitlement is a client-side gate. Pick one:
      RevenueCat (one SDK and one webhook for both stores, free under $2.5k
      a month of revenue) or the App Store Server API plus the Play Developer
      API direct (free for ever, twice the code). Either way a webhook writes
      `subscriptions` (widen it to what the store sends), authenticated by a
      shared secret; renewals, refunds and expiry come through it.
      `accounts.absorb` must carry a row to the account it merges into. New knobs go in `pipeline/config.py` and
      docs/01. Tests use a fake, never the store.
- [ ] **S4 The paywall in the app.** (checked 2026-09-26) `subscribed` on
      `GET /v1/me`, then: on a pin's peek, standing in range with no walk
      through it, **Open** for a subscriber; otherwise a sheet that sells it,
      with Walk here as the free way if today's walk is not spent. The same
      sheet replaces "You've had today's walk. Another tomorrow." on the
      `walked_today` 403. Needs Restore purchases, the price and period, and
      terms and privacy links, or App Review rejects it. The purchase SDK
      needs a dev build; Expo Go cannot buy anything. UI.md for the sheet.
- [ ] **S5 A way past the paywall for e2e.** (checked 2026-09-26) The same
      shape as the gate's dev knob (docs/10, the e2e entry): a dev-only
      entitlement a release build cannot take. Then an e2e flow for each:
      paywall shown, subscriber opens off-walk.
- [ ] **S6 The products in the stores.** (checked 2026-09-26) One
      auto-renewing subscription in App Store Connect and Play, a price, a
      sandbox tester, and the subscription disclosed in both listings. Waits
      on `STORE_ACCOUNT`.

---

## Copenhagen journeys

- [ ] **A long walk still falls short where the map runs out.** (checked
      2026-09-26) About a stop a km (docs/10) took 10 km from 0.33 to 0.56 of
      the slider on the dense seed, but the lakes top out at 7.4 km for any
      stop count: shortest legs cross the bridges. The preview now says "The
      longest from here." under ROUTE_FILL. Left: legs routed longer than the
      shortest path (round the shore), if an honest short walk isn't enough.
      Also: 10 km plans are p95 1.5 s (2.1 s before `score` was cached by
      stop set). 9 solves in 10 are the spur cleanup re-solving once per
      stop, so the next cut changes answers: measure it with `route_bench`.
      Tried 2026-09-26 (dense seed, 200 runs, seed 1; before → after):
      trying only the stops at either end of a retracing leg took p95 from
      1131 to 722 ms (10 km: 1829 → 1116) but spurs >50 m from 12% to 16%
      (8 km 19 → 30%). Trying those first and the rest only if none helps
      kept spurs near (14%) but 10 km p95 stayed 1747. Both reverted: the
      speed is bought with spurs: a founder's call, not a cleanup.

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

- [ ] **`API_CREDITS`** (checked 2026-09-26) — the extraction path has never
      met the real API; every test uses `FakeAnthropic`. **There is no
      `--limit` flag**: `python -m pipeline.extract` bills every pending
      video. To spend cents: `python -m pipeline.enqueue --video <content_id>`,
      then `--status <id>`. What has never been sent is the structured-output
      schema (`MEMORY_SCHEMA`), so a rejection shows on the first chunk. Once
      funded: one video, `quality --compare` against the old prompt, the
      pending episodes, `review`, then `classifier_audit`. The 22 clips
      extracted before the video filter probably duplicate their episodes'
      memories; look at them in `review` or `dedup`. Also unmeasured: the
      `address` and `country` prompt fields (the geocoder chain, docs/10
      *The LLM names the place; free geocoders place it*). Run
      `pipeline.quality` (video, and `--source-type newspaper`) before and
      after, and extract content 160 (Blaagaardsgade) to see a geocoded place.
      New extractions only; no backfill yet. KB papers: `pwa` sits near 50 on
      every 1856 page, so nothing is filtered on it; expect ad-page noise.
      Waiting too: 340 Historisk Atlas sabotage stories, all inside the
      Copenhagen box, ingested 2026-09-26 (dev DB). Each is a title and one
      line, so enqueue one first and judge whether that is a card at all.
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

- **Which historical source first?** (checked 2026-09-26) Narrowed by
  Phase 1 § *Data sources*: KB Labs newspapers and the Historisk Atlas
  sabotage set lead, arkiv.dk has no API, setlist.fm is non-commercial only.
  The three-street count there decides it. Other founder candidates: x/Twitter,
  Reddit (both meter API access), free literature such as Project Gutenberg
  (no per-venue coordinates).
- **Reuse terms for arkiv.dk.** (checked 2026-09-26) Unknown. The legal
  posture assumes we may quote at all. Mediestream's are known now: KB Labs
  serves papers over 140 years old, free.
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
