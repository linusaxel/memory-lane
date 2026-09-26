# LOOP STATE — TERMINAL. Every TASKS.yaml task is `done` or `blocked` on a
# human gate, and TODO.md's founder-brainstorm list has no buildable item left.

```
updated:  2026-09-23 (t38, TERMINATE)
branch:   loop/autopilot   — NOT pushed. `main` is behind by this whole session.
gate:     GREEN, 568 pytest + 69 node tests, commit be67e45.
status:   TASKS.yaml: 49 done, 10 blocked (all NEEDS_DECISION / a named human
          gate), 0 todo, 0 doing, inbox empty. TODO.md's "Ideas — founder
          brainstorm, unvetted" section: every remaining line is either [x]
          done, a Resolved note that says no build is implied, or an explicit
          pointer at one of the same NEEDS_DECISION items below. There is
          nothing left for the loop to build without a human decision, an
          account, a device, or a card number.
```

**`TODO.md` is the roadmap and the source of truth.** This file is the loop's
orientation doc and does not compete with it. Where they disagree, TODO.md
wins and this file is stale.

## Why this is the stopping point, not another pause

STEP 2 of the loop's own procedure says: pick the first `todo`, or the first
`doing`; skip every `blocked` task unconditionally; if nothing is left that is
`todo` or `doing`, go to STEP 6 (terminate). That condition is met, and has
been re-verified twice in this session after a false alarm (see "Do not
redo" below) — this is not a guess.

## What this whole session added (chronological, oldest first)

TASKS.yaml's own backlog (t0–t29, 2026-09-20 to 21): full crawler → ingest →
transcripts → extraction → API → mobile app → store config pipeline; the
layer/contrast/tag system; proximity unlock; submissions with photo and
audio; sign-in; anniversaries; the daily route; the embed and
card. See `loop/JOURNAL.md` t0–t29 for the one-line-per-tick record, or prior
`STATE.md` revisions in git history for longer summaries.

TODO.md's untracked founder-brainstorm list (t30–t38, 2026-09-22 to 23), once
TASKS.yaml ran dry:

| Commit | What |
|---|---|
| `27ddff9` | Static logo mark |
| `caba568` | Animated startup logo |
| `6584fdb` | Tab bar delimiters |
| `1daec1e` | Start-route affordance |
| `a0b5caa` | Route-complete moment (haptic) |
| `e52e956` | Configurable route distance (`GET /v1/routes/today?radius_meters=`) |
| `eb6060b` | Heart/favorite a memory |
| `d316427` | Streak counter (F27) — computed from `unlocks`, not stored |
| `f6f8a7b` | Proximity notification (F28) — opt-in background geofencing over today's route |
| `be67e45` | Warm accent — `seal` moved from stamp red to a warm ochre |

Full detail on any of these is in `loop/JOURNAL.md`'s per-tick lines or the
commit itself; no need to re-derive it by reading code.

## What works right now

```bash
docker compose up -d --build              # API + PostGIS + Redis
curl -fsS localhost:8080/v1/stats         # the API is up and has data
./loop/verify.sh                          # 568 pytest + 69 node tests, GREEN
python -m pipeline.seed_dev               # memories you can actually reach
cd mobile && npx expo start               # the app
```

## The complete human checklist

Nothing below can be advanced by the loop — each needs a decision only a
human can make, an account the loop may not open, a card the loop may not
hold, a device the loop cannot touch, or a person physically walking
somewhere. Ordered roughly by dependency, not by task id.

**Decisions (free — no money, no account, just a call to make):**

| Task | What to decide |
|---|---|
| `W4-00` | Which historical source first: arkiv.dk (no API, scraping, unclear reuse terms), Mediestream, or setlist.fm (documented REST API, dense Copenhagen coverage, ranked third in the brief but the strongest contrast material available). Recorded in `TODO.md` → Open questions. |
| `D-05` | Depends on `W4-00`. Once the source is picked, write F3 ("arrive somewhere and find its history") against real data instead of the fixture. |
| `W4-02` | Semantic place dedup: have extraction emit structured venue/locality/region fields (a prompt + schema change, `W4-04`), or accept a human review pass over the 25 proposed merges `pipeline/dedup.py --apply` has not yet run. Measured ~1/3 wrong on naive heuristics; a bad merge destroys memories and is invisible afterward. |
| `P4-01` | Stranger-note decay conflicts with 3.2's promise that a filed memory is permanent and stays in its author's collection. Three ways out in the task's own note: decay only the unwritten `friend` layer (YAGNI today), a separate non-memory `note` entity that decays, or declare 4.1/4.2 superseded by 3.2 and delete them. |

**Money and accounts:**

| Task | Gate | What to do |
|---|---|---|
| `W1-09` | API_CREDITS | Run one video through the queue path (`python -m pipeline.enqueue --video <id>` then `pipeline.worker --burst`), then eyeball 20 summaries for quality. Nothing else can validate extraction quality — `tests/fakes.py::FakeAnthropic` proves the plumbing, not the prose. |
| `W2-08` | DEPLOY | Railway account + card, new project, PostGIS service, `psql $DATABASE_URL -f db/schema.sql`, deploy this repo's Dockerfile, load data, note the HTTPS domain. Full steps in the task's own note. Unblocks `W3-14`. |
| `P2-00` | DEPLOY | Stop serving OSM's public tiles from the embed before it's public. Stadia Maps (free tier, then ~$20/mo) or Protomaps on Cloudflare R2 (~$3/mo). `TILE_URL` is one constant either way. Independent of `W2-08`. |
| `W3-14` | EAS_BUILD | Depends on `W2-08`. Replace the three `PLACEHOLDER`s in `mobile/app.json` (**irreversible once submitted**), point `eas.json` at the real Railway domain, Google Maps SDK key, `eas init`, `eas credentials`, `eas build --profile production --platform all`. |
| `W3-15` | STORE_ACCOUNT | Depends on `W3-14`. Apple Developer Program ($99/yr) + Google Play Console ($25). Store copy is already written (`mobile/store/listing.md`, `mobile/store/privacy.md`). Needs real device screenshots for Android (no emulator here) and a feature graphic. **Read the note's "THE ONE PEOPLE DISCOVER TOO LATE"** — a personal Play account needs 14 days of closed testing with 12 testers before production access, regardless of how finished the app is; start that the day `W3-14` produces an `.aab`. |

**A real device, walking around (no account, no money):**

| What | Why the loop can't do it |
|---|---|
| Proximity notification (F28, commit `f6f8a7b`) end-to-end | Code and config are both done and offline-verified (`expo prebuild --no-install`), but nobody has walked a real build into a geofenced stop's radius with the app backgrounded to confirm the local notification actually fires. |
| `W3-13` (not a checklist item, see below) | Already performed once on a real simulator; recorded, not re-parked. |

**`W3-13` is discharged, not parked.** Its `verify` is `MANUAL` and
`test_done_task_is_actually_proven` correctly refuses to call a screenshot an
exit code, so it stays `blocked` forever by design — read its own note in
`TASKS.yaml` for the full record of what was actually seen on a real iOS
Simulator build (permission primer, pinned credit, sealed composition
refusing at 128m). Nothing further to do here; it is not a to-do, it is an
audit trail.

## Do not redo

- **Every commit in the two tables above is in.** Contrast scoring, the layer
  filter, `meta.total`, the tag vocabulary, the palette (including the
  2026-09-23 warm-accent recolor), cross-video place dedup, the proximity
  unlock, submissions with photo and audio, Google/Apple sign-in, the dev
  seed, rate limiting, the corpus export, the pinned credit, anniversaries and
  time locks, the route polyline, both logo animations, the tab bar
  delimiters, the start-route affordance, the route-complete haptic, the
  configurable route distance, hearting a memory, the streak counter, the
  proximity notification, and the warm accent. `git log` carries the commit
  for each.
- **A prior tick in this session (t37) wrongly declared the founder-brainstorm
  list fully exhausted before it actually was** — it missed the still-unbuilt
  "warm accent" item. That was caught and corrected before the next tick
  started real work (see `loop/JOURNAL.md` t37's correction line). **This
  STATE.md's "terminal" claim has been re-verified twice**: once after t37's
  correction (found warm-accent), and again after t38 shipped warm-accent
  (read all 4 remaining unchecked founder-brainstorm lines in full — each
  explicitly states no build is implied). If a human adds new lines to
  TODO.md's founder-brainstorm section, or un-blocks a `NEEDS_DECISION` task,
  re-scan before trusting either list is still empty — don't just trust this
  file's word for it, the same mistake t37 made.
- **The streak is computed, not stored.** `api.accounts.current_streak(days,
  today)` is a pure function over `unlocks.unlocked_at::date` fetched via
  `STREAK_DAYS_QUERY` (`api/queries.py`) through the existing `MY_DEVICES`
  account grouping. Do not add a `streak_count`/`streak_date` column.
- **The proximity notification watches today's route, not the map viewport.**
  `App.tsx` re-registers geofences off `routeShown`, not `memories`/the panned
  map region — bounded, already "nearby", and does not thrash on every pan.
- **`isIosBackgroundLocationEnabled` stays `false`** in `app.json`'s
  expo-location plugin options. Geofencing is CoreLocation region monitoring,
  which wakes the app on its own; it does not need continuous
  `UIBackgroundModes: ["location"]`. Do not flip this "to be safe".
- **`seal`/`sealSoft`/`sealDeep` are `#8A5A17`/`#F0E4C8`/`#5C3A0E` (light) and
  `#D9A54B`/`#3D3018`/`#F0C878` (dark) as of 2026-09-23** — a warm ochre,
  not the stamp red they were before. `api/card.py`'s `--accent` and the two
  hardcoded map-`Circle` rgba literals in `App.tsx` were updated with it and
  must move together with any future change to `theme.ts`'s `seal` —
  `tests/test_palette.py` only catches the `theme.ts`↔`card.py` drift, not
  the `App.tsx` one, because a `Circle` can't take a `dual()` value.
- **`daily_routes.radius_meters` exists on both the local dev db (migration
  014 applied) and `db/schema.sql`.** Do not re-run 014 against the dev db
  again — idempotent, but nothing to gain.
- **`Haptics.notificationAsync(NotificationFeedbackType.Success)` fires from
  two places** (`UnlockButton.tsx` on a completed hold, `App.tsx:unlock()` on
  a route-completing unlock) — deliberate. Don't add a third meaning to it
  without checking both existing ones first.
- **The `ruff format` corruption was never ruff** — an editor watching the
  directory. `compileall` catches it every time.
- **The OSM/Overpass enrichment pass for contrast is deliberately not built**:
  60% of coordinates are city centroids; it would confidently describe the
  wrong street corner.
- **`SplashScreen.preventAutoHideAsync()` is called at `App.tsx` module
  scope.** Do not add a second call, and don't remove it without also
  removing `StartupLogo`'s `hideAsync()`.
- **`ios/` and `android/` are gitignored, disposable `expo prebuild`
  output.** Regenerating them is expected and safe; delete them again after
  checking a manifest/plist.
- **A stray, long-running `pytest`/`verify.sh` process from an unrelated
  earlier session can survive between ticks** in this environment and collide
  with a later gate run against the same shared Docker Postgres, producing a
  spurious `RED` ("database system is in recovery mode") unrelated to any
  code change. Check `ps aux | grep -i "verify.sh\|pytest"` for an
  implausibly long elapsed time before trusting a RED gate.
- **A Docker Desktop restart leaves every container `Exited`, even after the
  daemon itself is back.** `docker info` succeeding does not mean the `db`
  service is up — check `docker compose ps -a` and run `docker compose up -d
  db` if it shows `Exited`, same as the gate's own bootstrap does, before
  concluding a DB-connection RED is a code problem.

## Rejected approaches — do not retry

- Scraping channel HTML for `"videoId"` — returns 0 for every channel now.
- Homebrew Python 3.14 — broken `pyexpat`.
- expo-router, bottom-sheet or react-query for a one-screen app.
- Shelling out to `pytest --collect-only` inside a test.
- An OR-split full-text predicate for `/v1/memories/search` — built, measured
  against the live database, reverted.
- **`npx prettier` on `mobile/`** — no config, rewrites everything to double
  quotes at 80 columns. Match the file by hand.
- **Opening the `com.PLACEHOLDER.memorylane://` URL by hand** to point the dev
  client at Metro. Use `REACT_NATIVE_PACKAGER_HOSTNAME=localhost` +
  `xcrun simctl launch`.
- **Precise SVG path length via `getTotalLength()`** for the startup-logo
  animation — a fixed overshoot `strokeDasharray` was enough.
- **A stored `streak_count`/`streak_date` counter** — rejected for a computed
  streak off `unlocks`.
- **Geofencing off the map's viewport list** (`memories`/`shown`) — rejected
  in favor of today's route (`routeShown`): bounded, already nearby, no
  pan-driven thrashing.
- **`UIBackgroundModes: ["location"]`** for the proximity notification —
  region monitoring doesn't need it; declaring it asks review for more than
  the feature uses.
- **A "moss" (green-leaning) variant of the new accent** — tested and passed
  contrast (4.85:1 light, tighter margin than the ochre-brown chosen), but the
  ochre-brown ramp cleared every pair with more room (5.4:1+) and reads just
  as warm; picked for margin, not for looking worse.

## If you are a human reading this because the loop stopped

Nothing is broken. Every task the loop can build without you has been built,
tested, and committed to `loop/autopilot` (not pushed — `main` is behind by
this entire session). Pick anything from the checklist above, do it, and
either hand the result back to a fresh `/ml-tick` (for a decision: just edit
the task's `state`/`gate` in `TASKS.yaml` and the note explaining what was
decided) or continue by hand from there (for anything requiring an account,
a build, or a store submission — those stay manual forever, the loop must
never hold credentials or spend money).
