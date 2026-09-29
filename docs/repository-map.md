# Repository map

Where things live. How they talk to each other is in [architecture.md](architecture.md).

## Top level

| Path | What it is |
|------|------------|
| `api/` | FastAPI over PostGIS: reads, the gate, submissions, sign-in, routes |
| `pipeline/` | Ingest → transcripts → extraction (sequential or over RQ), plus the dev and review tools |
| `crawler/` | Channel discovery via yt-dlp, and the text sources. Imports nothing from `pipeline/` |
| `db/` | `schema.sql` (applied on first container init) and `migrations/` for databases that already exist; `python -m pipeline.migrate` applies both |
| `mobile/` | The Expo app. Read [`mobile/UI.md`](../mobile/UI.md) first |
| `tests/` | pytest. [07-testing.md](07-testing.md) covers markers and fakes |
| `loop/` | `verify.sh` (the gate) and the autonomous loop's state: `TASKS.yaml`, `STATE.md`, `JOURNAL.md`, `run.sh` |
| `e2e/` | `run.sh` drives the real app on a simulator. Read [`e2e/README.md`](../e2e/README.md) before writing a flow |
| `.maestro/` | The Maestro journeys `e2e/run.sh` plays |
| `osrm/` | `build.sh` and the Copenhagen extract for a local walking router |
| `media/` | Uploads land here in dev (`MEDIA_DIR`). A named volume under Docker |
| `docs/` | Everything else. The index is in [README.md](../README.md#documentation) |

Root files: `Dockerfile`, `railway.json` and `start.sh` (deployment, see
[architecture.md](architecture.md#deployment)), `docker-compose.yml`, `pyproject.toml`
(ruff, enforced by the gate), `pytest.ini` (markers), `requirements*.txt`.

### Differences from the usual layout

There is no `src/`: the three programs (`api/`, `pipeline/`, `mobile/`) sit at the
root because they deploy and run separately. There is no `scripts/` either: `loop/`
and `e2e/` are the scripts, and each module in `pipeline/` is its own CLI
(`python -m pipeline.<name>`). This is deliberate, not a to-do.

## Key files

| File | Purpose |
|------|---------|
| `pipeline/run_all.py` | **Run full pipeline** in one command with `--dry-run`, `--skip-*` options |
| `crawler/yt_crawler.py` | **Channel discovery** via yt-dlp — lists a channel's videos + metadata, and searches YouTube |
| `crawler/sources.py` | **Text sources:** the `Source` interface and `SOURCES`. A new source is one file and one line here |
| `crawler/kb_aviser.py` | KB Labs newspapers (pre-1886), searched by street |
| `crawler/historisk_atlas.py` | Historisk Atlas stories matched by sitemap title (`Sabotage` for the WWII set) |
| `crawler/gutenberg.py` | Public-domain books: `<ebook id> <word>` keeps the windows naming the place |
| `crawler/runeberg.py` | Nordic public-domain books from Projekt Runeberg, same query shape: `<work key> <word>` |
| `pipeline/ingest.py` | Polls the `active` channels in `sources` into `content`; `--video <url> --to <id>` adds one; `--source <name> --query <q>` runs a text source |
| `pipeline/sources.py` | **The source funnel:** `list` (yield per source), `discover` (YouTube search over Copenhagen), `screen` (Haiku only), `set`, `add` |
| `pipeline/geocode.py` | **Places what the model names:** DAWA, Photon, Wikidata behind one guard, `place()` |
| `pipeline/transcripts.py` | Fetches YouTube transcripts via youtube-transcript-api |
| `pipeline/extract.py` | **Core logic** - Claude extracts memories + coordinates (sequential) |
| `pipeline/tasks.py` | RQ tasks for parallel extraction with Haiku pre-filter |
| `pipeline/worker.py` | RQ worker entry point for scaled extraction |
| `pipeline/enqueue.py` | CLI to queue videos for parallel processing |
| `pipeline/queue.py` | Redis/RQ queue setup |
| `pipeline/quality.py` | **Score the summaries.** Run before and after any prompt change; `--compare` scores a candidate prompt against the current one on the same chunks; `--labels` re-judges the labelled memories and prints what the judge keeps of each verdict |
| `pipeline/classifier_audit.py` | Re-extract a sample of chunks the pre-filter rejected; counts what it drops. Bills |
| `pipeline/review.py` | **Review extractions by hand.** Accept/edit/reject; `--stats` is the edit rate |
| `pipeline/seed_dev.py` | **Fixtures for an empty database**: e2e's, the tests', route_bench's. Refuses one holding real content |
| `pipeline/tags.py` | The extractor's closed tag list, and `from_text`: a submission's #words |
| `pipeline/dedup.py` | Propose place merges; `--only` applies a reviewed subset |
| `pipeline/export.py` | Hand a customer the corpus as rows, without the transcripts |
| `pipeline/perf.py` | **Time the read path on a corpus this size isn't.** Run before and after touching `api/queries.py` |
| `pipeline/themed_routes.py` | **Which areas could carry themed walks.** Per hotspot, the tags with `ROUTE_SIZE` walkable stops; ready at three. The check before the generated-routes job, which will grow here |
| `pipeline/route_bench.py` | **How the route does on a full map.** Every plan setting rolled at random; spurs, stops, walk vs budget, `fresh` (another roll, another walk), ms, over `seed_dev`'s dense map, planted and rolled back. Needs `ROUTING_URL`; `--solvers` needs nothing and scores the solver against brute force |
| `pipeline/sweep.py` | Reap uploads no submission ever claimed. Describes unless `--apply` |
| `pipeline/migrate.py` | **Brings a database up to `schema.sql`** and records it in `schema_migrations`. The Dockerfile runs it before the API |
| `pipeline/db.py` | Database connection (SQLAlchemy + psycopg3) |
| `pipeline/config.py` | **Every env knob**, read once. Add new settings here |
| `e2e/run.sh` | **Watch the flows happen.** Drives the real app on a simulator; `--record` leaves an mp4 |
| `e2e/travel.py` | Writes the walk flow's legs and stop names for the seeded start |
| `.maestro/` | Six journeys covering the ids in `docs/08-ux-flows.md`. Read `e2e/README.md` before writing one |
| `tests/test_flows.py` | The same six journeys headless, so a red flow can be attributed |
| `tests/fixtures/walk_labels.json` | Walk/maybe/skip for all 209 memories as of 2026-09-29 (docs/04, *Corpus read*): what a judge change is measured against |
| `tests/test_quality_labels.py` | `quality --labels` scores the judge against the labels and reruns free |
| `tests/fixtures/hashtags.json` | Hashtag cases both parsers are held to (`test_hashtags.py`, `hashtags.test.ts`) |
| `tests/test_public_host.py` | What Railway's host turns off (`/docs`, the embed, the dev database fallback), and the health check |
| `tests/fakes.py` | `FakeAnthropic` and friends: the suite never spends credits or touches the network |
| `db/schema.sql` | PostgreSQL + PostGIS schema |
| `db/migrations/` | SQL for databases that already exist, applied by `pipeline.migrate` |
| `pyproject.toml` | Ruff config. `./loop/verify.sh` enforces it |

## `api/`

| File | Purpose |
|------|---------|
| `api/main.py` | The app: CORS, the media mount, and the router includes. 60 lines |
| `api/models.py` | Every shape the API accepts or returns |
| `api/queries.py` | Every SQL string. `tests/test_api_sql.py` EXPLAINs them all |
| `api/gate.py` | row → Memory, redacted unless you are standing there |
| `api/read.py` | The read endpoints |
| `api/route_solver.py` | **Today's walk.** Which stops, what order; its docstring is how a walk is ranked |
| `api/write.py` | Unlock, media, submissions, reports |
| `api/accounts.py` | `/v1/me` and `/v1/auth/*` |
| `api/my_data.py` | A copy of one person's data, for a GDPR request. A CLI, not a route |
| `api/card.py` | The server-rendered card. Gates itself |
| `api/embed.py` | The embeddable map. Off when `ENABLE_EMBED=0` |
| `api/streets.py` | Walking metres and street shapes for today's route, from OSRM. Crow-flies × 1.3 without it |
| `api/media.py` | What an upload is allowed to be, and where it lands |
| `api/auth.py` | Google and Apple ID tokens: the three checks, and why each one |
| `api/billing.py` | Who has paid: RevenueCat's webhook and the read-back that writes `subscriptions` |
| `api/privacy.py` | The privacy policy both app stores require, served from here. Its #contact is the app's Contact row |
| `api/moderation.py` | Screens a post, note or name by local rules before it is public (App Store 1.2) |
| `api/blocked_words.txt` | The words `moderation.py` refuses: LDNOOBW English and Danish, pruned |
| `api/moderate.py` | A CLI for a reviewer: what reports hid, and reinstating it |

The endpoint list is [06-api.md](06-api.md).

## `mobile/`

| File | Purpose |
|------|---------|
| `mobile/App.tsx` | Plan → preview → walk: one map, only today's stops on it, the pill recentres |
| `mobile/src/Plan.tsx` | **How far today.** The slider page and the preview card with Start walk |
| `mobile/src/MemorySheet.tsx` | The memory detail sheet — locked and open are two compositions |
| `mobile/src/UnlockButton.tsx` | Hold-to-unlock: the ring, the haptics |
| `mobile/src/UnlockHere.tsx` | The unlock ring over the map, for the memory you stand on |
| `mobile/src/Approach.tsx` | How close you are, as the ring you are going to hold |
| `mobile/src/MemoryMarker.tsx` | One pin, lit when it can be opened from here |
| `mobile/src/NextStopArrow.tsx` | The way to the next stop, on the screen edge, while it is off screen |
| `mobile/src/RouteLine.tsx` | The route drawn: ink over a paper casing, still. Why still: docs/09 §3a |
| `mobile/src/Memories.tsx` | **The journal.** Streak, past walks, what you filed, and You |
| `mobile/src/Submit.tsx` | **The only screen that writes.** Photo, voice, tags, and why there is no map picker |
| `mobile/src/Settings.tsx` | You: its own sheet, from the map's top-right corner |
| `mobile/src/Paywall.tsx` | The subscription sheet (F35). Prices from the store; "not available" without a key |
| `mobile/src/purchases.ts` | RevenueCat, and nothing else: no-ops without a key. Never decides who has paid |
| `mobile/src/AddGlyph.tsx` | The Add button's icon: a brand pin with a plus |
| `mobile/src/CloseButton.tsx` | The × every card, sheet and page closes with |
| `mobile/src/YouGlyph.tsx` | The You button's icon |
| `mobile/src/SignIn.tsx` | The sign-in screen the app sits behind (F22), and the Account card. Neither button works in Expo Go |
| `mobile/src/MemoryMedia.tsx` | A submitted memory's photo and its recording |
| `mobile/src/SourceLine.tsx` | Who said this, with their face on it |
| `mobile/src/HeartGlyph.tsx`, `Padlock.tsx`, `StartupLogo.tsx` | Drawn marks: the heart, the app's one symbol, the launch logo |
| `mobile/src/api.ts` | The API client. One fetch, no wrapper library |
| `mobile/src/device.ts` | This installation's self-issued id |
| `mobile/src/unlocked.ts` | What this device has earned. Cached locally, authoritative on the server |
| `mobile/src/hearted.ts` | Which memories this device has hearted |
| `mobile/src/seen.ts` | The hearts and notes each of your memories had when you last looked |
| `mobile/src/Notes.tsx` | The notes under an open memory (F33) |
| `mobile/src/route.ts` | What this device's daily walk looks like, and the journal's walks. Cached, server-authoritative |
| `mobile/src/reach.ts` | Which locked pins can be opened from where you stand (unit tested) |
| `mobile/src/cluster.ts` | Group memories that share a map point (unit tested) |
| `mobile/src/region.ts` | Metres, paths and the next-stop arrow (unit tested) |
| `mobile/src/useMapCamera.ts` | Owns the map ref and every camera move |
| `mobile/src/useBreath.ts` | The next stop's pin hop. Transform only, so the tap target never moves |
| `mobile/src/geofence.ts`, `geofenceRegions.ts`, `notifyNearby.ts` | The opt-in proximity notification: the native wrapper, the pure region maths, the opt-in flag |
| `mobile/src/theme.ts` | Every colour and typeface. Never a hex or font name anywhere else |
| `mobile/src/Glass.tsx` | A control floating over the map: Liquid Glass, or paper and the one shadow |
| `mobile/src/mapStyle.ts` | How the map gets out of the way |
| `mobile/src/format.ts` | How numbers are written on screen |
| `mobile/src/hashtags.ts` | A description's #words, the server's rule, for drawing them |
| `mobile/src/types.ts` | Types more than one screen needs |
| `mobile/src/Crashed.tsx` | What a render error shows instead of a blank screen, around the whole app |
| `mobile/src/devLocation.ts`, `devOpen.ts` | Dev only: a told position, a screen opened on launch |
| `mobile/plugins/withoutBackgroundFetch.js` | Takes back the `fetch` background mode expo-task-manager declares for every app |
