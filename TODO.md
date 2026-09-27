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

- **A prompt's variance can't be measured without hand-deleting its cache.**
  2026-09-27: `extraction_chunks` is keyed on the exact request, so re-running
  a video on the same prompt returns the stored reply. Six runs of video 534 each
  needed a psql `DELETE` of its rows first. Fix: a `--runs N` on
  `pipeline.quality` that calls `extract_memories_from_chunk` unstored and
  prints each run's survivors.
- **`mobile/` has no formatter, so every edit is hand-indented.** 2026-09-27:
  wrapping the sheet's credit strip in a row meant re-indenting fifteen JSX lines
  by hand, and the same session left a stray `</Pressable>` that only the
  typecheck caught. Fix: pin Prettier as a devDependency with a config matching
  today's style (2 spaces, single quotes, trailing commas), add `prettier --check`
  to `loop/verify.sh`, and do one reformat commit listed in `.git-blame-ignore-revs`.
  Then drop the "never run `npx prettier`" rule in AGENTS.md.

- **The e2e flows assert on whole sentences of copy.** 2026-09-27: a copy pass
  had to hand-edit seven `.maestro/*.yml` files and regex-escape every changed
  sentence, and a missed one fails a 10-minute run. Fix: give the gate notes and
  card titles a `testID` and assert on that, keeping prose matches for labels only.

---

## Known defects

- [ ] **Most places are still the model's guess.** (checked 2026-09-27)
      10 of 26 venue places are `llm`, and re-geocoding all 10 today finds
      none: the names aren't on the map as said. "Nørrebro Bridge" is
      Dronning Louises Bro, "Barbershop on Vognmagergade" is a description,
      Maskot and Mexibar aren't in OSM. A named Photon `other` is a `poi` now
      (Nørrebroparken resolves at 50 m) but no current row needed it. Next:
      decide whether an `llm`-only place belongs on the map at all, or have
      the prompt give the local name ("Dronning Louises Bro").

- [ ] **A retelling with new detail is not merged.** (2026-09-27, content
      537) Tove Ditlevsen growing up on Hedebygade is told at 2:24 and 5:44
      with 0.20 word overlap, under `_same_story`'s 0.3. Distinct stories at
      one place peak at 0.07 on the corpus, but that is 19 memories. Next:
      collect a few more before moving the bar to 0.2.

- [ ] **A name misspelled in the captions is copied into every summary.**
      (2026-09-27, content 535) "Jørgen Let" for Leth, from the
      auto-captions. Next: have the brief spell names from the title and
      source when they disagree with the transcript.

- [ ] **Prompt caching: only the classifier is left uncached.** Measured
      2026-09-27 on videos 535-537 (one burst worker): chunk 1 writes ~4.3k
      (system ~3.8k + source and brief ~0.5k), every later chunk reads it, and
      the judge's ~1.4k system prompt is read on passes two and three. The
      brief call (~14k, once a video) and the Haiku classifier (~0.2k prompt,
      under Haiku's 4,096 minimum) are never cached. Left: with several
      workers, a video's first wave of chunks may all write. Check the
      `cache read` log lines the first time more than one worker runs.

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
a subscription. Built 2026-09-27: the gate, RevenueCat's webhook and
read-back (`api/billing.py`), the paywall (F35) and its two e2e flows (docs/10
*A subscription opens the map*, *RevenueCat sells it; our table decides*).
Nothing can be bought until the stores exist, so everybody is free.

- [ ] **S6 The stores and RevenueCat.** (checked 2026-09-27) Waits on
      `STORE_ACCOUNT` and `DEPLOY` (the webhook needs a public URL). No code:
      - App Store Connect: the Paid Apps agreement, banking and tax (without
        them no product loads); one subscription group, monthly and yearly,
        auto-renewing, no introductory offer; an In-App Purchase key for
        RevenueCat; App Store Server Notifications to RevenueCat; a sandbox
        tester.
      - Play Console: the same two subscriptions; a service-account JSON for
        RevenueCat; real-time developer notifications (Pub/Sub) to RevenueCat.
      - RevenueCat: entitlement `map`, offering `default` with the monthly and
        annual packages, the webhook at `https://<deploy>/v1/billing/revenuecat`
        with `Bearer <REVENUECAT_WEBHOOK_SECRET>` as its Authorization, the
        secret server key into `REVENUECAT_API_KEY`, the public SDK keys into
        `EXPO_PUBLIC_REVENUECAT_IOS_KEY` / `_ANDROID_KEY` (eas.json).
      - Both listings and privacy disclosures name the subscription and
        purchases; the review note says how to reach the paywall.
      - Then on a real device: buy monthly, see the row, open a pin from the
        map, cancel in the sandbox, see it lapse. Nothing has ever called
        RevenueCat for real: the tests patch `billing.fetch_subscriber`.
- [ ] **Revisit RevenueCat when its fee outgrows two integrations.** Free
      under $2.5k/month, then 1% of gross (before VAT and the store cut). When
      that fee passes what it costs to keep the App Store Server API and Play
      Developer API direct, or RevenueCat blocks something we need, leave: only
      `billing.fetch_subscriber` and the app's SDK change, since
      `subscriptions` stays ours.

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

## Copenhagen sources

Researched 2026-09-27 (channel pages, caption tracks and terms, checked on the
primary sites). No show matches Tuesdays with Stories (comedians telling their
own stories about named spots) in English or Danish. The candidates, the
rejects and why are rows now: `python -m pipeline.sources list`.

- [ ] **Screen the discovered local TV and archives.** (checked 2026-09-27) The
      first `discover` run found Bispebjerg Lokal-TV, Christianshavns Kvarter,
      Frederiksberg Lokal TV, Kgs. Enghave Lokalhistoriske Arkiv, Foreningen
      Gadeliv, Peter Jensen's "Vesterbro-minder 1900–1920". `screen` each;
      promote the ones that pass to `trial`.
- [ ] **Trial the Wollstonecraft letters** (source 11). (checked 2026-09-27)
      Screened 3 of 3 windows passing. `enqueue` one part, then judge: the
      historical prompt reads a first-person memoir, and 1795 street names may
      not geocode.
- [ ] **One-off videos.** (checked 2026-09-27) Andrew Schulz "Dropping In #20"
      (Copenhagen) and Ari Shaffir "You Be Trippin'" with Iain Stirling
      (Denmark): `ingest --video … --to <id>` under their channels.
- [ ] **Sources that need their own plan.** (checked 2026-09-27) From the
      source-scaling ideation, each with a named catch:
      - Walk-and-talk recording: someone narrates a walk; Whisper plus the GPS
        track at each timestamp is the coordinate, no geocoding. A product
        feature, not a source.
      - Podcasts: RSS plus local Whisper into `transcripts`, never DR.
      - Public-domain memoirs (Andersen's *Mit Livs Eventyr*, Nexø's
        *Erindringer*): Runeberg / ADL, after the Wollstonecraft trial says
        whether books pay. Needs historical street names.
      - Politiets Registerblade (1890–1923): who lived at each address. Filler.
      - Film locations (DFI, fan lists): already placed, very stop-worthy.
      - Prompt at a thin spot: "Were you ever here?" opens the submit sheet.
- [ ] **Open sources with coordinates.** (checked 2026-09-27) Wikipedia and
      Wikidata: 4,321 items within 5 km of Rådhuspladsen (text CC BY-SA,
      data CC0); about famous people, not personal memories. OSM memorial
      plaques: 108 in the centre (ODbL). Both fit the text-source path in
      `crawler/sources.py`.
- [ ] **Run the backlog through the Batch API.** (checked 2026-09-27) Half
      price, and nothing in the pipeline is waiting on an answer. Worth it
      before a whole-channel run, not for one video.

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

- [ ] **`API_CREDITS`** (checked 2026-09-27) — funded 2026-09-27 ($20), and
      content 534 extracted end to end on Sonnet 5 (20 memories), so the
      schema is accepted. Everything below is still to do. **There is no
      `--limit` flag**: `python -m pipeline.extract` bills every pending
      video. To spend cents: `python -m pipeline.enqueue --video <content_id>`,
      then `--status <id>`. Next: `quality --compare` against the old prompt, the
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
- [ ] **`STADSARKIV_ERINDRINGER`** (checked 2026-09-27) — the best Copenhagen
      source: 3,322 written memories at street level, 1,516 transcribed, from
      about 1890 on. The writers keep copyright, and the only machine access is
      the archive's undocumented Solr search
      (`solr.kbharkiv.dk/solr/apacs_core/select?q=collection_id:18`). Ask the
      archive (Eva Greve Mortensen) for written permission to summarise them
      before ingesting any. Strip the writers' addresses and phone numbers.
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
