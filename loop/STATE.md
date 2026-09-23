# LOOP STATE — every TASKS.yaml task is done or parked; working the founder brainstorm list.

```
updated:  2026-09-23 (t38, INFRA)
branch:   loop/autopilot   — NOT pushed. `main` is behind by this session's commits.
gate:     INFRA — Docker daemon is down (`docker info` fails: "Cannot connect
          to the Docker daemon"). Last known-good gate: GREEN, 568 pytest +
          69 node tests, commit 8eef3f6. No code change this tick - nothing
          to fix, a human needs to start Docker Desktop.
status:   TASKS.yaml has no `todo` and no `doing` left (unchanged from
          2026-09-21). The next pick is still TODO.md's untracked
          "Ideas — founder brainstorm, unvetted" list (see below), unchanged
          from before this INFRA stop.
```

**Everything below this point is unchanged from the last GREEN tick (t37,
commit `8eef3f6`) — the INFRA stop touched nothing else.** Re-run
`./loop/verify.sh` once Docker is back before trusting the gate line above.

**`TODO.md` is the roadmap and the source of truth.** This file is the loop's
orientation doc and does not compete with it. Where they disagree, TODO.md
wins and this file is stale.

## What this session added

| | |
|---|---|
| `caba568` … `e52e956` | Animated startup logo, tab bar delimiters, start-route affordance, route-complete moment, configurable route distance — see prior STATE.md revisions or JOURNAL.md t30–t34 for detail. |
| `eb6060b` | **Heart/favorite a memory.** `memory_hearts` join table, `POST /v1/memories/{id}/heart`, `heart_count` on every read. |
| `d316427` | **Streak counter (F27).** `api.accounts.current_streak` reads distinct calendar days from `unlocks` (via `MY_DEVICES`) and counts back from today — no new column. `Profile.streak`, shown in `Settings.tsx` once above zero. |
| `f6f8a7b` | **Proximity notification (F28), the other half of "streak + proximity notification".** `mobile/src/geofence.ts` wraps `expo-location`'s `startGeofencingAsync` + `expo-task-manager` to fire a local `expo-notifications` notification when a still-locked, unsealed stop on **today's route** comes into range - not the map's panned viewport. `mobile/src/geofenceRegions.ts` holds the native-free selection logic (locked, not sealed, capped at ~20 regions), unit-tested in `geofenceRegions.test.ts`. **Off by default** - a new "Notify me when a memory is nearby" toggle in `Settings.tsx` (`notifyNearby.ts` persists it) is the only thing that requests background location; nothing else in the app asks for position while it is closed. `app.json` now declares a real `NSLocationAlwaysAndWhenInUseUsageDescription` and `isAndroidBackgroundLocationEnabled: true`; the deprecated iOS Always key and motion permission stay `false`, and `isIosBackgroundLocationEnabled` stays off (geofencing is region monitoring, not continuous tracking - asking for more than the feature needs is exactly what rule 2 exists to catch). Verified offline both ways with `expo prebuild --no-install` (Android manifest gets `ACCESS_BACKGROUND_LOCATION`; iOS Info.plist gets the real Always string and neither of the other two keys), then the generated `ios/`/`android/` dirs were deleted again (gitignored, always regenerable). `tests/test_app_config.py` rewritten to match the new intentional config. Both privacy-policy copies (`api/privacy.py`, `mobile/store/privacy.md`) disclose the new permission, guarded by a new `tests/test_store_copy.py` entry. Docs updated: F28 in `docs/08-ux-flows.md`, `docs/10-decisions.md`/`docs/11-memory-types.md` moved from "planned" to "shipped", `mobile/UI.md` rule 2 rewritten. **Not done:** a real device confirming background delivery end to end, or the human-side App Store Connect / Play Console privacy disclosure updates a new background permission requires before submission. |

Prior session (not journaled at the time, visible only in git log): `27ddff9`
static logo mark, `f9f7fbb`/`94c9dbc` seeded the brainstorm list itself and
resolved three flagged conflicts (subscription-as-second-track, streak+
geofence notification, and — see below — warm accent, all "Resolved
2026-09-22" in TODO.md).

## What works right now

```bash
docker compose up -d --build              # API + PostGIS
./api/test_api.sh http://localhost:8080   # 11 checks
./loop/verify.sh                          # 568 pytest + 69 node tests, GREEN
python -m pipeline.seed_dev               # memories you can actually reach
cd mobile && npx expo start               # the app
```

## The next concrete action

**Founder-brainstorm is *not* fully exhausted — a prior tick's summary was
wrong about this, corrected in JOURNAL.md t37.** Re-scanning TODO.md's
"Ideas — founder brainstorm, unvetted" section (line ~811) head to tail found
one real unchecked, buildable item still there:

1. **Warm accent, not a reskin** (`TODO.md`, "Resolved 2026-09-22: warm
   accent, not a reskin"). Decision already made, nothing to re-litigate:
   replace `seal` red (`mobile/src/theme.ts`) with a warm moss/ochre tone,
   re-running the same contrast measurement `mobile/UI.md` already documents
   for `seal` (it has to clear the same bar against both the map style and
   both light/dark themes). No change to the map style, card layout, or type
   system - this is one token and the doc measurement that justifies it.
   Explicitly parked *within* this same item and not to be picked up: a
   separate "urban/city" theme variant (YAGNI until Phase 1 has a second
   neighborhood).

Every other line in that section is either `[x]` done, a Resolved/decision
note that says no build is implied (subscription-as-second-track), or a
pointer at an existing open question with no code of its own
(mass-sourcing candidates → the historical-source question; onboarding →
"nothing to add unless a specific step is the complaint"; the
picture/date/description/link item → "name which screen, that's a display
fix"). Once warm-accent ships, re-scan the section head to tail again before
trusting that it is empty, the same way this tick had to correct the
previous one's premature "founder-brainstorm is done" claim.

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
| *(not a TASKS.yaml row)* proximity notification | human verification | put a build on a real device, walk it into a geofenced stop's radius with the app backgrounded, confirm the local notification actually fires; then update the App Store Connect / Play Console privacy disclosures for the new background-location permission before any submission — code and copy are both ready, this is the one thing the gate cannot check |

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
  route distance, hearting a memory, the streak counter, the proximity
  notification (geofencing)** are all in. TODO.md carries the commit for each.
- **The streak is computed, not stored.** `api.accounts.current_streak(days,
  today)` is a pure function over `unlocks.unlocked_at::date` fetched via
  `STREAK_DAYS_QUERY` (api/queries.py) through the existing `MY_DEVICES`
  account grouping. Do not add a `streak_count`/`streak_date` column.
- **The proximity notification watches today's route, not the map viewport.**
  `App.tsx` re-registers geofences off `routeShown` (the unlock-overlaid
  route), not off `memories`/the panned map region - that list is bounded
  (`ROUTE_SIZE`, well under the OS's ~20-region cap) and does not change
  every time somebody pans, which a viewport-driven watch would. Don't wire
  `startWatching` to `memories` or `shown` instead; that was considered and
  rejected for exactly that reason.
- **`isIosBackgroundLocationEnabled` stays `false` in `app.json`'s
  expo-location plugin options.** Geofencing is CoreLocation region
  monitoring, which wakes the app on its own; it does not need continuous
  `UIBackgroundModes: ["location"]`. Do not flip this "to be safe" - it would
  be over-declaring a capability the feature does not use, which is worse
  for review, not safer.
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
- **`ios/` and `android/` are gitignored, disposable `expo prebuild` output.**
  Regenerating them (this tick ran `expo prebuild --platform <p> --no-install`
  for both, once with `--clean`) is expected and safe - they are rebuilt from
  `app.json` and the installed plugins every time, never hand-edited. Delete
  them again after checking a manifest/plist rather than leaving them for git
  status to trip over.
- **A stray, long-running `pytest`/`verify.sh` process from an unrelated
  earlier session can survive between ticks** in this environment and
  collide with a later tick's own gate run against the same shared Docker
  Postgres, producing a spurious `RED` ("database system is in recovery
  mode") that has nothing to do with any code change. If a gate run fails
  with a Postgres connection/recovery error, check `ps aux | grep -i
  "verify.sh\|pytest"` for a process with an implausibly long elapsed time
  (`ps -p <pid> -o pid,etime,command`) before concluding the tree is broken;
  kill it and rerun. This happened once, in this tick (t37) — the rerun was
  clean.

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
  animation** — skipped in favor of a fixed overshoot `strokeDasharray`.
- **A stored `streak_count`/`streak_date` counter** (TODO.md's own original
  brainstorm suggestion) — rejected in favor of computing the streak from
  `unlocks` on read.
- **Geofencing off the map's viewport list (`memories`/`shown`)** — rejected
  in favor of today's route (`routeShown`): bounded, already "nearby", and
  does not thrash on every pan.
- **`UIBackgroundModes: ["location"]` / `isIosBackgroundLocationEnabled:
  true`** for the proximity notification — rejected; region monitoring does
  not need it, and declaring it would be asking iOS review for more than the
  feature uses.
