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

- **The `api` container runs whatever image was last built.** (2026-09-26) It
  does not mount the source, so a plain `docker compose up -d` served 09-22 code
  that queried a dropped column; the app showed only "Can't reach Memory Lane
  right now." and a session went to debugging the app. Fix: bind-mount `./api`
  and `./pipeline` with `--reload` in `docker-compose.yml`, or `--build` in the
  Quick start.

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

- [ ] **DAWA resolves Danish places; the LLM only picks which place.**
      (checked 2026-09-26) `https://api.dataforsyningen.dk/adresser?q=<address>`:
      free, no key, WGS84, and it fuzzy-matches OCR'd spellings
      ("Blaagaardsgade" → "Blågårdsgade"). Replaces model-guessed coordinates
      (docs/10, *The coordinates are mostly guesses*) and their cost. Today the
      model's coordinates go straight into `places` (`pipeline/extract.py`,
      `geocode_status`).
- [ ] **Newspaper ingestion from KB Labs.** (checked 2026-09-26) `GET
      https://labs.statsbiblioteket.dk/labsapi/api/aviser/export/fields` with
      `query`, `fields` (link, recordID, timestamp, familyId, fulltext_org),
      `max`, `structure=header&structure=content`, `format=CSV`. Free, no key,
      returned real 1856 text. ⚠️ Only papers over 140 years old (~pre-1886),
      not negotiable without an institutional agreement. OCR is rough
      Fraktur: expect garbled place names, drop low confidence. Many hits are
      classified-ad pages, addresses with no event: filter articles from ads
      or accept the noise. Query by street name to keep extraction targeted.
- [ ] **Email it@historiskatlas.dk for API access.** (checked 2026-09-26) An
      open-data association of 220+ archives, museums and libraries, seeking
      partners. Say the use and the attribution. Needed because the per-story
      licence ("Geo" in their API) is not on the public pages.
- [ ] **Email kbhbilleder@kff.kk.dk.** (checked 2026-09-26) 41,779 historical
      photos, maps and drawings (Copenhagen Museum + City Archives), ~5,000
      out of copyright and commercially usable, many already geotagged by
      users. Bot-protected (HTTP 202, 0 bytes): ask, never scrape. The
      platform is open source with a public APACS API:
      github.com/CopenhagenCityArchives.

**Next**

- [ ] **Historisk Atlas via its sitemap.** (checked 2026-09-26)
      `https://historiskatlas.dk/sitemap.xml`, 11,740 stories; robots.txt has
      no Disallow and pages are server-rendered. Parse `window.passed.geo` →
      `{geoid, title, intro, latitude, longitude, ugc}`. URL-encode æøå or
      ~50% of fetches fail. `contents` and `tag_geos` are null: the licence
      needs the API (email above). **Start at geoid 19000–20000**, the WWII
      resistance sabotage set: exact dates and addresses ("Sabotage mod Islev
      Møbelfabrik, 03.05.1945"), the highest-contrast material in any source
      so far. ⚠️ Only ~8% of stories fall in Copenhagen (n=90, so ~900 total):
      the corpus leans Funen/Jutland. ⚠️ Also a partial competitor: judge
      their neighbourhood-level content before building on it.
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
step ships and stands on its own; in order.

- [ ] **M1 Supersede "no map of everything".** docs/10 § *Only today's walk
      unlocks* says a browsable corpus is a finishable one. Locked pins are
      not browsable, so the rule it protects survives: only today's walk
      unlocks. Mark the F29 line `Superseded`, restate it, fix docs/08 (F1,
      F29) and mobile/UI.md. Docs only, before any code.
- [ ] **M2 Open on the map.** After sign-in and the location primer (F8), the
      map with the user's dot and the locked pins within walking range
      (`/v1/memories/nearby`, already gated). "Plan a walk" on the map opens
      today's F1 page unchanged: the standard way in stays. An accepted walk
      today still opens on the walk (F25). e2e: every flow that starts on the
      plan page taps through the map first.
- [ ] **M3 A direction arrow on the user dot.** Check native first: MapKit's
      user dot may draw the heading cone on a real phone by itself
      (`showsUserLocation`, `mobile/App.tsx`); the simulator has no compass,
      so verify on a device. Only if not: `Location.watchHeadingAsync` and a
      custom marker.
- [ ] **M4 Tap a locked pin: the peek.** A sheet that says plainly the only
      way in is to walk there, with one button: "Walk here". The sneak peek is
      what the gate already lets out (place, tag, source, year, distance), and
      the summary as grey redacted bars sized to its length, drawn from a word
      count, never from the text. ⚠️ The summary never reaches the client
      locked, blurred or not: a CSS/blur peek is a leak. If the peek needs a
      new field, it goes through `api/gate.py`.
- [ ] **M5 "Walk here" plans a walk through that memory.** `GET
      /v1/routes/preview` and `POST /v1/routes/today` take an optional
      `include=<memory_id>`. The server checks it: gated-eligible, within
      `budget_meters / 2`, reachable within `UNLOCK_RADIUS_METERS` of a street.
      Then it seeds the solver with it as a forced stop. Accept still carries
      no stops beyond that one id, and the solver stays deterministic, so
      preview and accept still agree. Amend docs/10 § *Preview, then accept*
      ("the client never names a stop" becomes "names at most one, and the
      server vets it").
- [ ] **M6 The plan page, started from a pin.** Same slider, loop and theme
      chips, the chosen memory marked as a fixed stop on every preview; "Show
      me another" never drops it. The slider's floor rises to what reaches
      it: too far for the length reads "Too far for 2 km: at least 3 km",
      not F1's "No walk that long from here".
- [ ] **M7 A pin tapped after today's walk is accepted.** One walk a day
      stands, so "Walk here" cannot plan a second. Decide before building:
      the peek says "On tomorrow's walk" and the pin is remembered for
      tomorrow's plan, or the button is simply absent. Undecided.
- [ ] **M8 Say "you are on a walk".** (checked 2026-09-26: there is no walk
      mode today, only the app. Once accepted, the map is the walk until
      midnight, and the F25 pill "Today's route · 0 of 5" is the only hint.)
      With M2 the map has two states, so the walk needs to look like one: a
      persistent top bar "On today's walk · 2 of 5" in place of Journal/+ Add,
      route-blue, and the off-route pins hidden as F25 already does. One
      signal, not three. Update F25 and mobile/UI.md.
- [ ] **M9 Leave the walk at any time.** An "End walk" on that bar returns to
      the map of locked pins (M2). Decide before building: it *pauses* (today's
      `daily_routes` row stays, the bar on the map says "Resume walk", earned
      stops stay earned, and one walk a day stands) or it *abandons* (the row
      is deleted and a new plan is allowed, which reopens the day lock in
      docs/10 § *Preview, then accept*). Pause is the smaller change and keeps
      the decision; abandon needs a superseded entry. No confirm dialog for
      pause; one for abandon.

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

- [ ] **A long walk still falls short where the map runs out.** (checked
      2026-09-26) About a stop a km (docs/10) took 10 km from 0.33 to 0.56 of
      the slider on the dense seed, but the lakes top out at 7.4 km for any
      stop count: shortest legs cross the bridges. The preview now says "The
      longest from here." under ROUTE_FILL. Left: legs routed longer than the
      shortest path (round the shore), if an honest short walk isn't enough.
      Also: 10 km plans are p95 1.5 s (2.1 s before `score` was cached by
      stop set). 9 solves in 10 are the spur cleanup re-solving once per
      stop, so the next cut changes answers: measure it with `route_bench`.

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
