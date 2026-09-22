# LOOP STATE — every TASKS.yaml task is done or parked; working the founder brainstorm list.

```
updated:  2026-09-22
branch:   loop/autopilot   — NOT pushed. `main` is behind by this session's commits.
gate:     GREEN, 547 pytest + 63 node tests
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
| `caba568` | **Animated startup logo** (TODO.md brainstorm list). `mobile/src/StartupLogo.tsx` draws the logo-mark on via `strokeDashoffset`, 750ms, while `App.tsx` now holds the native splash (`SplashScreen.preventAutoHideAsync`, which nothing called before this) through font loading and the animation, then `hideAsync`s. Also fixed a stale TODO.md checkbox: the route-polyline brainstorm item was already shipped in `ba61806` and had never been checked off. |
| `6584fdb` | **Tab bar delimiters** (TODO.md brainstorm list). `mobile/src/TabBar.tsx` gets a `color.rule` hairline (1×24, centred) between each pair of tabs — the same token the bar's own top border already uses. |

Prior session (not journaled at the time, visible only in git log): `27ddff9`
static logo mark (icon/splash/favicon rasterized from `mobile/assets/logo-mark.svg`),
`f9f7fbb`/`94c9dbc` seeded the brainstorm list itself and resolved three
flagged conflicts (warm accent, subscription-as-second-track, streak+geofence
notification — all now "Resolved 2026-09-22" in TODO.md).

## What works right now

```bash
docker compose up -d --build              # API + PostGIS
./api/test_api.sh http://localhost:8080   # 11 checks
./loop/verify.sh                          # 547 pytest + 63 node tests, GREEN
python -m pipeline.seed_dev               # memories you can actually reach
cd mobile && npx expo start               # the app
```

## The next concrete action

**Two open backlogs, not one.** TASKS.yaml is exhausted (see the parked table
below, unchanged from last session). TODO.md's "Ideas — founder brainstorm,
unvetted" section (line ~811) still has real unbuilt items, cheapest first:

1. **Start-route affordance.** A button on the route view that only flips
   local UI state (the route is already computed and stored server-side) to
   highlight the next unvisited stop. No server change. Now the least loaded
   pick — tab bar delimiters and the animated startup logo are both done.
2. **Route-complete moment.** One haptic/animation on the last stop's
   unlock, reusing `mobile/src/UnlockButton.tsx`'s existing haptic rather
   than inventing a new mechanic.
3. **Configurable route distance.** Accept an optional radius on
   `GET /v1/routes/today` and store it with the day's route row instead of
   `ROUTE_RADIUS_METERS` staying a process-wide env default. Backend +
   migration, bigger than 1-2.
4. **Heart/favorite a memory.** New `memory_hearts` join table (not a
   counter column, so a device can't inflate by re-hearting),
   `POST /v1/memories/{id}/heart`, a count on the read shape. Ordering stays
   on `contrast_score`/`layer` — do not use heart count as a ranking signal
   yet.
5. **Streak + proximity notification.** Both resolved "build both" in
   TODO.md, but this is the biggest item on the list: a streak counter is
   small, but the proximity notification needs on-device geofencing AND
   flipping `mobile/UI.md` rule 2 (`ACCESS_BACKGROUND_LOCATION`, currently
   forced `false`) — a real App Store privacy-review change, not a toggle.
   Worth splitting into two ticks (streak first, geofencing separately) if
   picked up.

TASKS.yaml's own next actions (unchanged, still true):

6. **`P4-01`, free, needs a decision** — read the note on that task; three
   defensible ways out, Phase 4 vs. 3.2's permanent stranger note.
7. **`W4-02` / semantic dedup, free, needs a decision** — TODO.md 1.2:
   structured venue/locality/region fields vs. a human review pass.
8. **`API_CREDITS`** — the extraction path has never run against a real
   API. `python -m pipeline.enqueue --video <content_id>` then `--status
   <id>`, no `--limit` flag on the bulk path.
9. **`DEPLOY`** — Railway, ~$5/mo, not Fly (no PostGIS on its managed
   Postgres). Unblocks `P2-00` and 2.3.
10. **`EAS_BUILD`**, then **`STORE_ACCOUNT`** — three `PLACEHOLDER`
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
  the static logo mark, the animated startup logo, the tab bar delimiters**
  are all in. TODO.md carries the commit for each.
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
