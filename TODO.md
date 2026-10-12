# Memory Lane — TODO

This file is the source of truth for open work. `loop/TASKS.yaml` is the
executable contract the `/ml-tick` loop runs against; it gets repopulated from
whichever phase here is active. If the two disagree, this file wins and
TASKS.yaml is wrong.

**Open work only.** A finished entry is deleted, not ticked: `git log -p
TODO.md` keeps its history, and a decision it carried goes to
`docs/10-decisions.md` first. Everything done before 2026-09-24 is in the
history of this file at `c4703b4`; the long research behind the money, walk and
source entries, before this file was consolidated, is at `9421fb0`. Entries
that didn't move launch, coverage or retention were cut on 2026-10-12; they
are at `a3a85ef`.

**Every entry says when it was last checked** against the code, as
`checked YYYY-MM-DD`. More than a few days old means verify before acting on
it: a stale entry once sent a session to rebuild search, which had shipped a
week earlier.

**Next batch** (asked for as "pick the next batch of todos"): The app › One
look, run with the prompt there. Delete this line once that section is done.

---

## Friction

What slowed a session down or nearly shipped something wrong, and would again.
The rules for adding to it are in AGENTS.md, "Then log the friction". Newest first;
delete an entry when its fix lands.

- **The Figma MCP stops after a handful of calls.** 2026-10-12: the personal
  team is on Starter, which caps MCP calls a month, and the Monta seat is
  Collab, which can't edit. A redesign session made the file and then got no
  further. Mockups came out as HTML rendered by headless Chrome instead
  (`~/Downloads/memory-lane-redesign/board.html`). Fix: a Professional seat on
  the personal team, or start design work from HTML and skip Figma.

- **The source screen fails biographies that hold a spot scene.** 2026-10-10:
  Haiku's screen scored Kirstine Meyer's Ørsted essays 0.00 and 0.25, rejecting
  the 1820 Nørregade discovery window as "not personal experiences"; the
  screen's 0.3 bar would have dropped it. `CLASSIFIER_PROMPT` in
  `pipeline/tasks.py` already says "first-hand or as history" (616d507), and
  Haiku still failed it. Fix: a biography line among its QUALIFY examples
  ("In 1820, in his rooms on Nørregade, Ørsted saw the needle move"), measured
  with `classifier_audit` (cents, so run with `!`).

- **A chrome change costs the whole e2e suite.** 2026-10-12: the map's dock
  changed the buttons every flow taps through `steps/launch.yml`, so the
  only honest check was all three flows, about 7 minutes with the editor
  blocked (Metro serves the run). Consolidating again won't fix it: they went
  six to three on 2026-10-07, and the time is the per-flow database rebuild,
  the cold start and the walked legs. Fix: a `smoke.yml` (launch, then tap
  Plan a walk, Journal, Add and Locate and back, about a minute), run
  first and alone for chrome changes; the full suite before a release.

- **No e2e flow screenshots the locket.** 2026-10-10: porting the unlock
  engine, walk-and-unlock passed green with nothing showing the lid had drawn
  or swung. It took a hand loop of `simctl io screenshot` and contact sheets
  to see it. 2026-10-12: a `takeScreenshot` after the press lands on the open
  memory, since `longPressOn` and the slide's `swipe` block past the unlock.
  Fix: a background `simctl io screenshot` loop in `steps/unlock-stop.yml`
  (`runScript`), or a dev knob that holds the locket open on screen.

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
      - The listing: lead with the story cards, captured from the e2e flows;
        title, subtitle and keywords in Danish and English. Give it 3–4 days:
        Apple boosts a new app once, in its first week or two.
      - Then on a real device: buy monthly, see the row, plan a second walk
        the same day, cancel in the sandbox, see it lapse. Nothing has ever
        called RevenueCat for real: the tests patch `billing.fetch_subscriber`.
- [ ] **Rate limiting on the API.** (checked 2026-09-24) None exists;
      `CORS_ORIGINS` and `REPORT_THRESHOLD` are the only abuse controls.
      Needed before the public launch.
- [ ] **The launch bar, then launch day.** (checked 2026-10-04) Launch when
      the closed-testing cohort comes back for days (`python -m api.metrics`);
      people gone after a day means not yet. Then email the waitlist; post in
      r/copenhagen, Danish local-history groups and press, and Product Hunt.
      Start a week ahead so it lands inside Apple's boost.

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
      The batched web research (c7eff8d) has run on fakes only: on the first
      `batch --run`, check the batch API takes the web tools with
      `cache_control` and effort (a rejection stops with "A batch stored no
      reply"), and compare `pipeline.cost` with an earlier run.
- [ ] **Human labels, then let them decide.** (2026-10-05) Every judge and
      prompt number so far is against `walk_labels.json`, which an agent
      made, and the judge, fact-check and trim run on the extractor's own
      model. The founder labels ~100 memories: `python -m pipeline.review
      --limit 40` at a time, then `--accept` / `--reject` the ids with
      `--person` (without it a verdict is an agent's). Then, in order:
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
- [ ] **The rest of the plaques.** (2026-10-04) 18 of 105 are done: research
      first (docs/10 *A thin source is a lead*), then extraction. Run
      `python -m pipeline.batch --source "OpenStreetMap plaques" --run`
      (~$10-20), and read the memories it makes before the next source.
- [ ] **Screen and trial the new sources.** (2026-10-04, blocked on credits)
      Ingested, all `candidate`: plaques 232 (105), filming 233 (39),
      Wikipedia 234 (15 windows), memoirs 235–243 (256 windows; Carl Møller's
      *Paa Farten* first). Follow `.claude/skills/find-sources`: `screen`,
      then a one-item trial each.

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
- [ ] **Email it@historiskatlas.dk for API access.** (checked 2026-10-12) Drafted
      in `docs/permission-request.md`; send it. The
      per-story licence ("Geo" in their API) is not on the public pages, and
      the sitemap source has title and intro only. 340 sabotage stories are
      ingested (dev DB), each a title and one line. Also a partial competitor:
      judge their neighbourhood-level content before building on it.
- [ ] **Email kbhbilleder@kff.kk.dk.** (checked 2026-10-12) Drafted in
      `docs/permission-request.md`; send it. 41,779 historical
      photos, maps and drawings, ~5,000 out of copyright and commercially
      usable, many geotagged. Bot-protected: ask, never scrape. Open source
      with a public APACS API (github.com/CopenhagenCityArchives). Picture memories.
- [ ] **More public-domain memoirs.** (checked 2026-10-12) Ingested, none
      extracted: Brandes' *Levned* II (242) and III (243), Heiberg's *Et Liv
      gjenoplevet* 1-3 (382-384; 383 and 384 still `candidate`). Brandes I
      (231) gave 4. Next, billed: `python -m pipeline.batch --source "<name>"
      --run` for each, then read what it made. Nexø has no free text.
- **Excluded:** arkiv.dk (private use only, no API) and setlist.fm
  (non-commercial API; commercial means Live Nation). Revisit only with a
  licence.

---

## The app

Home is a map of the locked memories around you, faded (docs/10, *A map
before the planner*); the planner plans one walk and only its stops open. The
rule for anything game-like or crafted: quiet by default, loud only for real
progress; refine what exists rather than add.

### One look (2026-10-12: built without Figma; tomorrow, the Figma pass)

Built in the app on 2026-10-12, with Figma's MCP capped (docs/10, *Dusk, and
the map's dock*): the Dusk palette, the dock, the compass-rose emblem and the
drawn icons. The comparison shots are re-made by `mobile/scripts/shoot.sh map
preview collector journal`.

The prompt for tomorrow: "Figma has reset. Using the Figma MCP: take the
shipped Dusk screens (map with the dock, planner, Collector, journal) as
references, draw the same four as one frame, then push them: a calmer dock,
the rose, the six icons as one family. Screenshot and show me beside the app's
shots. What wins in Figma changes values in theme.ts and the SVGs, not
meanings; run the gate and shoot the touched screens."

- [x] **Palette.** Three loud candidates, then three muted ones from the
      founder's Pinterest board; Dusk chosen. theme.ts, api/card.py, link.ts,
      app.json's splash and primaryColor, UI.md › Tokens, docs/09 part 16,
      docs/10.
- [x] **The map dock** (`MapDock.tsx`). Not yet run: the e2e flows that tap
      Journal, Add and Plan a walk on home (labels kept).
- [x] **A Plan-a-walk emblem**: the compass rose, swings 0.9 s.
- [x] **One icon family** (`Icon.tsx`): ink line over a cream tone, every
      button over the map, walk and planner; go is now the HUD's charcoal.
- [ ] **In Figma, push it further** (the prompt above). Open: the raised
      button sits third of four, off centre; `app.json`'s `#A8350F`
      adaptive-icon orange waits on the icon art itself.
- [ ] **A walk cycle for Plan a walk** (2026-10-13, Figma). The dock's
      button is your Collector's still art, bobbed and slid out of its ring
      on a tap. Make it walk for real: a side-view cycle of each class (4–6
      frames, same image tool and care as the eight stages, one stage at a
      time), played on a tap in `PlanWalkButton.tsx`. Hand-drawn SVG walkers
      were tried 2026-10-12 and rejected: the art has to be the classes'.
- [ ] **(Later) the character floating over the map** with its bar under it.
      Not chosen now. If it comes back: a pre-rendered idle loop, no 3D engine.

### The Collector

You pick one of four wizard classes and it grows through eight looks as your
lockets (memories opened) climb (`mobile/src/collector.ts`). It replaced XP
and levels (docs/10, *The Collector*). Nothing is spent or sold, and nothing
ever covers a memory.

- [ ] **Test it with walkers before the real art.** (checked 2026-10-11) The
      Locket-keeper lesson: four game layers were reversed in eight days
      without a user. Print the four classes, each with its eight stages, and
      show five people after a walk. Do they pick one quickly, and do they ask
      what comes next? Does needing their own memories to grow read as a push
      or a wall? Fantasy Hike's 708 reviews never asked for gear
      (`docs/research-fantasy-hike.md`), so this is the founder's pull until
      walkers show it is theirs too. Then measure: D30, walks and memories
      filed per walker, before and after the Collector (2026-10-12), and how
      many filed ones get hidden.
- [ ] **The art: 4 classes × 8 stages, one stage at a time.** (checked
      2026-10-11) The Canva lineups were bad: eight figures in one image drift
      and blur. In Figma (GPT image), start from the sheet's front view as stage
      4 (`~/Downloads/memory-lane-mascot/wizards/` 01, 08, 19, 09), then make each
      stage as an edit of the one before, up to 8 and down to 1. Each class's
      ranks and its locket line are in `collector.ts` and the memory notes.
      Then: transparent backgrounds, a check that it reads in dark mode, and a
      check at 44 pt (does each stage still look different at journal size?).
      Files replace the placeholders in `mobile/assets/collector/<class>-<stage>.png`
      (today every stage is the sheet's front view, cut by hand); nothing
      else changes. The rank-up and the ladder (2026-10-12) are built
      for gear: each stage should visibly add something (hood trim, a staff,
      a lantern, a robe colour), or the rank-up springs a wizard into itself.
      The placeholders' white fringe shows on the dark plate.

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
shield (the streak is gone: docs/10, *No streak*), and an extra walk. A surprise open off a walk is now free, once a
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
- [ ] **Pitch commissioned walks to the city.** (checked 2026-10-02)
      Probably year one's biggest line, guessed 50–300K DKK. Budget 2024 set
      aside 2.1M DKK for "The Copenhagen App"; the city leads a 35M DKK EU
      tourism project with Wonderful Copenhagen, Nationalmuseet, Københavns
      Museum and StoryHunt, the incumbent (8 free walks, 11 at 99 DKK). The
      city pays for free walks that spread tourists out. A sales
      conversation, not code.

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
         whether visitors or locals pay: visitors
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
      Postgres has no PostGIS. Unblocks the waitlist, the webhook and an OSRM
      sidecar (~1.6 GB RAM to build).
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

---

## Open questions

- **Sign in at the first unlock, not at launch?** (checked 2026-10-04) The
  wall comes before anything is shown, and "your collection follows you"
  holds only once there is one. App Review 5.1.1(v) allows sign-in where an
  account feature needs it. Supersedes *Sign-in comes first, and it is the
  whole onboarding* if taken; the founder's call.
