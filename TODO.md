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

- **A stale queue bills whatever it holds on the next worker run.** 2026-09-30:
  424 jobs enqueued 2026-09-29 and never run (325 Historisk Atlas stories,
  9 book chapters, 10 videos) sat behind a one-book re-extraction; `worker
  --burst` would have billed all of them. Found only by listing Redis. Fix:
  `worker` prints each queue's size and the contents behind it, and asks,
  before it starts.
- **Auto mode blocks `python -m pipeline.transcripts` and dev-database
  writes.** 2026-09-29: Claude Code's permission classifier refused the
  transcript fetch, leaving 105 videos untranscribed until a human ran it.
  2026-09-30: it refused a hand triage (merge two places, hide four memories)
  and its undo, each a round-trip through the founder. Fix: Bash allow rules in
  `.claude/settings.json` for `venv/bin/python -m pipeline.*`, or a human runs
  it with `!`.
- **`sources screen` says only "pass rate: None" when it screened nothing.**
  2026-09-29: two channels gave that with no reason. One had no long video
  in the newest nine; the other's only long video had no captions
  (`transcript_failed`). Finding out took two DB lookups. Fix: `screen` logs
  how many long videos it found, and how many have no captions.
- **`walking_matrix` returns zeros off the sidecar's map.** 2026-09-29: a
  scratch script with the tests' New York `ANCHOR` and `.env`'s `ROUTING_URL`
  got an all-zero matrix, because OSRM snaps every point to one node at the
  edge of Copenhagen. The solver picked walks on it without complaint, and it
  cost a round of misreading. `_plan_route` drops such points by snap, but
  `walking_matrix` passes the zeros on. Fix: in `street_table`, fall back to
  crow-flies when every snap is over `UNLOCK_RADIUS_METERS`.
- **The venv has no pip.** 2026-09-29: AGENTS.md and `docs/01-setup.md` say
  `pip install -r requirements.txt`, but `venv/` was made by uv, so
  `venv/bin/pip` and `python -m pip` both fail. Only `loop/verify.sh` names
  `uv pip install --python venv/bin/python`. Fix: say that in both docs.
- **Placement has no before/after tool.** 2026-09-28: `quality --compare`
  samples chunks by hash and scores summaries only. A venue-line change is
  judged on the chunks that produced `llm` places, by whether they geocode.
  That took a throwaway script (baseline read free from `extraction_chunks`,
  candidate billed, both run through `geocode.place`). Fix: a `--places` mode
  on `pipeline.quality` doing just that.
- **No flow attaches a photo, so uploads broke unseen.** 2026-09-28: SDK 57's
  global `expo/fetch` refuses React Native's `{ uri }` FormData part, and every
  photo and recording failed on the phone without a request reaching the API.
  Maestro can drive the system picker (tap "Library", "Allow Full Access", a
  cell by `point`), so it is testable. Fix: in `file-and-edit.yml`, attach the
  simulator's first stock photo before Post and assert its image on the card.
- **A damaged Pods tree fails as a link error.** 2026-09-28: the simulator slice
  of `Pods/React-Core-prebuilt/React.xcframework` had lost its `React` binary,
  so every build died on `ld: framework 'React' not found` and run.sh said
  "xcodebuild failed". A clean `build/` did not help and wiped the codegen
  output `pod install` keeps there; about 20 minutes to find. Fix: a run.sh
  preflight that the binary exists, else "rm -rf mobile/ios/Pods/React-Core-prebuilt && pod install".

- **Checking a preview-card change means minutes-long e2e flows.** 2026-09-27:
  the four flows that touch planning (look-around, lakes-loop, walk-and-unlock,
  notify-nearby) take 100-160 s each, and notify-nearby minutes more. Each one
  signs in from a cleared launch and walks a whole scenario, so re-checking one
  card string cost about 10 minutes, and the founder called it far too long.
  Fix: a short `plan-card.yml` (sign in, Plan a walk, drag, One way, Show me
  another) that the long flows stop re-asserting, so a card change is checked
  in under a minute.

- **file-and-edit.yml is red on main.** 2026-09-27: after Post, the flow's
  `".*ferry horn.* #food"` never shows, on a clean `main` too, so nothing after
  it (the journal's My Memories tab, edit, delete) is checked end to end. It
  cost a second e2e run to prove the break was not the journal change. Fix: find
  what the posted sheet now renders instead, and assert on that.
- **The venv has no pip.** 2026-09-27: AGENTS.md's quick start says
  `python3 -m venv` and `pip install`, but `venv/` was made by uv, so
  `venv/bin/pip` and `python -m pip` both fail; it took three tries to find
  `uv pip install --python venv/bin/python`. Fix: make the quick start say uv.
- **A route-size change breaks e2e, and run.sh calls it INFRA.** 2026-09-27:
  one stop a km made the 4 km default four stops; travel.py exits 3 on anything
  short of the flows' count, so run.sh rolled 20 starts and blamed the
  environment. The gate stayed green. Fix: a test in `tests/test_flows.py`
  that `_route_size(WALK_KM.initial km)` equals the stops walk-and-unlock.yml walks.
- **A classifier prompt change can't be measured without a throwaway script.**
  2026-09-27: `classifier_audit` only re-extracts rejected chunks; comparing
  the old and new prompt over `classifier_verdicts.chunk_text` took a 70-line
  scratch replay. Fix: `classifier_audit --against <old prompt file>` that
  replays stored chunks through both prompts and prints flips per source.
- **A run's cost can't be read from its log.** 2026-09-27: the worker logs
  cache read/write/uncached input per call but no output tokens, so three
  Københavnerliv videos were guessed at $0.30-0.50 each and only the console
  said $1-2. With $15 of credit, every batch needs a number. Fix: add
  `usage.output_tokens` to the same `cache read` log line in `pipeline/extract.py`.
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

- [ ] **Most places are still the model's guess.** (checked 2026-09-28)
      55 of 132 venue places are `llm` now (32 video, 20 book, 3 archive).
      Most are gone rather than misnamed: closed cinemas (Palladium, Vester
      Bio), hospitals (Sundholm, Frederikshospitalet), cafés (HH Café,
      Chickegrill). OSM has no such point. A "name it as the local map does,
      in the local language" venue line was measured on the 53 chunks behind
      them and not shipped: placed went 17 → 24 of kept, but kept fell 102 →
      88. Most gains are a street or a district standing in for the
      venue (Strøget, Kødbyen, "Frederiksberg"), and it misnamed two addresses
      (Toldbodgade → "Topgade 77"). Its real wins: Vor Frue Kirke,
      Assistens Kirkegård, Amalienborg, Gustav-Adolf-Gedenkstein. The book
      prompt kept German names either way (Friedrichshospital). Next: a
      closed place is a Wikidata or historical-map lookup, not a prompt
      fix; decide whether an `llm`-only pin is served at all.

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

## Launch readiness

From a readiness audit on 2026-09-28: what stands between "TODO done" and a
public launch that the rest of this file doesn't track. Blockers first.

- [ ] **Account deletion: Apple token revocation.** (checked 2026-09-28) `DELETE
      /v1/me` and the journal's two-press delete are built, but a Sign in with
      Apple account must also have its tokens revoked through Apple's REST
      API, which needs the `.p8` key (`STORE_ACCOUNT`). The GDPR copy is
      `python -m api.my_data`, answered by email: see the privacy policy entry.
- [ ] **The privacy policy is thin.** (checked 2026-09-29) Photos are
      re-encoded without EXIF now (`api/media.py`). No controller, no legal
      basis, no retention, no RevenueCat or geocoders. Contact reads `CONTACT_EMAIL`,
      unset until you pick an address.
      The generated `PrivacyInfo.xcprivacy` declares no collected data.
- [ ] **The corpus has no legal footing for a paid app.** (checked 2026-09-29)
      Researched source by source in docs/10, *The sources' legal footing*;
      a Danish lawyer still reads it before launch. The blockers:
      - YouTube: written permission per channel, drop the Webshare proxy,
        delete a transcript once it is extracted. Or drop the channels.
      - Historisk Atlas: ingest only CC BY, BY-SA and PD stories.
      - A report and takedown route on every memory (DSA Arts 16/17), for
        privacy, defamation and copyright alike.
      - Label summaries AI-generated (AI Act Art 50(4), in force now).
      - Suppress health, crime and WWII politics about private people, and
        place private people at the street, not the door.
      - A written legitimate-interest assessment and a DPIA.
- [ ] **No production database discipline.** (checked 2026-09-29)
      `pipeline.migrate` runs on every deploy now. No backups, no staging. Media lives on local
      disk, which a Railway redeploy loses without a volume.
- [ ] **Nobody hears about a crash.** (checked 2026-09-29) A render error
      shows `mobile/src/Crashed.tsx`, the API logs with timestamps, and `/`
      answers 503 without its database. Still no error reporting: nothing
      leaves the phone or the server. Pick a service (Sentry's free tier covers
      both), then report from `Crashed.componentDidCatch` and the API.
- [ ] **No `expo-updates`, so every fix waits on review.** (checked
      2026-09-29) Needs the EAS project (`EAS_BUILD`) for its update URL and a
      `runtimeVersion` policy. The `development` EAS profile still points at
      localhost, which is right for a dev client.

---

## Make memories worth the walk

A hand read of all 209 memories (docs/04, *Corpus read, 2026-09-29*) found
52 worth the walk. These are the fixes, in order. Measure each one against the
labels before and after (`python -m pipeline.quality --labels`). Every change
is to `pipeline/extract.py` unless named.

- [ ] **Re-extract the other books with the archival prompt.** (checked
      2026-09-30) Carl Møller went from 8 visible to 12 (docs/04, *Carl Møller
      re-extracted*). Next Oehlenschläger vol. I (204), Andersen (202) and
      Leonora Christina (203), one at a time: reset `memories_extracted` for
      the source, clear stale `extraction:<id>:memories`, enqueue, then
      `dedup --memories` and read its pairs before hiding any.
- [ ] **Judge v2 on the research rubric.** (checked 2026-09-30) Parked
      until grounding lands (the launch-area gate and dedup have). It was measured
      once (docs/04, *Judge v2, measured and parked*): most of the skips it
      keeps fail on place, duplicates or facts, which a judge reading a summary
      can't see. When it comes back, the three drop-gates (`private_person`
      within living memory, `promo`, `relative_time`) worked as worded there.
      The bar of two of incident, breach and feeling cost 40% of the walks, so
      retune that. Measure with `python -m pipeline.quality --labels --half
      tune`, then report `--half check` against v1's 32% / 96%.
- [ ] **Summary against its chunk.** (checked 2026-09-30) ~20 factual or
      speech-recognition errors: Tom "Christensen", Vestergade for
      Vimmelskaftet, lupus called cancer. Automatic fixes damaged walks and
      the first flag-only prompt flagged 77% (docs/04, *Summary against its
      chunk*). A verdict prompt that stores only contradictions is built on
      branch `parked/unsupported-flags`, never run: parked for interest-first
      work. Most of these are misheard names, which the next item targets.
      Separately, and unmeasured: have the extraction prompt spell known
      people as they are in print.
- [ ] **Then-vs-now: finish the backfill, then the points.** (checked
      2026-09-30) `pipeline/now.py` is built (docs/10, *What is there now comes
      from OSM, not the model*). The first run looked at 14 places and confirmed
      4 before overpass-api.de started refusing this IP. Run `python -m
      pipeline.now` again until it logs no "did not answer". Next, the ~20 bars that
      OSM stores as points need an `around` query, which the public server
      times out on. Then check that the ranking reads better.
- [ ] **Let a visible oddity with a life story pass.** (checked 2026-09-30)
      The Weather Girls on Richshuset are the north star (docs/04, *The north
      star*), and `HISTORICAL_SYSTEM_PROMPT`'s static-description rule would
      reject them. Narrow the rule so that something still visible, working or
      odd, with a dated history (made, stopped, restored), passes. Add the
      Weather Girls as a worked pass example. Measure with `python -m
      pipeline.quality --compare` before it ships.

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

- [ ] **arkiv.dk: excluded.** (checked 2026-09-29) 550+ archives, no public
      API, and its terms say private use only, never commercial. Licensing
      happens item by item with each local archive; plan no sprint around it.
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

- [ ] **Decide on the local TV channels.** (checked 2026-09-29) All screened.
      Your call, by the funnel's rule. For scale, the two active channels pass 0.85–1.00
      at 6–31 memories an hour. NTV Nørrebro (144) passes 0.57 at 2.5/h and
      Bispebjerg Lokal-TV (146) 0.47 at 1.3/h, both from trial extractions
      already made. Frederiksberg Lokal TV (159) passes 0.42 and Christianshavns
      Kvarter (155) 0.32, not yet trialled. Rejected Peter Jensen (152, a DR
      radio archive). Paused Kgs. Enghave (176, no captions, waits on Whisper).
      Foreningen Gadeliv was never a row.
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
- [ ] **Set up the Webshare proxy.** (2026-09-27) The code is in;
      transcripts stay capped at ~40 a day until this is done.
      1. Buy Webshare's **rotating residential** plan (~$3.50/GB, ~2,500
         transcripts), not the free proxies: those are datacenter and blocked.
      2. Put `WEBSHARE_PROXY_USERNAME` and `WEBSHARE_PROXY_PASSWORD` in `.env`
         (the proxy username and password on its dashboard, not the login).
      3. Run `python -m pipeline.transcripts --limit 60`. It works if it gets
         past ~40 without `RequestBlocked`. If not, the fallbacks are below.
      4. Put the drip back to a shorter delay in cron once it holds.
- [ ] **Get transcripts past YouTube's IP block.** (checked 2026-09-27) After
      ~40 caption fetches in a day, youtube-transcript-api gets
      `RequestBlocked`, and a batch stalls for hours. Captions, not the
      ~$0.02-0.05 a memory, are the ceiling on growth. It is an IP rate limit
      on the timedtext endpoint; no header, cookie or client trick lifts it.
      Shipped: the drip (`transcripts --limit`) and `WEBSHARE_PROXY_*`
      (rotating residential, ~$3.50/GB, ~2,500 transcripts). Left: the setup
      item above. Researched dead ends,
      so nobody re-tries them: the library's cookie auth (off since v1.1.0);
      yt-dlp `--remote-components ejs` (JS challenges, not 429s); yt-dlp with
      cookies ("page needs to be reloaded", yt-dlp #17389, fix in unmerged
      PR #17723); InnerTube `get_transcript` (HTTP 400 since 2025-12,
      YouTube.js #1102); Tor (exits banned); `captions.download` (own videos
      only). If Webshare IPs get blocked too (library #511):
      1. **Supadata**, 100 transcripts a month free, then $5/300.
      2. **yt-dlp + bgutil PO tokens, by hand:** `pip install
         bgutil-ytdlp-pot-provider`, its docker server on 4416, then
         `--extractor-args youtube:player_client=android_vr,web_embedded`.
         Same IP, so it only helps if the block is on the token, not the IP.
         Trap: `automatic_captions` lists machine translations into every
         language, so take only the `-orig` track.
      3. **Local Whisper on the audio** (yt-dlp `-x`), with the podcast source.
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
- **May a card run past 70 words?** (checked 2026-09-30) The Weather Girls
  post (docs/04, *The north star*) runs ~400 words and earns them. Short stays
  the default; the founder doesn't mind longer ones when the story carries it.
