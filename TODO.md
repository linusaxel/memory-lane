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

- **The gate says RED, not INFRA, when Docker is down.** 2026-10-01: with the
  daemon stopped, `./loop/verify.sh` exited 1 with 413 db-test errors, which
  reads as "fix your code" until you find "Cannot connect to the Docker daemon"
  in the setup errors. Fix: `docker info` up front in verify.sh, exit 2 if it fails.
- **`walk-and-unlock` is red on main.** 2026-10-01: after f448aea, stop 3's
  "Stop 3 of 4. Where the night went long, dev seed. Locked, within reach."
  never shows, every run, with or without the bottom-row change, so a layout
  change took a baseline run (~6 min) to clear. Cause (seen on the failure
  screenshot): by stop 3 the welcome unlock and yesterday's are spent and a
  simulator has no steps, so the stop is short ("1,000 steps to go"), not
  unlockable. Fix: give the flow's account steps, or subscribe it, before the
  walk.
- **`test_route_order` reddens the gate at random.** 2026-10-01:
  `ROUTE_SEED=3605168176` fails
  `test_within_budget_repeatable_and_full_as_the_budget_allows` on untouched
  main, so a gate run went RED on a change that never touched routing, and it
  took a stash and a replay to prove that. Fix: make that seed pass (or relax
  the "nothing more fits" check by the circuity margin) and pin it in the test.
- **The streak and the unlock rules use different clocks.** 2026-10-01:
  `api/accounts.py` `current_streak(..., date.today())` uses the host's date,
  but everything else uses UTC `gate.today()`, which is exactly the bug
  `gate.py` warns about. Fix: pass `today()`.

- **`dedup --memories` misses a book's retellings when they sit on different
  place rows.** 2026-10-01: it found none of the dog, grocer or gallows pairs
  in source 204 (Schloss Friedrichsberg against Frederiksberg Slot, and so
  on), and Carl Møller had the same problem. They were found by reading 28
  rows by hand. Also, a hand-hide of the new fire telling left that scene
  with nothing visible, because the save-time check had already hidden the
  old one. Fix: compare the memories of one source with each other, whatever
  place they are on, and show pairs where one side is already hidden.
- **`quality --compare` shows one draw per chunk, and a chunk varies more
  than a prompt.** 2026-09-30: the stored baseline kept two Andersen memories
  from a chunk the same prompt leaves empty 6 times in 8, so the candidate
  read as a regression until it was rerun by hand (~50 extra calls). Fix: a
  `--runs N` that reports how often each chunk keeps something, per prompt.
- **Auto mode blocks `python -m pipeline.transcripts` and dev-database
  writes.** 2026-09-29: Claude Code's permission classifier refused the
  transcript fetch, leaving 105 videos untranscribed until a human ran it.
  2026-09-30: it refused a hand triage (merge two places, hide four memories)
  and its undo, each a round-trip through the founder. Fix: Bash allow rules in
  `.claude/settings.json` for `venv/bin/python -m pipeline.*`, or a human runs
  it with `!`.
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
- **A classifier prompt change can't be measured without a throwaway script.**
  2026-09-27: `classifier_audit` only re-extracts rejected chunks; comparing
  the old and new prompt over `classifier_verdicts.chunk_text` took a 70-line
  scratch replay. Fix: `classifier_audit --against <old prompt file>` that
  replays stored chunks through both prompts and prints flips per source.
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
      2026-10-01) Carl Møller went from 8 visible to 12, Oehlenschläger
      vol. I from 13 to 22, and Andersen from 5 to 10 (docs/04, *Carl Møller
      re-extracted*). Next Leonora Christina (203): reset `memories_extracted` for
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

Decided 2026-09-26 (the founder), changed 2026-09-30: three memories a day
open free from anywhere; after that, standing on one costs 1,000 steps, and a
subscription opens it for nothing (docs/10, *Three free a day, then steps
where you stand*). Built 2026-09-27: the gate, RevenueCat's webhook and
read-back (`api/billing.py`), the paywall (F35) and its two e2e flows (docs/10
*A subscription opens the map*, *RevenueCat sells it; our table decides*).
Nothing can be bought until the stores exist, so everybody is free.
Researched 2026-10-02: a currency, the map and the walk, in *Map, walk and
money* below.

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
- [ ] **Steps on a real iPhone.** (checked 2026-09-30) Built iOS-only
      (docs/10, *Three free a day, then steps where you stand*): 1,000 steps
      an unlock, from Core Motion via `src/steps.ts`. A simulator has no pedometer,
      so nothing has ever counted a real step. On a device: grant Motion &
      Fitness, walk, reopen, see the count at the top of the map rise once;
      deny it and the free three still open. Unverified: whether Core Motion misses steps
      only a Watch counted.
- [ ] **Steps on Android.** (checked 2026-09-30) `expo-sensors` can't read
      history there (it throws), so `syncSteps` returns early. Use
      `react-native-health-connect` v4 and its config plugin, `READ_STEPS` in
      `android.permissions`, 30 days back; aggregate with `dataOriginFilter` on
      the phone's own origin to leave out manual entries. Android 13 and below
      need the Health Connect app (`getSdkStatus`). Play needs the Health
      Connect declaration, a privacy-policy rationale screen in the app, and
      the Health apps declaration (Activity and Fitness). Google's docs say
      Health Connect counts steps itself on Android 14+; Niantic says it needs
      a tracker app: check on a device.
- [ ] **Store disclosures for steps.** (checked 2026-09-30) App Privacy:
      Fitness, linked to you, app functionality, not tracking. Add the step
      count to the DPIA the location data already needs.
- [ ] **A cap on the stored balance?** (checked 2026-09-30) None yet. Add one
      (~10k) if a hoard empties the map in an afternoon; tune the price on the
      corpus before launch, since pins are dense in the centre.

---

## Map, walk and money

Researched 2026-10-02 with eight parallel research passes over primary sources:
dev blogs, filings, GDC talks, papers, regulator texts and community reactions
to specific changes. Nothing here is decided. **D** marks a founder decision.
The other entries follow from those decisions. Nobody has published A/B data
on any of it, and no app the research found gates story text on standing
there, so every price below is borrowed from a neighbouring kind of app: tune
it on real data. Checked 2026-10-02 against docs/10 *Steps open a memory* and
*Pick one to start, then where you stand*.

### Decide first

- [ ] **E0 D: Are opens paid at all?** (checked 2026-10-02) Today a story
      opens on the spot for 1,000 steps, or free with the subscription. The
      research splits.
      - **Against charging (steps as a toll).** No walking app checked
        (Pikmin Bloom, Pokémon GO, Walkr, Monster Hunter Now, Dragon Quest
        Walk) charges steps for something you have already walked to. They
        *pay* for steps (growth, hatching, fuel) and use being there as the
        lock.
        - Adding conditions on top of being there drew the genre's worst
          backlash. Pokémon GO's 2021 cut of the radius from 80 m back to
          40 m caused a boycott, and Niantic reversed it
          (https://www.mcvuk.com/business-news/pokemon-go-reverses-on-its-controversial-pokestop-distance-requirement-changes/).
          The 2023 remote-raid cap drew 60k+ petition signatures and was
          framed as a "disability tax"
          (https://www.techradar.com/news/pokemon-go-raises-the-price-of-remote-raid-passes-inviting-concerns-of-ableism).
        - A step charge bites the same group: cyclists, bus riders, limited
          mobility.
        - Etkin (JCR 2016): showing a step count made people walk more and
          enjoy it less
          (https://www.fuqua.duke.edu/duke-fuqua-insights/etkin-counting-steps).
      - **For charging (walking is the "wait").** Story apps live on
        wait-or-pay. Kakao Page's CEO: "I will pay to save time"
        (https://www.koreajoongangdaily.com/business/kakao-proves-japan-has-an-appetite-for-korean-webtoons/10588321).
        - Pocket FM: $500M a year, $415M of it from users unlocking
          episodes (https://techcrunch.com/?p=3162605).
        - Webtoon: paid content was 80.2% of 2023 revenue, at an ARPPU of
          $11.5 a month from microtransactions
          (https://www.sec.gov/Archives/edgar/data/1997859/000119312524151708/d396527ds1.htm).
        - In Memory Lane the walk is the wait, and opening a story is the only
          thing on sale with real pull.
      - **Recommendation:** keep opens paid, and fix what made it feel like a
        toll, which is arriving with nothing to pay. Make the first open of
        the day free, and earn enough by walking that walkers rarely pay
        money (E2). If the answer is no, the subscription needs something
        else to sell (E5), and the step economy goes.
- [ ] **E1 D: Licensing before money.** (checked 2026-10-02) This blocks any
      paid open of a DR-derived story, and it matters more than the currency.
      - **DR treats archive clips as commercial "other business".** The
        accounting-separation rules stop it giving them away for commercial
        use, and the quoted price is about 80 DKK a second plus VAT. Sources:
        Folketing KUU bilag 39
        (https://www.ft.dk/samling/20211/almdel/KUU/bilag/39/2490051.pdf) and
        spm 91
        (https://ft.dk/samling/20211/almdel/kuu/spm/91/svar/1847170/2514752.pdf).
        Both returned 403, so the figures come from search excerpts: verify
        them.
      - **The free DR archive at the Royal Library is narrow.** Its Copydan
        Arkiv collective licence streams to private citizens on KB's own site
        "and not in any other way". It excludes AI use, training included,
        without explicit consent
        (https://kum.dk/fileadmin/_kum/2_Kulturomraader/Ophavsret/Aftalelicensgodkendelser/Generelle/2025-03-Afgoerelse_om_godkendelse_af_Copydan_Arkiv_iht.____50__stk._4__jf._stk._2.pdf).
        The pipeline's LLM extraction may clash with that.
      - **Linking is lawful; framing that gets round access restrictions is
        not.** CJEU C-466/12 Svensson; C-392/19 VG Bild-Kunst.
      - A paywall in front of free public-service content would likely be
        challenged by DR and Copydan, and it would look bad in Denmark.
      - **Safe defaults:** charge for the walk, the curation or the
        convenience, never for a DR clip. Link out to DR's own player, or
        license per clip from DR's sales arm.
      - Add this to the lawyer's read of docs/10 *The sources' legal footing*
        (YouTube is already "No, as built").
      - If it stays open: let Embers buy only stories from sources that are
        clearly ours to charge for (Gutenberg, user posts, licensed), and keep
        the rest free on the spot.

### The currency: one, called Embers

- [ ] **E2 Embers: earned by walking, also sold.** (checked 2026-10-02)
      Depends on E0. Supersedes the 1,000-step price in `api/models.py`
      (`STEPS_PER_UNLOCK`).
      - **Earn:** 1 Ember per 1,000 steps, capped at 5 a day; +1 for finishing
        a walk.
        - Why a cap: a slow trickle is how Pokémon GO keeps free coins from
          emptying the shop. Gym coins are capped at 50 a day, down from 100
          in 2017 (https://pocketmonsters.net/news/4153).
        - Every walk-to-earn currency that could be cashed out collapsed
          under inflation: STEPN's GST −99.7%, monthly users 700K → 45K
          (https://decrypt.co/122460); SWEAT −93%, earning made 400% harder
          (https://dailycoin.com/sweatcoin-increases-minting-difficulty-as-sweat-economy-sweat-sinks-22/).
          So Embers are never cashable and never tradeable.
      - **Buy:** 5 for 29 DKK, 15 for 69 DKK, 40 for 149 DKK, about 3.7–5.8 DKK
        an open. That sits above Webtoon and Radish (2–3 DKK an episode)
        because each open costs a walk too. An untested guess.
      - **At the lock:** offer "Open for 7 DKK" as a direct purchase, so
        nobody has to buy a pack for one story. This meets the CPC rule
        against forcing bundles (E3).
      - **Spends**, all next to being there and none past it:

        | Spend | Cost | Based on |
        |---|---|---|
        | Open a story you are standing at | 1 | Pay-per-episode (Pocket FM, Webtoon) |
        | First open of the day | free | A cyclist arriving with nothing still gets in |
        | A stop on a planned walk | ½ | Cheaper stops give the walk a reason to exist (W4) |
        | Reach: 20 m → 60 m for one walk | 3 | Pokémon GO lures and incense, the 80 m radius |
        | Themed walk with a stop only the walk reaches | 99 DKK or 15 | StoryHunt's premium Copenhagen walks, 99 DKK (https://www.storyhunt.io/en/copenhagenlocalwalks) |

      - **Reach is sold per walk and never taken back.** Players treat range
        as owed once given; the 80 m reversal above shows it.
      - **Server:** the balance is Embers on `users`, not steps. `/v1/me/steps`
        keeps its watermark and converts to Embers on credit. The cap is
        applied per UTC day (`gate.today()`). Purchases and the subscription
        go through RevenueCat (consumables on the same offering) and the
        `subscriptions` read-back pattern. The app is never believed.
      - Keep the existing order: a subscriber pays nothing, then the free open
        of the day, then an Ember, then the welcome unlock, then 403. Re-derive
        this against *Pick one to start* before building.
- [ ] **E3 The rules any Ember must meet.** (checked 2026-10-02) Hard
      constraints, not choices.
      - **Apple 3.1.1:** currency only through IAP; bought currency "may not
        expire"; loot-box odds disclosed
        (https://developer.apple.com/app-store/review/guidelines/).
      - **Apple 3.2.2** allows rewards for in-app actions.
      - **Apple 5.1.3(i):** Motion & Fitness data is never used for ads,
        marketing or analytics. Turning steps into credit is not banned, and
        step-reward apps are live, but that is a reading, not a ruling.
      - **EU CPC key principles on in-game virtual currencies, 21 Mar 2025**
        (https://commission.europa.eu/live-work-travel-eu/consumer-rights-and-complaints/enforcement-consumer-protection/coordinated-actions/social-media-online-games-and-search-engines_en;
        text: https://esportslegal.news/wp-content/uploads/2025/03/Key-principles-on-in-game-virtual-currencies.pdf):
        - Show the DKK price next to every Ember price, worked out without
          bulk discounts.
        - One currency, no exchanges.
        - Price items in whole Embers, with no leftovers stranded by pack
          sizes.
        - A 14-day withdrawal right on unused Embers.
        - No one-sided change to what an Ember is worth.
        - Spending off by default for minors, and no "buy now" pressure at
          children.
        - Currency earned only in play is out of scope, but Embers are also
          bought, so all of it applies.
      - **Denmark:** Forbrugerrådet Tænk reported 17 games, Pokémon GO among
        them, to Forbrugerombudsmanden on 11 Sep 2024 for showing prices only
        in virtual currency
        (https://taenk.dk/presse/forbrugerraadet-taenk-anmelder-17-spil-manipulere-spillerne-med-virtuel-valuta).
        No ruling has been found yet.
      - **The Digital Fairness Act:** proposal expected Q3–Q4 2026. It is
        weighing real-money prices on items bought with currency, and loot
        boxes. Check whether it has been published before building.
      - **If the app ever shuts:** refund or convert unspent Embers. Kindle
        Vella turned unused tokens into gift-card credit
        (https://www.geekwire.com/2024/amazon-to-shut-down-kindle-vella-serial-book-platform-saying-it-hasnt-caught-on-as-wed-hoped/).
        Radish let them vanish
        (https://kcomicsbeat.com/2025/07/03/radish-fiction-to-shut-down-by-end-of-2025/).
- [ ] **E4 Never sell these.** (checked 2026-10-02) Write each into docs/10
      when E2 lands, so nobody adds it later.
      - **Reading from afar.** Pokémon GO's remote raid pass earned well, then
        "came to dominate the experience… in a way we never intended"
        (https://techcrunch.com/2023/03/30/pokemon-go-will-raise-the-price-of-remote-raid-passes).
        Pulling it back cost a boycott and, per AppMagic (disputed by
        Niantic), a five-year revenue low
        (https://videogameschronicle.com/news/pokemon-go-developer-denies-that-its-earnings-have-dropped-to-a-five-year-low).
        This is already the line in *Pick one to start*.
      - **A second currency.** Choices runs two paid currencies, and players
        called a quiet 16→22 diamond rise "scummy"
        (https://www.pocketgamer.biz/how-does-choices-stories-you-play-monetise/).
      - **Loot boxes or any random paid reward.** Illegal in Belgium (fines up
        to €800k), and a likely DFA target. The FTC's Genshin settlement
        ($20m, Jan 2025) covered hidden currency tiers and odds
        (https://www.ftc.gov/system/files/ftc_gov/pdf/ferguson-cognosphere-concurrence.pdf).
      - **Countdown offers and one-tap purchases.** The FTC's $245m Epic
        settlement covered these dark patterns
        (https://ftc.gov/news-events/news/press-releases/2023/09/ftc-announces-claims-process-fortnite-players-who-were-charged-unwanted-items).
      - **Step-energy that refills.** Duolingo's switch to Energy raised its
        metrics, but drew a petition ("two lessons a day")
        (https://www.change.org/p/duolingo-hearts-not-energy). With a handful
        of opens a day, an energy pool only reads as a squeeze.
      - **Selling location or step data.** GDPR, Apple 5.1.3, and it clashes
        with the device-UUID identity model.
- [ ] **E5 Memory Lane+ (the subscription).** (checked 2026-10-02)
      - 49 DKK a month or 349 DKK a year: unlimited opens on the spot, themed
        walks included, 10 Embers a month.
      - Benchmarks: Western Europe medians are $8.99 a month and $39.44 a year
        (https://revenuecat.com/report). Adapty finds Dutch users pay 62% more
        than US users. No Nordic median was found.
      - Plan for the subscription to carry about 80% of revenue. At Duolingo
        it was 81% in FY2024, and in-app purchases only $34.7M in 2023
        (https://www.sec.gov/Archives/edgar/data/1562088/000156208825000039/q4fy24duolingo12-31x24shar.htm).
      - Push annual: 44.1% of annual plans are retained after a year, against
        17.0% of monthly ones (RevenueCat 2025).
      - Updates S6: add the consumables, and change the entitlement's
        meaning.

### The map: keep showing every pin

- [ ] **V1 Record why the map shows every locked pin.** (checked 2026-10-02)
      Decided already (docs/10 *A map of what is locked*); add this evidence
      to that entry.
      - Every location app that lasted shows its targets: Ingress, Pokémon GO
        after the fix, Geocaching, Wandrer, Atlas Obscura.
      - Pokémon GO's worst-punished change took away "what is near me, and
        where". The tracker was removed 30 Jul 2016, the rating fell to about
        1.5★, and players got refunds
        (https://proof.csmonitor.com/Technology/2016/0802/Pokemon-Go-creators-remove-a-key-feature-risking-users-wrath).
        Niantic's fix was to show more: Nearby and Sightings
        (https://www.androidpolice.com/2016/11/23/niantic-ditto-pokemon-go-tweaks-nearby-more-regions/).
      - Curiosity needs a gap you can feel (Loewenstein 1994) and peaks at
        partial knowledge (Kang et al. 2009,
        https://pubmed.ncbi.nlm.nih.gov/19619181/). A hidden pin makes no
        gap. Place, year, source and tags with no text sits at that peak.
      - In the field, people plan around a preview but save the content for
        the spot. In Smith et al. 2019's study of 29 locals on three history
        tours, "no participants took the opportunity to view the stop-based
        content in advance"
        (https://dirkvl.info/wp-content/uploads/2019/11/smith-et-al_chapter-glam.pdf).
      - Hiding pins until you have steps fails worst at the first session:
        at home, with 0 steps, on an empty map.
      - The spoiler research is contested (Leavitt & Christenfeld 2011 vs the
        failed replications), so build on neither side of it.
- [ ] **V2 Full detail near you, a glow further out.** (checked 2026-10-02)
      - The nearest three locks get a strong pin with direction and distance.
        Further ones thin to soft clusters or areas, as Pokémon GO's
        "Sightings" do.
      - Zelda BotW's CEDEC 2017 talk: guides placed everywhere made players
        feel railroaded, and varying what is visible fixed it
        (https://gigazine.net/gsc_news/en/20171004-breath-of-the-wild-design-secret).
        Assassin's Creed's creator apologised for checklist maps
        (https://gamespot.com/articles/patrice-desilets-creator-of-assassins-creed-has-ap/1100-6470759/).
      - Risk: a wall of locks reads as a checklist or a paywall (the
        Geocaching premium-cache resentment).
      - Fits the one-pin rule ("Pins: one kind").
- [ ] **V3 "What to look at when you're there" on the peek.** (checked
      2026-10-02)
      - Participants in Smith et al. 2019 wanted to be told what to look at,
        and it helps when GPS wobbles near 20 m. Riot! 1831's immersion broke
        on GPS error (https://www.roaring-girl.com/work/1831-riot/).
      - It must stay a pointer to the spot ("the corner doorway, the green
        tiles"), never a line of the story. *A locked memory says what it is,
        not what it says* rejected a teaser line.
      - Needs a new extracted field, so measure it before and after, as
        docs/04 *Memory quality* requires.
- [ ] **V4 Later, maybe: fog as a record, not a gate.** (checked 2026-10-02)
      - Brighten the streets you have walked; the pins stay visible.
      - Fog of World (4.81★, 3.6K ratings) and Wandrer's untravelled-roads
        view (https://news.wandrer.earth/2026/01/30/wandrer-untraveled-roads.html)
        work because the fog covers your own record, not the content.
      - Could fold into G3/G7.

### The walk: give it a reason to exist

Today a walk's stops cost the same as any pin. Its only rewards are the streak
(F27), the finish card and the journal grouping, so "Walk here" to one chosen
pin beats it. No published A/B tests compare curated routes with free choice.

- [ ] **W1 A stop only the walk reaches.** (checked 2026-10-02) The strongest
      mechanism found.
      - One stop shows as "?" and is never drawn on the map; it opens when you
        reach it.
      - Two cases point the same way. Pokémon GO's Routes is widely disliked,
        yet Zygarde Cells, which drop only on Routes, kept people walking them
        (https://mein-mmo.de/en/pokemon-go-trainers-spot-limit-for-a-rare-item-that-is-stupid,1054960).
        Adventure Lab's bonus cache opens only for finishers
        (https://www.geocaching.com/geocache/GC9CYAF).
      - Uncertain rewards motivate more than sure ones (Shen, Fishbach & Hsee
        2015, https://www.chicagobooth.edu/review/uncertainty-can-improve-motivation),
        and a resolved tease is a net positive (Ruan, Hsee & Lu 2018).
      - Server: `api/routes.py` picks the hidden stop from memories not near
        any other pin. The unlock vets it like any stop. Its locked peek
        withholds even the place until you are within reach. Avoid a daily
        cap that turns it into a grind.
      - The gate is unchanged: it opens standing there, like any stop.
- [ ] **W2 Start at "1 of 5", with a ring that fills.** (checked 2026-10-02)
      - Count the stop you are standing at, or the welcome unlock, as the
        first.
      - Endowed progress: car-wash cards pre-stamped 2 of 10 were redeemed by
        34%, against 19% for blank 0 of 8 cards, with the same effort
        (Nunes & Drèze 2006, https://coglode.com/nuggets/endowed-progress-effect).
      - The goal gradient: people speed up near the reward (Kivetz et al.
        2006, https://business.columbia.edu/sites/default/files-efs/pubfiles/1200/goalgradient.pdf).
      - Strong in the lab, untested in walking apps.
- [ ] **W3 Loose walks: skip and reorder.** (checked 2026-10-02)
      - In Smith et al. 2019, every participant changed the prescribed route:
        reordered stops, skipped some, took the tram.
      - Free roaming split people too. Some loved it; others hated "the
        uncertainty" and wanted visited spots marked.
      - So a walk is finished when its stops are opened, in any order, and a
        stop can be dropped without ending the walk. Check
        `ROUTE_COMPLETED_QUERY`.
      - Keep stories short. People found more than 5 minutes too long but
        still wanted more coverage.
- [ ] **W4 Walk stops at ½ Ember.** (checked 2026-10-02) Part of E2. Makes
      the walk the cheaper choice. Moderate evidence: economics, plus Nunes &
      Drèze indirectly. Keep the discount modest, or it undercuts the
      subscription.
- [ ] **W5 A broken streak can be repaired.** (checked 2026-10-02)
      - A broken streak hurts, more so when people blame themselves, and less
        when it can be repaired (Silverman & Barasch, JCR 2023, 7 studies,
        https://www.colorado.edu/business/faculty-research/2023/04/19/or-track-how-broken-streaks-affect-consumer-decisions).
      - Duolingo: allowing two Streak Freezes instead of one lifted daily
        actives by 0.38% (https://blog.duolingo.com/how-duolingo-streak-builds-habit).
      - A repair could cost Embers: a sink that is not a toll.
      - Watch for streak anxiety. On its own a streak won't make anyone choose
        the walk.
      - Overlaps G5.
- [ ] **W6 D: Themed walks.** (checked 2026-10-02)
      - Four stops sharing an era, a person or a source, so the walk tells one
        story. This is the paid product in E2, E5 and E7.
      - It reverses docs/10 *Tags come from the text, and a walk has no
        theme*, so mark that entry Superseded if it goes ahead.
      - Evidence: moderate and qualitative. Zombies, Run! users rated story as
        the favourite feature (https://discovery.ucl.ac.uk/id/eprint/10139156/).
        Questo shows people pay for story walks, not that they keep them.

### Money from outside the player

- [ ] **E6 Pitch commissioned walks to the city.** (checked 2026-10-02)
      Probably year one's biggest revenue line.
      - Copenhagen's Budget 2024 set aside 2.1M DKK for "The Copenhagen App".
        The city runs Copenhagen Local Walks, one co-funded with Frederiksberg.
        It leads a 35M DKK EU Urban Initiative tourism project (about 5.5M DKK
        to the administration over 3.5 years from Dec 2024) with Wonderful
        Copenhagen, Nationalmuseet, Københavns Museum and StoryHunt
        (https://kk.dk/sites/default/files/agenda/385094d2-b65c-48bb-834c-f898e6c0fc8a/56179e1b-ac0b-422e-a21c-0f3ae234d508-bilag-7_0.pdf).
      - StoryHunt is the incumbent: 8 free walks for the city, 11 premium at
        99 DKK.
      - What the city pays for is free walks that spread tourists out.
      - Guessed at 50–300K DKK in year one. Needs a sales conversation, not
        code.
- [ ] **E7 Premium walks on GetYourGuide / TripAdvisor.** (checked
      2026-10-02)
      - Questo sells this way, on revenue share
        (https://tech.eu/2021/02/18/questo-funding/). Agencies take 20–25%
        and app stores 15% (VoiceMap's numbers,
        https://docs.voicemap.me/tour-publishers/dashboard-details/).
      - Only on public-domain or licensed sources (E1).
      - Guessed at 20–150K DKK.
- [ ] **E8 Later: sponsored stops.** (checked 2026-10-02)
      - Niantic charges "less than $0.50 per daily unique visit", and it
        works only at McDonald's-scale footfall
        (https://techcrunch.com/2017/05/31/pokemon-go-sponsorship-price).
      - Yelp's paying ad locations fell 5% in 2024, mostly restaurants and
        retail (https://www.sec.gov/Archives/edgar/data/1345016/000134501625000007/yelp-20241231.htm),
        so small cafés churn.
      - Nothing found shows per-visit deals working in Copenhagen. Revisit
        after real traffic, and label it if built.
- [ ] **Not doing: walk-to-earn with a brand marketplace or offerwall.**
      (checked 2026-10-02)
      - WeWard (20M users) and Sweatcoin (about $20M revenue in 2023) work at
        millions of monthly users. Below about 1M it earns close to nothing.
        WeWard's founder said blockchain was "simply not economically viable"
        at 3 million users
        (https://theunblocked.substack.com/p/weward-sortir-de-la-blockchain-pour).
      - Delete this entry if the scale ever comes.

### Plan against these numbers

- [ ] **E9 Benchmarks for the business case.** (checked 2026-10-02)
      - **Download to paid:** 2.0% median (freemium 2.1%, hard paywall 10.7%)
        (https://revenuecat.com/report).
      - **Revenue per install at D60:** Health & Fitness $0.66, Gaming $0.14.
        Travel trials convert best, at 48.7%.
      - **Ceiling:** Pikmin Bloom made $8.4M (2022), $20.9M (2023), $33.4M
        (2024) and $100M lifetime, from passes, events and collection, never
        access
        (https://www.pocketgamer.biz/pikmin-bloom-hits-100m-after-four-years-as-2025-becomes-its-best-year-yet/).
        Niantic made about $33 per monthly user a year: an upper bound, not a
        target.
      - **No evidence** that adding consumables lifts a non-game subscription
        app. Hybrid adoption is 10–35% depending on the definition, mostly in
        games.
      - The economics research would rather sell single opens in DKK with no
        currency: less regulation, most of the benefit. The founder wants a
        currency, which is why E2 is one currency with a direct DKK purchase
        at the lock.

### The retention risk none of this fixes

- [ ] **Running out of stories.** (checked 2026-10-02)
      - Detour's users loved it, and it never caught on: "after 4 years… we
        never got widespread traction"
        (https://blog.southparkcommons.com/p/andrew-mason-shares-what-hes-learned-about-setting-company-values-and-knowing-when-to-pivot).
        Each tour took 3–4 months to produce.
      - Field Trip, Niantic's passive history feed with no goal, shut in 2019
        (https://www.engadget.com/2019-07-13-niantic-to-shut-down-field-trip.html).
        Ingress, built on the same places, became the company.
      - Pokémon GO: 28.5M US daily users in July 2016, under 5M within months
        (https://www.bgr.com/entertainment/pokemon-go-popularity-2016-users/).
      - Survivors (VoiceMap, izi.TRAVEL) scaled on content supplied by
        creators.
      - Once someone has done the stories near them, nothing above brings
        them back. That is a matter of corpus density and submissions, the
        Copenhagen sources sections. Track it as the first retention metric.

---

## Facelift

Researched 2026-10-01 (docs/09 part 9): the step apps, the iOS 26 / Expo 57
stack, and an audit of the screens against UI.md. F1 to F7 shipped the same
day (`git log`). Left:

- [ ] **F8 Lock Screen widget** (`expo-widgets`): the balance and the nearest
      story. After launch; skip Live Activities.

F9 to F12, from the founder on the simulator (docs/09 part 10), shipped the
same day: one walk card, Center on me, a heart that stays put, and the credit
at the top (docs/10, "One walk card" and "The credit is a byline").

---

## Feels like a game

The founder wants the app to feel like a game. Researched 2026-10-01 from
Pokémon GO, Pikmin Bloom, Monster Hunter Now, Zelda's Compendium, Hollow
Knight's Hunter's Journal, Duolingo's streak milestones and the "Juice it or
lose it" talk. The journal became a left drawer over the map the same day
(`src/Drawer.tsx`), with Settings moved to a cog on the map. The rule for all
of it: quiet by default, loud only for real progress. If everything sparkles,
nothing feels special. Checked 2026-10-01.

- [x] **G1 Name the pill.** Done 2026-10-01 another way: the pill is gone,
      and the journal is the book icon alone (docs/10, "Act at the bottom,
      read at the top").
- [ ] **G2 Trainer-card header.** A level and an XP bar under the name, and
      the streak as a flame chip on the avatar. Decide first what earns XP:
      memories, steps or walks. The streak's place is a past decision, under
      Walks only (2fcab97), so moving it reverses that.
- [ ] **G3 Collection grid.** Pokédex-style tiles in three states: unknown
      ("?"), a silhouette of a locked memory nearby, and opened. Counts like
      "12 / 40 found in Indre By", scoped by neighbourhood, never one total
      ("3 / 500" feels hopeless). A place you have heard every story of gets a
      gold border, as Hollow Knight marks a completed entry.
- [ ] **G4 Counters that tick up.** After a walk, opening the drawer rolls
      memories, places and steps up from their old values, with a haptic on
      each tick, instead of showing them already counted.
- [ ] **G5 Streak milestones.** At 7, 30 and 100 days, a moment of its own: a
      burst over the panel, a success haptic and a sound. Ordinary days stay
      quiet. Frame it around walks, and consider a rest day so a missed day
      does not punish (Duolingo's guilt design gets mixed reviews).
- [ ] **G6 A ceremony for something new.** An unseen unlock pulses. The first
      time it scrolls into view it scales 0.8 → 1.08 → 1 with a shimmer and a
      soft chime, then the flag clears.
- [ ] **G7 Today card.** First in Walks, like Pikmin Bloom's Lifelog: today's
      trace on a mini map, steps, and a week strip with a dot for each day you
      walked. Past walks below as postcards carrying what they opened.
- [ ] **G8 Tabs that follow a swipe.** Swipe between Walks, Unlocked and
      Mine, with the underline tracking the pager rather than jumping.
- [ ] **G9 Drawer on the UI thread.** The spring runs on React Native's
      Animated with the native driver, but the drag is JS-driven. Move it to
      reanimated + gesture-handler if it drops frames on a real phone. That
      needs a native rebuild.

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
