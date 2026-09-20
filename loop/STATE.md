# LOOP STATE — W0–W3 complete. Phase 1.5 shipped. TODO.md is the roadmap.

```
updated:  2026-09-20 (interactive session, not a loop tick)
branch:   loop/autopilot   — pushed, and main is at the same commit
gate:     GREEN, 265 tests
status:   W0–W3 done. Phase 1.5 (proximity unlock) done and in the app.
          Remaining work is TODO.md, and the human gates below.
```

**Since the last tick**, in an interactive session: the whole proximity-unlock
mechanic (server-side gate, hold-to-unlock, collection, three tabs), a visual
direction that is written down in `docs/09-visual-design.md`, and an audit of
`TODO.md`'s defect list that struck six entries as already fixed. W3-13 below is
done — the app has been driven in the Simulator extensively.

**This file said TERMINATED. That was wrong on two counts and is corrected here.**

1. W3-13 was unparked by commit `aab8d65`. It is now genuinely finished — the
   app has been run in the Simulator many times since. Its one automated attempt
   had failed on a missing iOS 26.5 runtime rather than on our code.
2. The W0–W3 milestone is finished, but the project is not. **`TODO.md` at the
   repo root is now the roadmap and the source of truth** — historical / friend
   / stranger layers, Copenhagen launch, contrast scoring. Phase 1 arrives here
   as W4-xx tasks. This file stays the loop's orientation doc; it does not
   compete with TODO.md.

Everything below still holds: the W0–W3 human checklist is real and unchanged.

## What works right now

```bash
docker compose up -d --build              # API + PostGIS
./api/test_api.sh http://localhost:8080   # 14/14 pass
./loop/verify.sh                          # 265 tests, GREEN
cd mobile && npx expo start               # the app
```

- **Crawler**: `@TuesdayswithStories` auto-discovered, 25 videos ingested,
  25 transcripts fetched, 0 failed. Baseline before this work: **0 videos**.
- **Database**: 224 memories across 194 places (the unique index merged 30
  duplicates), all geocoded. 83 of them are gated by the unlock radius; the
  other 133 sit on shared city centroids and stay open. See F7.
- **API**: containerized, CORS fixed, sync handlers, `/privacy` live.
- **App**: three tabs (map, unlocked, you), proximity unlock with a
  hold-to-unlock ring, an on-device collection, a permission primer, and a
  typographic direction with its own doc. Bundles for iOS and Android; both
  native manifests verified.

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

Simulator builds need no Apple account and no signing.
```bash
docker compose up -d --build api
cd mobile && EXPO_PUBLIC_API_URL=http://localhost:8080 npx expo run:ios
xcrun simctl location booted set 40.7484,-73.9857    # Manhattan, where the data is
```
Confirm: the permission prompt shows our copy, pins render, the sheet opens,
and "Watch at 12:43" opens YouTube at the right second. Take three screenshots
at 6.9" (`xcrun simctl io booted screenshot`) — map, sheet, near-me.

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
- **No auth or rate limiting.** The data is public and read-only, and an API key
  inside an app binary is not auth. `limit<=100` and `radius_km<=100` bound the
  blast radius. Add it when there is a bill to protect.
- **`/v1/memories/search` has no usable index.**
  `to_tsvector('english', m.summary || ' ' || p.name)` spans two tables, so no
  expression index can serve it — the predicate must be split into an `OR`
  first. v1 has no search screen, so nothing uses the slow path.
- **`meta.total` is wrong** on three endpoints. The app ignores it entirely.
- Full list in `loop/TASKS.yaml` → `inbox:`.

## Rejected approaches — do NOT retry

- **Scraping channel HTML for `"videoId":"..."`** — returns 0 videos for every
  channel tested (2026-09-20). Not a regex to fix; YouTube stopped serving it.
- **Homebrew Python 3.14** — broken `pyexpat` breaks `pip` and
  `platform.mac_ver()`. The venv is uv-managed **3.12.12**. Install with
  `uv pip install --python venv/bin/python ...`, never `venv/bin/pip`.
  The broken venv is at `venv.broken-py314/` (76MB, safe to delete).
- **`expo-router` / bottom-sheet / react-query** — one screen, one modal, one
  fetch. Refused on purpose.
- **Shelling out to `pytest --collect-only` inside a test** — fork bomb.
