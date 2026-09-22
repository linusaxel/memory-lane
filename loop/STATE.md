# LOOP STATE — every TASKS.yaml task is done or parked; working the founder brainstorm list.

```
updated:  2026-09-23
branch:   loop/autopilot   — NOT pushed. `main` is behind by this session's commits.
gate:     GREEN, 568 pytest + 63 node tests
status:   TASKS.yaml has no `todo` and no `doing` left (unchanged from
          2026-09-21). This tick's work came from TODO.md's untracked
          "Ideas — founder brainstorm, unvetted" list instead, per explicit
          user direction, not from TASKS.yaml.
```

**`TODO.md` is the roadmap and the source of truth.** This file is the loop's
orientation doc and does not compete with it. Where they disagree, TODO.md
wins and this file is stale.

## What this session added

| | |
|---|---|
| `caba568` | **Animated startup logo** (TODO.md brainstorm list). |
| `6584fdb` | **Tab bar delimiters** (TODO.md brainstorm list). |
| `1daec1e` | **Start-route affordance** (TODO.md brainstorm list). |
| `a0b5caa` | **Route-complete moment** (TODO.md brainstorm list). |
| `e52e956` | **Configurable route distance** (TODO.md brainstorm list). |
| `eb6060b` | **Heart/favorite a memory** (TODO.md brainstorm list). `memory_hearts` join table, `POST /v1/memories/{id}/heart`, `heart_count` on every read. Landed with no journal line and a stale STATE.md at the time (a prior tick's session ended mid-STEP-5) — backfilled at the start of the next tick; gate was re-verified green before any new work started. If a future tick finds another gap like this, do the same: confirm the commit's tests still pass, backfill JOURNAL.md with the real commit SHA and date, then continue. |
| `d316427` | **Streak counter** (TODO.md brainstorm list, streak half of "streak + proximity notification"). `api.accounts.current_streak` reads distinct calendar days from `unlocks` (via the existing `MY_DEVICES` account grouping) and counts back from today to the first gap — **no new column**, cheaper than TODO.md's own `users.streak_count`/`streak_date` suggestion and nothing to desync across a signed-in account's devices. `Profile.streak`, shown in `Settings.tsx`'s stat row once above zero. F27 in `docs/08-ux-flows.md`; `docs/10-decisions.md`/`docs/11-memory-types.md` updated from "planned" to "shipped" for this half. |

Prior session (not journaled at the time, visible only in git log): `27ddff9`
static logo mark, `f9f7fbb`/`94c9dbc` seeded the brainstorm list itself and
resolved three flagged conflicts (warm accent, subscription-as-second-track,
streak+geofence notification — all "Resolved 2026-09-22" in TODO.md).

## What works right now

```bash
docker compose up -d --build              # API + PostGIS
./api/test_api.sh http://localhost:8080   # 11 checks
./loop/verify.sh                          # 568 pytest + 63 node tests, GREEN
python -m pipeline.seed_dev               # memories you can actually reach
cd mobile && npx expo start               # the app
```

## The next concrete action

**The founder-brainstorm list is down to one open item.** Every other line in
TODO.md's "Ideas — founder brainstorm, unvetted" section (line ~811) is now
either `[x]` done, a Resolved/decision note with no code of its own, or a
pointer at an existing open question. Re-scan the section head to tail before
trusting this, in case a human edited it in the meantime — but as of this
tick, the one real remaining line is:

1. **Proximity notification (the other half of "streak + proximity
   notification, reopened").** On-device geofencing (`expo-location`'s
   `startGeofencingAsync`) firing a **local** notification when a walkable
   memory comes into range — no APNs/FCM, no push server. This is the bigger
   half: it requires flipping `mobile/UI.md` rule 2
   (`ACCESS_BACKGROUND_LOCATION`, the iOS `NSLocationAlways…`/
   `NSMotionUsageDescription` strings, currently forced `false`) — a real App
   Store privacy-review change, not a toggle, and `mobile/UI.md` itself needs
   its rule-2 text updated once this lands, not just the app config. Not a
   hard-limit gate on its own (no store account or build touched to write the
   code), but big enough that a tick attempting it should expect to spend the
   whole tick on the permission plumbing alone and land the actual
   notification logic in a follow-up, rather than trying both at once.
   Also update `docs/08-ux-flows.md` F1's "deliberately absent" list and F23
   once it ships — both currently still say "no notifications", correctly,
   until this lands.

After that, TASKS.yaml's own next actions (unchanged, still true):

2. **`P4-01`, free, needs a decision** — read the note on that task; three
   defensible ways out, Phase 4 vs. 3.2's permanent stranger note.
3. **`W4-02` / semantic dedup, free, needs a decision** — TODO.md 1.2:
   structured venue/locality/region fields vs. a human review pass.
4. **`API_CREDITS`** — the extraction path has never run against a real
   API. `python -m pipeline.enqueue --video <content_id>` then `--status
   <id>`, no `--limit` flag on the bulk path.
5. **`DEPLOY`** — Railway, ~$5/mo, not Fly (no PostGIS on its managed
   Postgres). Unblocks `P2-00` and 2.3.
6. **`EAS_BUILD`**, then **`STORE_ACCOUNT`** — three `PLACEHOLDER`
   tripwires first; bundle id is irreversible once submitted.

## Parked, and what each one needs

| Task | Gate | What a human has to do |
|---|---|---|
| `W1-09` | API_CREDITS | one video through the queue path, then read 20 summaries |
| `W4-02` | NEEDS_DECISION | structured venue/locality/region from extraction, or accept 25 pairs by review |
| `P4-01` | NEEDS_DECISION | decide what a stranger note *is*, now that 3.2 shipped a permanent one |
| `P2-00` | DEPLOY | a tile account. Stadia key, or Protomaps on R2. `TILE_URL` is one constant |
| `D-05` | NEEDS_DECISION | choose the historical source (arkiv.dk scraping vs setlist.fm's REST API), and confirm reuse terms |
| `EAS_BUILD` | EAS_BUILD | replace the three PLACEHOLDERs, then build |
| `STORE_ACCOUNT` | STORE_ACCOUNT | Apple $99/yr, Play $25 |

**`W3-13` is discharged, not parked.** Unchanged from last session — see
git history / prior STATE.md revisions for the full record; it stays
`blocked` in `TASKS.yaml` because its `verify` is `MANUAL`.

## Do not redo

- **Contrast scoring, the layer filter, `meta.total`, the tag vocabulary, the
  palette, cross-video place dedup, the proximity unlock, submissions with photo
  and audio, Google/Apple sign-in, the dev seed, rate limiting, the corpus
  export, the pinned credit, anniversaries and time locks, the route polyline,
  the static logo mark, the animated startup logo, the tab bar delimiters,
  the start-route affordance, the route-complete haptic, the configurable
  route distance, hearting a memory, the streak counter** are all in. TODO.md
  carries the commit for each.
- **The streak is computed, not stored.** `api.accounts.current_streak(days,
  today)` is a pure function over `unlocks.unlocked_at::date` fetched via
  `STREAK_DAYS_QUERY` (api/queries.py) through the existing `MY_DEVICES`
  account grouping. Do not add a `streak_count`/`streak_date` column — that
  was TODO.md's own first idea and was deliberately not built, because it
  would need incrementing at every unlock call site and would drift the
  moment a second device on the same account unlocks something. If this ever
  gets too slow to compute on read (it will not at this corpus size), the
  fix is an index on `unlocks(device_id, unlocked_at)`, not a stored counter.
- **`daily_routes.radius_meters` exists on both the local dev db (migration
  014 applied) and `db/schema.sql`.** A fresh test db already has it; do not
  re-run 014 against the dev db a second time (it is idempotent - `ADD
  COLUMN IF NOT EXISTS` - but there is nothing to gain by repeating it).
- **`Haptics.notificationAsync(NotificationFeedbackType.Success)` now fires
  from two places** (`UnlockButton.tsx` on a completed hold,
  `App.tsx:unlock()` when that unlock also completes a started route) -
  deliberate, not drift. Both mean "a thing was earned." Do not add a third
  meaning to this exact call without checking both existing ones first.
- **The `ruff format` corruption was never ruff.** Traced to an editor watching
  the directory. `compileall` catches it every time and nothing ever landed.
- **The OSM/Overpass enrichment pass for contrast** is deliberately not built:
  60% of the coordinates are city centroids, so it would confidently describe
  the wrong street corner.
- **`SplashScreen.preventAutoHideAsync()` is now called at App.tsx module
  scope.** Do not add a second call elsewhere (React docs warn against
  duplicate registration) and do not remove it without also removing
  `StartupLogo`'s `hideAsync()` call, or the splash never hides.

## Rejected approaches — do not retry

- Scraping channel HTML for `"videoId"` — returns 0 for every channel now.
- Homebrew Python 3.14 — broken `pyexpat`.
- expo-router, bottom-sheet or react-query for a one-screen app.
- Shelling out to `pytest --collect-only` inside a test.
- An OR-split full-text predicate for `/v1/memories/search` — built, measured
  against the live database, reverted.
- **`npx prettier` on `mobile/`** — there is no config, so it rewrites every
  file to double quotes at 80 columns. Match the file by hand.
- **Opening the `com.PLACEHOLDER.memorylane://` URL by hand** to point the dev
  client at Metro. Start Metro with `REACT_NATIVE_PACKAGER_HOSTNAME=localhost`
  and use `xcrun simctl launch`.
- **Precise SVG path length via `getTotalLength()` for the startup-logo
  animation** — skipped in favor of a fixed overshoot `strokeDasharray`
  (220, longer than any of the three paths). Exact timing is not worth an
  extra native round trip for a 750ms one-shot; revisit only if the draw-on
  visibly stalls near the end on a real device.
- **A stored `streak_count`/`streak_date` counter** (TODO.md's own original
  brainstorm suggestion) — rejected in favor of computing the streak from
  `unlocks` on read. See "Do not redo" above for the reasoning.
