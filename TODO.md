# Memory Lane — TODO

This file is the source of truth for open work. `loop/TASKS.yaml` is the
executable contract the `/ml-tick` loop runs against; it gets repopulated from
whichever phase here is active. If the two disagree, this file wins and
TASKS.yaml is wrong.

**Open work only.** A finished entry is deleted, not ticked: `git log -p
TODO.md` keeps its history, and a decision it carried goes to
`docs/10-decisions.md` first. Everything done before 2026-09-24 is in the
history of this file at `c4703b4`; the long research behind the money, walk and
source entries, before this file was consolidated, is at `9421fb0`.

**Every entry says when it was last checked** against the code, as
`checked YYYY-MM-DD`. More than a few days old means verify before acting on
it: a stale entry once sent a session to rebuild search, which had shipped a
week earlier.

---

## Friction

What slowed a session down or nearly shipped something wrong, and would again.
The rules for adding to it are in AGENTS.md, "Then log the friction". Newest first;
delete an entry when its fix lands.

- **A subscriber's Customize row has no handle for Maestro.** 2026-10-11: its
  testID (`themes-plus`) is set only for free walkers, and its text is whatever
  is chosen ("Before 1800"), so a flow can't find it by either; a tap by point
  landed on a walk instead and started one. Fix: give the row a testID always.

- **The $ column in docs/04 is a guess.** 2026-10-11: no token usage is stored
  anywhere, so every Road-to-1,000 row priced memories at $0.25 each; the real
  Batches API usage said ~$0.55 a good one, 71% of it unserved research. It took
  a scratch script over `batches.list()` to find. Fix: `batch.send` logs each
  batch's $ from `result.message.usage`.
- **The dev pin silently beats the simulator's location.** 2026-10-11:
  `EXPO_PUBLIC_DEV_LOCATION` in `mobile/.env` overrides `simctl location` and
  Maestro's `setLocation`, so a walk driven on the dev sim never reaches its
  stop and nothing says why; it cost two blind runs. Fix: a `--walk` flag on
  `mobile/scripts/sim.sh` that starts Metro with the pin empty.

- **Walk scores are never refreshed when the rubric changes.** 2026-10-10:
  re-scoring 68 memories, 10 scored on 09-27 fell from 6-8 to 3-5 and stayed
  there on two reruns; 81 of 261 good memories carry pre-October scores, so
  "how far from the goal" is inflated. Fix: store the prompt's hash beside
  `walk_score` and have `walk_score --all` re-score the stale ones.

- **The source screen fails biographies that hold a spot scene.** 2026-10-10:
  Haiku's screen scored Kirstine Meyer's Ørsted essays 0.00 and 0.25, rejecting
  the 1820 Nørregade discovery window as "not personal experiences"; the
  screen's 0.3 bar would have dropped it. Fix: `CLASSIFIER_PROMPT` in
  `pipeline/tasks.py` asks whether something happened at a named spot, not
  whether it is first-hand.

- **No e2e flow screenshots the locket.** 2026-10-10: porting the unlock
  engine, walk-and-unlock passed green with nothing showing the lid had drawn
  or swung. It took a hand loop of `simctl io screenshot` and contact sheets
  to see it. Fix: `takeScreenshot` in `steps/unlock-stop.yml` mid-hold and
  just after the commit.

- **A change to `mobile/app.json` leaves e2e on INFRA for the next
  session.** 2026-10-09: the privacy commit touched it and the next
  `./e2e/run.sh` stopped until a hand `expo prebuild --clean` and `pod
  install`. Again 2026-10-11 after 8b70bba (about 10 min lost, plus a
  `--build` rerun). Fix: run.sh prebuilds itself when its stamp is stale.

- **Explicit-path commits still carry other sessions' hunks.** 2026-10-09:
  a parallel session's `git commit docs/10-decisions.md` took another's
  uncommitted entry with it. Fix: shared docs are committed by one session
  at the end, or `git add -p` then `git commit` without paths.

- **Auto mode blocks dev-database writes.** 2026-09-30: Claude Code's
  permission classifier refused a hand triage (merge two places, hide four
  memories) and its undo, each a round-trip through the founder. The free
  pipeline commands are allowed in `.claude/settings.json` since 2026-10-04;
  writes stay a prompt on purpose. 2026-10-10: billed `pipeline.scenes` runs
  and the delete before a book's re-run were refused too, even after "you do
  it". Fix: a human runs them with `!`; say so up front, don't try first.

---

## Launch

What stands between today and a public launch. Unblocked first, then what
waits on `DEPLOY`, `EAS_BUILD` or `STORE_ACCOUNT` (see *Blocked on you*).
Retention is measured already: `python -m api.metrics`.

### Unblocked now

- [ ] **The privacy policy's placeholders and questions.** (checked
      2026-10-09) `api/privacy.py`, `mobile/store/privacy.md` and the
      DPIA/LIA in `docs/data-protection.md` are written against the code.
      Placeholders: the controller (`COMPANY`), `CONTACT_EMAIL`, log and
      backup retention days. The founder decides:
      1. Keep positions and device ids out of logs: `--no-access-log` in the
         Dockerfile, or lat/lng/device out of GET query strings. The device
         id is the credential, so today the access log is a list of keys.
      2. Railway's log and backup retention and region; sign the Railway and
         RevenueCat DPAs.
      3. Google's real name as the public display name by default, or a
         chosen one?
      4. Stop storing email, which nothing uses?
      5. A retention for inactive accounts' walks, opens and surprises.
      6. `pipeline.dedup`'s whole-corpus mode skips user posts, so Anthropic
         leaves the user-data list?
      7. A minimum age.
      8. Swedish or Danish law (the lawyer's first question).
      The policy had drifted far from the code, and `tests/test_store_copy.py`
      checks keywords only: reread it on any change to `api/write.py`,
      `api/accounts.py` or `geofence.ts`.
- [ ] **Nobody hears about a crash.** (checked 2026-10-04) A render error
      shows `mobile/src/Crashed.tsx`, the API logs with timestamps, and `/`
      answers 503 without its database. Nothing leaves the phone or the
      server. Pick a service (Sentry's free tier covers both), then report
      from `Crashed.componentDidCatch` and the API.
- [ ] **The corpus has no legal footing for a paid app.** (checked 2026-10-04)
      Researched source by source in docs/10, *The sources' legal footing*; a
      Danish lawyer still reads it before launch, together with *Licensing before money* below.
      - YouTube: written permission per channel, or drop the channels. The
        email is drafted (`docs/permission-request.md`). Run `python -m
        pipeline.transcripts --forget-extracted` once for the backlog before
        the first email goes out. The Webshare proxy (`WEBSHARE_PROXY_*`,
        built) is dropped with it; set it up only for a channel that said yes.
        The dead ends past YouTube's ~40-a-day caption block, and the
        fallbacks (Supadata, bgutil PO tokens, local Whisper), are in this
        file at `9421fb0`.
      - Historisk Atlas: ingest only CC BY, BY-SA and PD stories.
      - Suppress health, crime and WWII politics about private people, and
        place private people at the street, not the door.
      - A written legitimate-interest assessment and a DPIA (location, and the
        step count).
### Waits on an account

- [ ] **A waitlist page.** (checked 2026-10-04) One screenshot and an email
      field. It tells you whether anyone wants the app and fills the beta:
      Play's personal account wants 12 testers for 14 days. Serve it from the
      API beside `/privacy` (`api/privacy.py`), not Framer. Opt-in emails get
      their own table and are never matched to `identities`. Becomes the
      landing page later, plus store badges. Needs `DEPLOY`.
- [ ] **No production database discipline.** (checked 2026-10-04)
      `pipeline.migrate` runs on every deploy. No backups, no staging. Media
      lives on local disk, which a Railway redeploy loses without a volume
      (`railway.json` has none). Needs `DEPLOY`.
- [ ] **No `expo-updates`, so every fix waits on review.** (checked
      2026-10-04) Needs the EAS project (`EAS_BUILD`) for its update URL and a
      `runtimeVersion` policy. The `development` EAS profile still points at
      localhost, which is right for a dev client.
- [ ] **Account deletion: Apple token revocation.** (checked 2026-10-04)
      `DELETE /v1/me` and the journal's two-press delete are built, but a Sign
      in with Apple account must also have its tokens revoked through Apple's
      REST API, which needs the `.p8` key (`STORE_ACCOUNT`).
- [ ] **Set up the stores and RevenueCat.** (checked 2026-10-04) Waits on
      `STORE_ACCOUNT` and `DEPLOY` (the webhook needs a public URL). Built
      2026-09-27: the gate, the webhook and read-back (`api/billing.py`), the
      paywall and its F35 check in `walk-and-unlock.yml`. No code left:
      - App Store Connect: the Paid Apps agreement, banking and tax (without
        them no product loads); one subscription group, monthly and yearly,
        auto-renewing, no introductory offer; an In-App Purchase key for
        RevenueCat; App Store Server Notifications to RevenueCat; a sandbox
        tester.
      - Play Console: the same two subscriptions; a service-account JSON for
        RevenueCat; real-time developer notifications (Pub/Sub) to RevenueCat.
      - RevenueCat: the entitlement `plus`, offering `default` with the monthly and
        annual packages, the webhook at `https://<deploy>/v1/billing/revenuecat`
        with `Bearer <REVENUECAT_WEBHOOK_SECRET>` as its Authorization, the
        secret server key into `REVENUECAT_API_KEY`, the public SDK keys into
        `EXPO_PUBLIC_REVENUECAT_IOS_KEY` / `_ANDROID_KEY` (eas.json).
      - Both listings and privacy disclosures name the subscription and
        purchases; the review note says how to reach the paywall.
      - Then on a real device: buy monthly, see the row, plan a second walk
        the same day, cancel in the sandbox, see it lapse. Nothing has ever
        called RevenueCat for real: the tests patch `billing.fetch_subscriber`.
- [ ] **Once the stores exist: the paywall's follow-ups.** (checked 2026-10-04) From a
      Mobbin talk on ~3,000 paywalls; trials, exit-intent offers, fake urgency
      and pop-ups are ruled out (docs/08, *Subscribe for more walks*).
      - A "save X%" badge on yearly, computed from the two store products'
        `price`, shown only when it rounds to 10% or more.
      - Experiments through RevenueCat's offerings A/B before anything of our
        own. First test: the stats line against the outcome line.
      - Retention and LTV from `subscriptions`: renewals by plan and cohort
        month, and how many second walks subscribers take. Without second
        walks, the product sells something nobody uses.
      - Social proof once a store rating is worth showing: the rating and one
        real review. Never invented.
- [ ] **The store listing: give the screenshots 3–4 days.** (checked
      2026-10-04) Apple boosts a new app for its first week or two, once. Lead
      with the story cards; title, subtitle and keywords in Danish and
      English. Capture them from the e2e simulator flows so they stay current.
      Needs `STORE_ACCOUNT`.
- [ ] **The launch bar, then launch day.** (checked 2026-10-04) Launch when
      the closed-testing cohort comes back for days (`python -m api.metrics`);
      people gone after a day means not yet. Then email the waitlist; post in
      r/copenhagen, Danish local-history groups and press, and Product Hunt.
      Start a week ahead so it lands inside Apple's boost.
- [ ] **Lifecycle nudges, after launch.** (checked 2026-10-04) Sign-in emails
      are often Apple relays with no marketing consent, so a push to a user
      idle for 7 days: "there's a walk near you". Wait for `api.metrics` to
      show where people drop off.

---

## Memories worth the walk

A hand read of all 209 memories (docs/04, *Corpus read, 2026-09-29*) found 52
worth the walk. Measure every change against the labels before and after
(`python -m pipeline.quality --labels`). Every change is to
`pipeline/extract.py` unless named.

- [ ] **Scene-first: re-do every stored memory.** (2026-10-10) Scene-first
      shipped as the book path (docs/10, *Scene-first is the book path*).
      Now, under $50: redraw the scores from before 10-05, `dedup --memories`,
      then re-extract each book source with its old memories kept and dedup
      picking the stronger retelling; log good counts before and after in
      docs/04 *Road to coverage*. Still open: a kept "colour" flourish can be a
      generalisation; the mother's grave is lost to the check's nitpicks;
      `batch.py` for half price; the video path after measuring it; a
      book's pictures into its fact sheets, from Gutenberg's HTML edition
      (docs/10, *A card is rendered from its fact sheet*).
- [ ] **Memories written by tour guides.** (2026-10-04, the founder's idea)
      A licensed guide files the stories they already tell at a place: quality
      from the author, where `walk_score` is too weak a signal (r = 0.45). An
      ordinary public memory through the gate, a higher prize in `_prize`
      (`api/route_solver.py`), never held for subscribers; a byline, maybe a
      link to book their tour. Ties to *Pitch commissioned walks to the city*
      and *Premium walks on GetYourGuide*. Open: how a guide is marked (by
      hand, never on email), whether their memory says so before it opens,
      paid or credited.
- [ ] **Measure $/memory from the bill.** (2026-10-04) `python -m
      pipeline.cost --since 2026-10-04` answers it, but the key in `.env` is a
      personal `sk-ant-usr-` key and the Cost Report API refuses it
      (`permission_error`). Needs an Admin key (`sk-ant-admin01-`, Console,
      Settings, Admin keys). Then record the figure in docs/04 *What it
      costs*; the estimate is ~$0.25 a memory with seeding and enrichment.
- [ ] **Human labels, then let them decide.** (2026-10-05) Every judge and
      prompt number so far is against `walk_labels.json`, which an agent
      made, and the judge, fact-check and trim run on the extractor's own
      model. The founder labels ~100 memories (walk / maybe / skip) in
      `review.py`. Then, in order:
      1. Add Cohen's κ (judge against human) to `quality --labels`.
      2. Pit the 3-pass judge against a walk-score threshold. The judge is
         at 31-41% precision; walk score is at AUC 0.87.
      3. Route the judge and `unsupported()` through `GRADER_MODEL`.
      4. Sweep `unsupported()` effort: low, medium, default.
      5. A/B the full transcript as cached context with "extract from this
         window only" against the brief alone. That costs ~$0.002 a chunk;
         the whole-video single call already lost.
      GEPA (DSPy) on the extraction prompt only after those settle.
- [ ] **Pick the extraction model, measured.** (2026-10-04) Sonnet 5.5 is the
      default by assumption. Opus 5.5 at low effort kept 12 memories where
      Sonnet kept 33 from the same 50 chunks, but each scored itself; since
      2026-10-05 `GRADER_MODEL` scores every bake-off, and Fable 5.1 can be
      called. Next: run Sonnet 5.5, Opus 5.5 low and medium and Fable 5.1 over
      `quality --labels` for the judge, and `quality --compare` for the
      writer, read blind by a person. Pick per step; cost breaks a tie.
      Grade against the founder's labels (above), not the agent's. Prices
      2026-10-05, per 1M tokens in/out, batch half: Sonnet 5.5 $2/$10, Opus
      5.5 $4/$20, Fable 5.1 $10/$50. Leaderboards don't settle it: Vectara
      has no 5.x rows and measures summaries, not this task.
- [ ] **Move the classifier off Haiku 4.5.** (2026-10-05) Anthropic retires
      it "not sooner than 2026-10-15", with 60 days' notice. When the notice
      lands, set `CLASSIFIER_MODEL=claude-sonnet-5-5` in `.env` and Railway.
      `classify_chunk` already sends no thinking. Then run
      `classifier_audit.py` once to confirm the pass rate holds.
- [ ] **See the 1-hour cache hold in a real run.** (2026-10-05) Shipped
      with only the gate as proof. Run the next paid `enqueue --video`, or
      a batch, and check its `log_cache` lines: cache reads should be ≥10×
      writes. If they aren't, the TTL isn't taking.
- [ ] **Drop the redundant JSON lines from the prompts.** (2026-10-05)
      "Return JSON: {...}" (`SYSTEM_PROMPT`, `HISTORICAL_SYSTEM_PROMPT`) and
      "Return only valid JSON" (`USER_PROMPT_TEMPLATE`) repeat what the
      enforced schema already does. Fold the change into the next measured
      prompt change rather than paying for a measurement of its own.
- [ ] **The rest of the plaques.** (2026-10-04) 18 of 105 are done: research
      first (docs/10 *A thin source is a lead*), then extraction. Run
      `python -m pipeline.batch --source "OpenStreetMap plaques" --run`
      (~$10-20), and read the memories it makes before the next source.
- [ ] **Review what the new judge would drop.** (2026-10-04) `glad_to_know`
      only filters new extractions. `python -m pipeline.quality --visible`
      lists the visible memories it now drops; read the list, then
      `pipeline.review --reject` what should go.
- [ ] **Video quotes after the longer card.** (2026-10-04) The 60-180 word
      prompt kept video's keep rate but quotes fell 9 to 4 on 15 chunks
      (docs/04, *A longer card*). Try "leave the quoted line out of the
      summary: it is read right below" and measure with `quality --compare
      --source-type video --score --runs 3`.
- [ ] **Screen and trial the new sources.** (2026-10-04, blocked on credits)
      Ingested, all `candidate`: plaques 232 (105), filming 233 (39),
      Wikipedia 234 (15 windows), memoirs 235–243 (256 windows; Carl Møller's
      *Paa Farten* first). Follow `.claude/skills/find-sources`: `screen`,
      then a one-item trial each.
- [ ] **Ask Københavns Museum for its podcasts.** (2026-10-04) Four
      place-bound shows on Podbean, no transcripts, ©. Ask for permission
      and transcripts, as `docs/permission-request.md` asks a channel.
- [ ] **Enrichment, first live run.** (2026-10-04) `pipeline/enrich.py` is
      built and tested with fakes; the first live call hit an empty credit
      balance. Run `python -m pipeline.enrich --memory <id>` on five strong
      memories, read every item against its page, and record the cost per
      memory in docs/04 before a new source's trial relies on it.
- [ ] **Re-extract the paused books with the archival prompt.** (checked
      2026-10-04) Carl Møller, Oehlenschläger vol. I, Andersen and Leonora
      Christina are done (docs/04). Left: Oehlenschläger 206-208 and
      Liebenberg (210), if they earn it. The recipe: set `memories_extracted =
      false` for the source's content, delete the Redis keys `extraction:<id>`
      and `extraction:<id>:memories`, enqueue each, `pipeline.worker --burst
      --yes`, and read the worker's "Retellings hidden" lines.
- [ ] **Places that are still the model's guess.** (checked 2026-10-04)
      `python -m pipeline.repin --choose --apply` placed 7 of 58 visible `llm`
      places; the other 51 are mostly gone rather than misnamed (closed
      cinemas, factories, hospitals), which is a Wikidata or historical-map
      lookup, not a prompt fix. A "name it as the local map does" venue line
      was measured and not shipped (docs/04). Two decisions, one question:
      should a 1000 m `llm` pin be planned on a walk at all (25 places, among
      them 5615, Andersen on "the ramparts"), and should `is_gated`
      (`api/gate.py`) gate on `precision_meters` instead of
      `coordinate_is_unique` (docs/10, "The coordinates are
      mostly guesses")? The position is self-reported either way: it stops
      `curl`, not a spoofer.
- [ ] **40 labels by a person.** (checked 2026-10-05) The judge and
      `walk_score` are tuned on agent labels; `memory_reviews.reviewer` now
      tells them apart. Run `python -m pipeline.review --limit 40`, then
      `--accept` / `--reject` the ids with `--person` (without it a verdict is
      an agent's). Unblocks the few-shot item in Parked.
- [ ] **Then-vs-now: the points.** (checked 2026-10-04) `now.py` asks for
      named points within 25 m when no area matches; `--blank` confirmed 3 of
      29 before the public Overpass refused the rest (docs/04, *Corpus work*).
      2026-10-09: the mirrors (kumi, private.coffee, mail.ru) were down too,
      and a public rerun looked at 20 of 97 and confirmed 13 (written to the
      dev DB; some read oddly: "Still Field's, a parking"). Fix that holds: a self-hosted
      Overpass on the Denmark extract beside OSRM. Then check that the
      ranking reads better. Also check `now.py`'s `[!boundary][!place]`
      area filter: a hand query still returned boundaries.
- [ ] **Summary against its chunk.** (checked 2026-10-04) ~20 factual or
      speech-recognition errors: Tom "Christensen", Vestergade for
      Vimmelskaftet, lupus called cancer. Automatic fixes damaged walks and
      the first flag-only prompt flagged 77%. A verdict prompt that stores
      only contradictions is on branch `parked/unsupported-flags`, never run.
      Unmeasured and cheaper: have the extraction prompt spell known people as
      they are in print.
- [ ] **Judge v2 on the research rubric.** (checked 2026-10-04) Parked until
      grounding lands (docs/04, *Judge v2, measured and parked*). When it
      comes back, the three drop-gates (`private_person` within living memory,
      `promo`, `relative_time`) worked as worded; the bar of two of incident,
      breach and feeling cost 40% of the walks, so retune that. Measure with
      `quality --labels --half tune`, then `--half check` against v1's 32% /
      96%.
- [ ] **Rank, don't bar.** (checked 2026-10-04) A pairwise judge, both
      orders, over a video's candidates (later a neighbourhood's), in place of
      `worth_telling`'s absolute bar.
- [ ] **A video read whole: measured, not shipped.** (checked 2026-10-04) It
      kept a third fewer memories and lost a walk on both runs. Before trying
      again, draw today's chunked prompt twice on the same five videos, and
      try 15-minute chunks as the middle course.
- [ ] **The batched web research, first live run.** (2026-10-09) Built with
      fakes only (c7eff8d). On the next `batch --run`, check: the batch API
      accepts the web search/fetch tools with `cache_control` and effort (a
      rejected batch stops with "A batch stored no reply"); research replies
      cut on `pause_turn`/`max_tokens` (now resent, not used); "Still waiting
      after 12 passes" (a pick's picture list changing between passes);
      `pipeline.cost` against an earlier run, since searches aren't
      discounted. Links and the walk score in `after_save` still go at full
      price.
- [ ] **`published_at` is NULL for flat-crawled videos.** (checked
      2026-10-04) `api/gate.py` serves it as the source's year and newspapers
      fill it; yt-dlp flat extraction returns no timestamp. A real date needs
      a per-video fetch, paid only for videos that pass the filter, or the
      channel RSS feed (newest 15).

---

## Sources

The historical layer has sources now: Gutenberg and Runeberg books, KB
newspapers and Historisk Atlas, inside `LAUNCH_BBOX` (docs/10, *One launch
area*). Candidates, rejects and why: `python -m pipeline.sources list`. In
priority order.

- [ ] **Check the historical layer, then specify its flow.** (checked 2026-10-04)
      Standing anywhere in the launch area should return at least one
      historical card, the top one the highest-contrast rather than the
      nearest, and worth screenshotting. Measured 2026-10-09 (250 m grid,
      2,586 walkable cells): an archival memory within 1 km of 46%, within
      500 m of 24%; 91% within 4 km of Rådhuspladsen at 1 km. Empty ring:
      Avedøre, Kalvebod Fælled, Kastrup, Tårnby, Rødovre, Husum (95-100%),
      Hellerup, Hvidovre, Sydhavn, Amager Øst, Nordhavn, Emdrup (50-87%).
      ~300 covered cells' top card has no contrast score, so they fall back to
      the nearest. Sources for the ring first, or shrink `LAUNCH_BBOX`. The flow for it in docs/08,
      *Arrive somewhere and find its history*, is still only proposed, waiting on a source that has since been chosen: specify it
      from the product, not from whatever ingestion produced.
- [ ] **Three streets, counted by hand.** (checked 2026-10-04) In the launch
      area, count the *interesting* cards each source yields per street: would
      this make someone stop walking? The prediction: newspapers and the
      sabotage set win, directories are filler.
- [ ] **Email it@historiskatlas.dk for API access.** (checked 2026-10-04) The
      per-story licence ("Geo" in their API) is not on the public pages, and
      the sitemap source has title and intro only. 340 sabotage stories are
      ingested (dev DB), each a title and one line. Also a partial competitor:
      judge their neighbourhood-level content before building on it.
- [ ] **Email kbhbilleder@kff.kk.dk.** (checked 2026-10-04) 41,779 historical
      photos, maps and drawings, ~5,000 out of copyright and commercially
      usable, many geotagged. Bot-protected: ask, never scrape. Open source
      with a public APACS API (github.com/CopenhagenCityArchives). Unblocks *Then and now, lined up*.
- [ ] **More public-domain memoirs.** (checked 2026-10-04) Brandes' *Levned*
      I added 4 (source 231); volumes 2 and 3 are `runeberg:gblevned/2` and
      `/3`, queried as `Kjøbenhavn`. Heiberg's *Et Liv gjenoplevet* is
      `--source adl --query heibfr05val` (and `06val`, `07val`). Nexø has no free text;
      *Mit Livs Eventyr* retells source 202. Gutenberg's own search works when
      gutendex is down.
- [ ] **Open sources with coordinates.** (checked 2026-10-04) Wikidata (CC0)
      and Wikipedia (CC BY-SA): 4,321 items within 5 km of Rådhuspladsen,
      about famous people, not personal memories. OSM memorial plaques: 108 in
      the centre (ODbL). Both fit the text-source path in
      `crawler/sources.py`. Wikidata is already used for placement and the
      "since" year, not as a source.
- [ ] **Building history: FBB plus Wikidata.** (checked 2026-10-03) 1,029
      protection cases in København with real text (architect, dates, value)
      at `kulturarv.dk/fbb/sagvis.pub?sag=N`, terms allow use; email
      cfk@slks.dk once for commercial use. `sagvis.pub` answers "Systemfejl"
      outside a search session, so the crawler drives the search form first.
      Join Wikidata (P84 architect, P1435 heritage) for architect and date;
      `crawler/fbb.py` as a text source. Fund og Fortidsminder (bulk `FF.zip`)
      and BBR are enrichment; Stadsarkiv byggesager, kbhbilleder scraping and
      arkitekturbilleder.dk are no.
- [ ] **Decide on the local TV channels.** (checked 2026-09-29) All screened.
      The two active channels pass 0.85–1.00 at 6–31 memories an hour. NTV
      Nørrebro (144) passes 0.57 at 2.5/h, Bispebjerg Lokal-TV (146) 0.47 at
      1.3/h; Frederiksberg Lokal TV (159) 0.42 and Christianshavns Kvarter
      (155) 0.32, not trialled. Kgs. Enghave (176) waits on Whisper. Subject
      to the YouTube permission under *Launch*.
- [ ] **One-off videos.** (checked 2026-09-27) Andrew Schulz "Dropping In #20"
      (Copenhagen) and Ari Shaffir "You Be Trippin'" with Iain Stirling
      (Denmark): `ingest --video … --to <id>` under their channels.
- [ ] **Kraks Vejviser and older address directories.** (checked 2026-09-26)
      Pre-1900 editions at kb.dk carry a public domain mark; Copenhagen
      Libraries host digitised volumes. OCR'd scans, real extraction work.
      "What stood here" for nearly every address: filler between the
      interesting cards.
- [ ] **Now on a spot** (docs/10, *The recent past is a memory*; docs/04,
      *Now, 2026-10-02*). In order:
      1. **Film shoots from the KK permits.** Snapshot the `Filmoptagelse`
         permits weekly; once a shoot has happened it becomes a dated card at
         the address it names, attached to the story already there. Credit
         Open Data DK.
      2. **Seating permits, weekly.** A restaurant name new to the address is
         a candidate opening; check it against CVR's registration date
         (`distribution.virk.dk`) before it counts.
      3. **The "now" line for bars**, from the current seating permit:
         measure on the ~20 places `now.py` leaves blank.
      4. **Expiring cards, designed not built.** Street events ("until
         Sunday") and KK's `anlaegsprojekter` (226 projects, CC BY, "opens
         2029"). Open: `expires_at` from the permit's end date, a re-check
         job, the sheet label, and whether a walk may route to one. A planned
         project is a dated fact that expires, not a memory: a second card
         type or nothing. Every planned-building AR app died of staleness;
         Stockholm växer survives by carrying the city's own status label.
- [ ] **Sources that need their own plan.** (checked 2026-09-27) Walk-and-talk
      recording (Whisper plus the GPS track; a product feature, not a source);
      podcasts (RSS plus local Whisper, never DR); Politiets Registerblade
      1890–1923 (filler); film locations (DFI, fan lists); "Were you ever
      here?" at a thin spot, opening the submit sheet.
- **Excluded:** arkiv.dk (private use only, no API) and setlist.fm
  (non-commercial API; commercial means Live Nation). Revisit only with a
  licence.

---

## The app

Home is a map of the locked memories around you, faded (docs/10, *A map
before the planner*); the planner plans one walk and only its stops open. The
rule for anything game-like or crafted: quiet by default, loud only for real
progress; refine what exists rather than add.

### The walk on the map

- [ ] **A direction arrow on the user dot.** (checked 2026-10-04)
      react-native-maps 1.29.8 has `followsUserLocation` but no heading prop.
      Look on a real phone whether MapKit's dot draws the heading beam with
      `showsUserLocation` (`mobile/App.tsx`). Only if not:
      `Location.watchHeadingAsync` and a custom marker. See *On a real phone*.
- [ ] **A long walk still falls short where the map runs out.** (checked
      2026-10-04) The lakes top out at 7.4 km for any stop count: shortest
      legs cross the bridges. The preview says "The longest from here." Left:
      legs routed longer than the shortest path (round the shore), if an
      honest short walk isn't enough. 10 km plans were p95 1.5 s, mostly the
      spur cleanup re-solving once per stop; retracing fell 21% → 13% with
      0e136e2. Speed bought with spurs is a founder's call: measure with
      `route_bench`.
- [ ] **Generated themed routes, reviewed before publishing.** (checked
      2026-10-04) An offline job: for each hotspot cluster × each tag, solve
      from the centroid, write `status='draft'`, accept or reject in the style
      of `pipeline/review.py`. `routes` went in 044 for want of a writer, so
      this brings the table back with its first draft. Waits on one area with ≥3 tags of ≥5 walkable
      stops: `python -m pipeline.themed_routes` says which. None yet outside
      the dev seed.

### A reason to finish the walk

- [ ] **"What to look at when you're there" on a stop.** (checked
      2026-10-04) A pointer to the spot ("the corner doorway, the green
      tiles"), never a line of the story; it also helps when GPS wobbles near
      20 m (Smith et al. 2019; Riot! 1831). Tried from the summary alone
      (docs/04, *What to look at*): about 6 of 40 real, 14 invented at places
      that are gone. Next: only where OSM confirms the place still stands,
      given OSM and Wikidata's description of the building instead of the
      story. A new extracted field: measure before and after.
- [ ] **The streak: a sound, and a rest day or a repair.** (checked
      2026-10-04) The 7/30/100 moment has a flame and a haptic (`Milestone` in
      `src/Plan.tsx`), no sound; a chime needs a bundled asset and an audio
      session set to mix, or it stops the walker's podcast. A missed day
      punishes: a rest day or a repair (broken streaks hurt less when they
      can be repaired, Silverman & Barasch 2023; Duolingo's second freeze
      lifted DAU 0.38%). The founder turned down a streak shield as a reward,
      so ask first. Watch for streak anxiety.
- [ ] **A today card in the journal.** (checked 2026-10-04) First in Walks, like Pikmin
      Bloom's Lifelog: today's trace on a mini map, steps, and a week strip
      with a dot for each day walked. Maybe later: brighten the streets you
      have walked (Fog of World, Wandrer), never hiding content.
- [ ] **A Lock Screen widget** (`expo-widgets`). (checked 2026-10-04)
      Today's walk or the nearest stop, and the streak. After launch; skip
      Live Activities.
- [ ] **Hear the story at its spot.** (checked 2026-10-04) A paragraph read
      on a street corner is the wrong format for somebody walking, and the
      sources are already recordings with an offset (docs/10, *An offset
      only exists when the source is a recording*). At the unlock, offer the
      clip from that second, for earbuds, beside the text. DR clips wait on
      *Licensing before money*; start with sources clearly ours or
      linkable. Prototype one stop before building it.

### Craft

- [ ] **Then and now, lined up.** (blocked 2026-10-03: no memory has an
      image; needs kbhbilleder access) The viewfinder in Add (docs/10, *The camera is a
      block*) ghosts an archival photo over itself at ~40% so the walker can match it. Open: where the
      "now" photo goes. Founder's call.
- [ ] **The seal starts with a cut.** (2026-10-09) The seal page cuts
      straight to a full-size open locket over the map, its lid large and
      partly off the left edge: the unlock played backwards, probably
      intended, but no transition. Founder's eye. Nothing guards the drop if
      the user's dot is off-screen.
- [ ] **Hand-drawn illustrations.** (checked 2026-10-03) The app has
      none. Places that want one: the empty walk list, sign-in, the paywall,
      the finish card. Commission one base style (`ILLUSTRATOR`), derive the
      rest. Bar: nobody asks which prompt made it.

### On a real phone

- [ ] **Things only a device can check.** (checked 2026-10-04) The simulator
      has no compass, pedometer or real GPS:
      - The direction arrow: does MapKit's dot draw the heading beam?
      - The nearby-memory notification with the phone locked and the app killed (`walk-and-unlock.yml`'s F28
        covers only the background).
      - Steps: grant Motion & Fitness, walk, reopen, see the journal's count
        rise once; deny it and walks still plan and open. Nothing has ever
        counted a real step. Unverified: whether Core Motion misses steps only
        a Watch counted.
      - The camera in Add: a real viewfinder, Take, the upload. The
        simulator's shot is a generated picture.
      - The route drawing itself and the locket unlock: frames were measured in the
        simulator only.
      - The seal's first-memory line over a dense map (the simulator's was
        sparse).
      - A mystery stop (docs/10, *A mystery stop*) appearing as you near it;
        e2e starts are random and the run so far had none.

---

## Money beyond the subscription

One walk a week is free (docs/10, *A free walk a week*); Memory Lane+ buys a walk every day and Customize
(themes and an era; docs/10, *A walk planner, nothing else* and
*Subscribers shape the walk*). Nothing else is sold. Every price is borrowed
from a neighbouring kind of app; tune on real data. The sources behind each
line are in this file at `9421fb0`, *Map, walk and money*. Anything a walk
earns stays unsold (Apple 3.1.1, the loot-box rulings). The founder turned
down, as rewards: keeping a previewed memory for the next walk, a streak
shield, and an extra walk. A surprise open off a walk is now free, once a
week, by timer (docs/10, *A surprise, once a week*), and the streak's rest
day is a rule, not a shield (*A rest day in the streak*).

- [ ] **Licensing before money (your decision).** (checked 2026-10-03) Blocks any paid
      open of a DR-derived story. DR sells archive clips at about 80 DKK a
      second (Folketing KUU bilag 39 and spm 91, unverified: both 403'd); the
      free DR archive at KB is private streaming only and excludes AI use.
      Linking is lawful (Svensson), framing round access restrictions is not.
      Safe default: charge for the walk and curation, never a DR clip; if it
      stays open, paid walks plan only sources clearly ours (Gutenberg, user
      posts, licensed). Add to the lawyer's read.
- [ ] **The price.** (checked 2026-10-03) 49 DKK a month or 349 DKK a
      year. Western Europe medians: $8.99 a month, $39.44 a year (RevenueCat
      report). Push annual: 44.1% retained after a year against 17.0% monthly.
      Plan for the subscription to carry ~80% of revenue.
- [ ] **A pass for visitors.** (checked 2026-10-04) A visitor fits "a walk
      a day" exactly and rarely subscribes for a three-day trip. A 1- or
      3-day pass, non-renewing, through RevenueCat beside the subscription.
      Price it against the entry above and StoryHunt (11 walks at 99 DKK).
- [ ] **Pitch commissioned walks to the city.** (checked 2026-10-02)
      Probably year one's biggest line, guessed 50–300K DKK. Budget 2024 set
      aside 2.1M DKK for "The Copenhagen App"; the city leads a 35M DKK EU
      tourism project with Wonderful Copenhagen, Nationalmuseet, Københavns
      Museum and StoryHunt, the incumbent (8 free walks, 11 at 99 DKK). The
      city pays for free walks that spread tourists out. A sales
      conversation, not code.
- [ ] **Premium walks on GetYourGuide / TripAdvisor.** (checked
      2026-10-02) Questo's model, revenue share (agencies 20–25%, stores 15%).
      Only on public-domain or licensed sources (see licensing above). Guessed 20–150K DKK.
- [ ] **Later: sponsored stops.** (checked 2026-10-02) Works only at
      McDonald's-scale footfall; small cafés churn. Revisit after real
      traffic, and label it if built. Not doing: walk-to-earn with a brand
      marketplace (near nothing below ~1M users).
- [ ] **Benchmarks for the business case.** (checked 2026-10-02) Download
      to paid: 2.0% median (freemium 2.1%). Revenue per install at D60:
      Health & Fitness $0.66. Ceiling: Pikmin Bloom, $100M lifetime from
      passes and events, never access.
- [ ] **Running out of stories: the first retention metric.** (checked
      2026-10-02) Detour never got traction (3–4 months a tour), Field Trip
      shut, Pokémon GO lost most of its daily users within months; the
      survivors (VoiceMap, izi.TRAVEL) scaled on creators' content. Once
      someone has walked the stories near them, nothing brings them back but
      corpus density and submissions. Track it.

---

## Embed

- [ ] **Map tiles of our own, before the embed is public.** (checked 2026-10-04)
      `TILE_URL` in `api/embed.py` is OSM's public tiles, which OSMF policy
      forbids for this. Stadia Maps (one URL + a key) or Protomaps/PMTiles
      (~$3/mo on R2), per `docs/09-visual-design.md`. **Blocks deploying the
      embed anywhere public.**
- [ ] **Per-customer `CORS_ORIGINS` and a per-embed key.** (checked
      2026-09-20) Blocked on `DEPLOY`. The first thing with a customer
      attached, so the first that needs a usage bound.

---

## Parked

Each waits on something named; none is worth building before it.

- [ ] **The first four cities.** (checked 2026-10-07) Waits on Copenhagen
      at full coverage (docs/10, *Thirty good in every kilometre near the
      centre*) and two measured numbers: the city's share using the app each
      month and the share of those who pay. Target ~10k €
      net a month ≈ 18k € pre-tax ≈ 19.5k € a month paid out by the stores
      (prices include VAT; then the stores keep 15%). That is ~4,400 payers
      at 49 DKK a month, ~7,400 on the year. At a guessed 1% of a city using it monthly and 3% of those
      paying, ~300 payers per million people: ~18 Copenhagens. Pick by
      walk-testable from Copenhagen, a language we can judge, free sources,
      tourists.
      1. **Copenhagen.** Finish and measure; nothing else ships first. Watch
         whether visitors or locals pay (*A pass for visitors*): visitors
         paying moves London up.
      2. **Stockholm.** A cheap replication: can we make a good city without
         living in it? One trip to walk-test. Ask what the next city costs in
         days, not credits.
      3. **London, one district** (the City or Southwark), not all of it. The
         first city that could pay: the largest English source pool, tourists,
         a short flight.
      4. **Edinburgh.** Compact, walkable old town, heavy tourism, and it
         reuses London's English-language source work. Amsterdam if London
         showed English sources were not what carried it.
      Copenhagen-only today: `LAUNCH_BBOX` (`pipeline/config.py`), the Danish
      phrases and neighbourhoods in `pipeline/sources.py`, `--area` in
      `pipeline/neighbourhoods.py`, and the extraction prompt's examples.
      Make each one a per-city setting when city 2 starts, not before.

- [ ] **Retrieve few-shot examples instead of hard-coding three.** (checked
      2026-10-04) Waits on ~50 person-reviewed rows (*40 labels by a person*).
- [ ] **Revealed-preference report.** (checked 2026-09-23) A `quality.py
      --signals` view: do the regex flags predict hearts and reports? Waits on
      hearts and reports from real people.
- [ ] **Incremental channel re-crawl, tiered.** (checked 2026-09-23) Waits on
      several channels and a scheduled ingest. Stopping at the first known id
      would break backfilling by dropping `limit`.
- [ ] **Rate limiting on the API.** (checked 2026-09-24) None exists;
      `CORS_ORIGINS` and `REPORT_THRESHOLD` are the only abuse controls. Waits
      on a public launch.
- [ ] **Revisit RevenueCat when its fee outgrows two integrations.**
      (checked 2026-10-03) Free
      under $2.5k/month, then 1% of gross. Leaving changes only
      `billing.fetch_subscriber` and the app's SDK; `subscriptions` stays
      ours.
- [ ] **Steps on Android.** (checked 2026-09-30) Steps are a journal stat that
      buys nothing, so this waits on wanting it. `react-native-health-connect`
      v4, `READ_STEPS`, 30 days back, `dataOriginFilter` on the phone's own
      origin. Play needs the Health Connect and Health apps declarations and
      an in-app rationale screen. Store disclosure for steps on both: Fitness,
      linked to you, app functionality, not tracking.
- [ ] **More themes.** (checked 2026-10-04) Themes lean a subscriber's walk
      on the extractor's tags (`THEMES` in `Plan.tsx`, `_shaped` in
      `api/read.py`). Architecture needs a new tag and re-tagging (credits).
      Friends-only needs a friend graph: `layer='friend'` has no writer. A
      walk that tells one story (one era, person or source) is the richer
      version.
- [ ] **Four off-vocabulary tags.** (checked 2026-10-04) `entertainment`,
      `celebrity`, `theater`, `festival` (15 rows) predate the filter;
      `tags.clean()` drops them on write but nothing remaps the old rows. Map
      them if a theme ever needs them.
- [ ] **A map that carries the brand.** (checked 2026-10-11) Waits on
      wanting the map itself on-brand (paper tones, Gloock street names);
      muted Apple Maps is the default developers back for a story-walk app.
      Apple Maps' ceiling: map types, dark mode, points of interest, tint. No
      colours, fonts or label control, and only raster tiles
      (`UrlTile shouldReplaceMapContent`). Cheap step first: a translucent
      world `Polygon` as a paper wash. If that falls short:
      1. **Spike for a day** in a worktree: the walk screen on
         `@maplibre/maplibre-react-native` (v11, New Architecture only, one
         maintainer, needs a dev build). Judge it on a real phone: fling,
         pinch and label feel are what migrations lose, not features.
      2. **Tiles:** a Protomaps PMTiles extract on Cloudflare R2 ($0-12 a
         month). MapTiler's and Stadia's free tiers are non-commercial;
         OpenFreeMap is one person with no SLA, so use it for the spike only.
      3. **The port is a rewrite of the map screen**, about 3-5 days. It
         touches `App.tsx` (the `MapView` and its camera calls),
         `MemoryMarker.tsx`, `RouteLine.tsx` and `useMapCamera.ts`. The
         camera is the hard part: MapLibre's is declarative and zoom-based,
         not region-based. The ring becomes a GeoJSON polygon.
         `patches/react-native-maps+1.29.8.patch` goes, because `belowLayerID`
         and `line-trim-offset` are built in.
      4. **Costs on top:** glyph PBFs for Gloock (MapLibre Native can't use
         local fonts), a dark style to maintain, VoiceOver that MapKit gave
         for free, and a tile host in the privacy policy.
      No adapter layer in the meantime. Map wrappers leak at the camera
      (Mapstraction, react-native-maps' own providers); keeping map code in
      those four files is the portability that pays. Teardown: Komoot,
      Bikemap and Felt run MapLibre on their own tiles; Zenly and Pedometer++
      left MapKit for creative control; Wikipedia iOS stayed for
      accessibility.

---

## Blocked on you

They cost money, need an account, or need a person. Full detail in
`loop/STATE.md`.

- [ ] **`API_CREDITS`** (checked 2026-10-04) Funded 2026-09-27; the books, the
      sabotage stories and the comparisons (`quality --compare`,
      `classifier_audit --against`, `quality --places`) have run. **There is
      no `--limit` flag**: `python -m pipeline.extract` bills every pending
      video. To spend cents: `python -m pipeline.enqueue --video <id>`, then
      `--status <id>`. Left: the pending episodes; the 22 clips extracted
      before the video filter, which probably duplicate their episodes'
      memories (`review` or `dedup`); content 160 (Blaagaardsgade) to see a
      geocoded place; and measuring the `address` and `country` prompt fields
      (`pipeline.quality` before and after). KB papers: `pwa` sits near 50 on
      every 1856 page, so expect ad-page noise.
- [ ] **`STADSARKIV_ERINDRINGER`** (checked 2026-09-27) The best Copenhagen
      source: 3,322 written memories at street level, 1,516 transcribed, from
      about 1890. The writers keep copyright; the only machine access is the
      archive's undocumented Solr search. Ask the archive (Eva Greve
      Mortensen) for written permission to summarise them first. Strip the
      writers' addresses and phone numbers.
- [ ] **`DEPLOY`** (checked 2026-09-20) Railway, ~$5/mo. Not Fly: its managed
      Postgres has no PostGIS. Unblocks the waitlist, the webhook, the embed
      and an OSRM sidecar (~1.6 GB RAM to build).
- [ ] **`EAS_BUILD`** (checked 2026-09-20) Three `PLACEHOLDER` tripwires to
      replace first; the bundle id is irreversible once submitted. Sign-in
      needs this too: neither button works in Expo Go, and
      `GOOGLE_CLIENT_IDS` / `APPLE_CLIENT_IDS` need real client ids.
- [ ] **`COMPANY`** (checked 2026-10-07) Swedish, since you live there
      and run it from there: a company is taxed where it is managed, so a
      Danish ApS run from Sweden risks both countries. Enskild firma now
      (periodiseringsfond, expansionsfond at 20.6%), or an AB (25k SEK) for
      limited liability from day one; a holding AB on top once profit
      outgrows spending (dividends and a sale tax-free inside it). 3:12 after
      the 2026 reform: ~320k SEK a year of dividends at ~20%, more taxed as
      salary. Before registering: an hour with an accountant who knows
      Øresund commuting, and Monta's contract for side-business and IP
      clauses; don't make Monta's office the place the app is run from.
      Before `STORE_ACCOUNT`: an organisation developer account needs the
      legal entity and a D-U-N-S number, or the store shows your own name
      as the seller. Cyprus (15% corporate, 0% dividends as non-dom) only
      if you really move, once profit passes ~29k € a year and the app no
      longer needs you in Copenhagen. Figures from memory, verify them.
- [ ] **`STORE_ACCOUNT`** (checked 2026-09-20) Apple $99/yr, Play $25. A
      personal Play account gates production behind **closed testing with 12
      testers for 14 continuous days**: start it the day EAS produces an
      `.aab`. The nearby-memory notification's background location needs the privacy disclosures
      updated and a real device confirming delivery.
- [ ] **`ILLUSTRATOR`** (checked 2026-10-03) An artist for the illustrations'
      base style, a few hundred. And decide where a "now" photo goes.

---

## Open questions

- **A floor on `walk_score`?** (checked 2026-10-03) Ranking by it moved
  planned stops only slightly (docs/10, *A walk picks its stops by the
  rubric*). Leaving 3 or less off walks would drop 22 labelled skips and 2
  walks. A bar, which the research argues against; the founder's call.
- **Does the podcast corpus eventually get pruned?** (checked 2026-09-20) It is
  US comedy anecdote in a product about Copenhagen history.
- **Sign in at the first unlock, not at launch?** (checked 2026-10-04) The
  wall comes before anything is shown, and "your collection follows you"
  holds only once there is one. App Review 5.1.1(v) allows sign-in where an
  account feature needs it. Supersedes *Sign-in comes first, and it is the
  whole onboarding* if taken; the founder's call.
