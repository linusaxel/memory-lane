# LOOP STATE — W0–W3 and Phase 1.5 shipped. Phase 3 started. TODO.md is the roadmap.

```
updated:  2026-09-20 (interactive session, not a loop tick)
branch:   loop/autopilot   — pushed, and main is at the same commit
gate:     GREEN, 398 tests
status:   W0–W3, Phase 1.5 (proximity unlock) and Phase 3.1–3.3 (submissions and
          sign-in) are in. Remaining work is TODO.md and the human gates below.
```

**Since the last tick**, all in interactive sessions:

- the proximity-unlock mechanic, server-side, with the collection and three tabs;
- **user-submitted memories** — `POST /v1/memories` with photo and audio upload,
  a submit screen, and a report endpoint that hides a memory at three reports;
- **Google and Apple sign-in**, so a collection survives a new phone. No
  passwords and no session tokens: the device id stays the only credential and
  signing in binds `devices.user_id`;
- a tidy-up sweep that split `api/main.py` into eight modules (1784 lines → 69),
  moved the design reasoning into `docs/10-decisions.md`, deleted what nothing
  called, and put the gate on GitHub Actions;
- **one tag vocabulary** instead of two: the app offered `sport`, the corpus
  stored `sports`, and `m.tags && …` is exact-string, so that chip matched
  nothing. `pipeline/tags.py` is the list, both write paths filter against it,
  and a test holds the app's copy equal to the server's;
- the palette actually applied (`65a222a`): press states on 28 controls, the
  card off the Tailwind zinc ramp, and two contrast pairs that missed AA.

**`TODO.md` is the roadmap and the source of truth.** This file is the loop's
orientation doc and does not compete with it. Where they disagree, TODO.md wins
and this file is stale.

## What works right now

```bash
docker compose up -d --build              # API + PostGIS
./api/test_api.sh http://localhost:8080   # 11 checks
./loop/verify.sh                          # 398 tests, GREEN
cd mobile && npx expo start               # the app
```

- **Crawler**: `@TuesdayswithStories` auto-discovered, 25 videos ingested,
  25 transcripts fetched, 0 failed. Baseline before this work: **0 videos**.
- **Database**: 224 memories across 176 places, after the unique index merged 30
  exact duplicates and `pipeline/dedup.py` merged 18 more by review. 94 memories
  are gated by the unlock radius; the rest sit on shared city centroids and stay
  open. See F7. Ten tables now — submissions brought `users`, `media` and
  `reports`, sign-in brought `identities`.
- **API**: containerized, CORS lockable, `/privacy` live, and **no longer
  read-only** — it takes submissions, uploads and reports. There is still no
  rate limit on any of that; see TODO 3.5, it is the real gap.
- **App**: three tabs, proximity unlock with a hold-to-unlock ring, a collection
  that syncs from the server, a submit screen with photo and voice, and
  Google/Apple sign-in. Neither sign-in button works in Expo Go — they need real
  client ids and a development build.

## THE HUMAN CHECKLIST — in dependency order

### 1. W1-09 · `API_CREDITS` — check extraction quality (~$0.10)

**There is no `--limit` flag.** `python -m pipeline.extract` runs
`extract_all_pending()` and bills every pending video (25 of them). To spend a
few cents instead, push one video through the queue path:
```bash
source venv/bin/activate
python -m pipeline.enqueue --video <content_id>   # then --status <content_id>
```
Then eyeball the result:
```sql
SELECT m.summary, p.name, m.extraction_confidence FROM memories m
JOIN places p ON m.place_id = p.id ORDER BY m.id DESC LIMIT 20;
```
Summaries should be vivid and name people ("Mark and Joe argued about
pastrami"), not generic ("they visited a deli"). If they are flat, tune
`SYSTEM_PROMPT` in `pipeline/extract.py`.

**While you are in there:** both model IDs are current now
(`claude-sonnet-5`, `claude-haiku-4-5`, in `pipeline/config.py`), but neither
has been run against real credits, so `EXTRACTION_MODEL` is still unvalidated —
that is most of what this gate is for. Also worth adding `cache_control` to the
system prompt, which is resent for every chunk.

### 2. W2-08 · `DEPLOY` — Railway (~$5/mo)

Railway, not Fly: Fly's managed Postgres has **no PostGIS**, so Fly would mean
running your own database container anyway. Railway runs the identical
`postgis/postgis:16-3.4` image already in `docker-compose.yml`.

1. New project → add service from image `postgis/postgis:16-3.4`,
   volume at `/var/lib/postgresql/data`, env `PGDATA=/var/lib/postgresql/data/pgdata`
2. `psql $DATABASE_URL -f db/schema.sql`
3. Add service from this repo (Railway auto-detects the `Dockerfile`);
   set `DATABASE_URL=${{Postgres.DATABASE_URL}}`
4. Load data: run the pipeline against the prod URL, or `pg_dump` local → restore
5. `./api/test_api.sh https://<domain>` — expect 14/14
6. **Note the HTTPS domain. It unblocks step 4 below.**

### 3. ~~W3-13 · look at the app~~ — **done**

Driven in the Simulator repeatedly across an interactive session: map, locked
and unlocked sheets, the hold-to-unlock ring, all three tabs, the permission
primer and the reach circle. Screenshots were reviewed rather than filed, and
`mobile/UI.md` carries the recipe. Kept below because the recipe is still how
you do it.

Simulator builds need no Apple account and no signing. **The recipe lives in
`mobile/UI.md` → "Verifying a UI change"** — this file used to keep a second
copy that had drifted (`expo run:ios` instead of `expo start --ios`, and missing
the `simctl privacy … grant` without which the permission dialog covers the
first screen). One copy now.

Confirm: the permission prompt shows our copy, pins render, the sheet opens,
and "Watch at 12:43" opens YouTube at the right second.

**Setting the location is not enough to reach a memory**, and that is a data
problem rather than a Simulator one — every dense point in the corpus is a
model-guessed centroid and therefore deliberately ungated, while the 83 gated
memories are scattered. TODO 3.6 is the dev seed that fixes it.

*Android cannot be checked locally* — no SDK, no adb. It is covered by the
manifest assertions and then by the first EAS build.

### 4. W3-14 · `EAS_BUILD` — real binaries

Three `PLACEHOLDER` tripwires must be replaced first:

| Where | Replace with |
|---|---|
| `mobile/app.json` → `ios.bundleIdentifier` / `android.package` | your real reverse-domain id — **irreversible once submitted** |
| `mobile/app.json` → `android.config.googleMaps.apiKey` | a Maps SDK for Android key |
| `mobile/eas.json` → `production.env.EXPO_PUBLIC_API_URL` | the Railway HTTPS domain from step 2 |

```bash
npm i -g eas-cli && eas login && eas init
eas credentials            # Apple cert + profile; Android keystore
eas build --profile production --platform all
```

Note the circular dependency: restricting the Maps key to package + SHA-1 needs
a signing SHA-1 that does not exist until `eas credentials` runs. Leave the key
unrestricted, then lock it down afterwards.

### 5. W3-15 · `STORE_ACCOUNT` — submit

Apple Developer Program **$99/yr** (identity verification, 1–7 days) and Google
Play Console **$25 once**. Copy is ready in `mobile/store/listing.md`; the
privacy URL is `https://<domain>/privacy`, already served by the API.

Pre-answered for you: export compliance (`ITSAppUsesNonExemptEncryption: false`),
no iPad screenshots (`supportsTablet: false`), and no background-location
declaration (the permission is deliberately absent).

Still needs a real Android device: 2+ phone screenshots and a 1024×500 feature
graphic. Install the `preview` APK from EAS — using iOS screenshots on a Play
listing is a policy risk.

> ### The one people discover too late
> If your Play account is **personal** rather than an organization, production
> access is gated behind **closed testing with 12 testers for 14 continuous
> days** — no matter how finished the app is. Start it the day step 4 produces
> an `.aab`, not after everything else is done.

## Known gaps, deliberately left

- **`published_at` is still NULL.** The INSERT path works and handles None
  safely, but yt-dlp's flat extraction returns no timestamp for this channel
  (verified). Real dates need a per-video fetch or the RSS feed (newest 15
  only). Nothing in the API serves it, so it blocks nothing.
- **No rate limiting on a write path that exists.** This entry used to say the
  API was read-only, which stopped being true the day submissions shipped.
  Nothing caps how many memories one device can file or how much it can upload,
  so a loop fills the disk. TODO 3.5, and the most real gap on this list.
- **No auth.** The device id is a bearer token in a request body: anyone holding
  yours can post as you, and signing in did not change that by design. Same
  threat model as the self-reported position. `limit<=100` and
  `radius_km<=100` bound the read side.
- **`/v1/memories/search` has no usable index.**
  `to_tsvector('english', m.summary || ' ' || p.name)` spans two tables, so no
  expression index can serve it — the predicate must be split into an `OR`
  first. v1 has no search screen, so nothing uses the slow path.
- Full list in `loop/TASKS.yaml` → `inbox:`.

## Rejected approaches — do NOT retry

- **Scraping channel HTML for `"videoId":"..."`** — returns 0 videos for every
  channel tested (2026-09-20). Not a regex to fix; YouTube stopped serving it.
- **Homebrew Python 3.14** — broken `pyexpat` breaks `pip` and
  `platform.mac_ver()`. The venv is uv-managed **3.12.12**. Install with
  `uv pip install --python venv/bin/python ...`, never `venv/bin/pip`.
  The broken venv was at `venv.broken-py314/`; it is deleted and gitignored.
- **`expo-router` / bottom-sheet / react-query** — three tabs, four modals and
  a handful of fetches, all hand-rolled. Still refused: a router would be more
  code than the thing it routes.
- **Shelling out to `pytest --collect-only` inside a test** — fork bomb.
