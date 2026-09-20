# JOURNAL — append-only, one line per tick. Never rewrite a line.
# format: <time> t<tick> <task> <state> commit=<sha> gate=<GREEN|RED|INFRA> <note>
2026-09-20T00:00Z t0 W0-01 done  commit=b7fc77b gate=GREEN bootstrap: loop harness written by hand; venv rebuilt on py3.12 (brew py3.14 pyexpat broken, pip unusable); measured old crawler returns 0 videos for every channel
2026-09-20T12:05Z t1 W1-01 done  commit=4a36a4b gate=GREEN yt-dlp 2026.08.19 declared+installed; verify green, 18 tests pass
2026-09-20T12:09Z t2 W1-02 done  commit=099a12c gate=GREEN crawler 139->85 lines, discovery only; 12 offline tests; deleted transcript dupes + unsafe extract_video_id
2026-09-20T12:13Z t3 W1-03 done  commit=2b2f5c5 gate=GREEN live proof: 150/150 videos from @veritasium (was 0); 2 live tests deselected by gate
2026-09-20T12:17Z t4 W1-04 done  commit=d79700c gate=GREEN channel: source wired into Stage 1 ingest; published_at now populated; 10 real-PostGIS tests; run_all.py unchanged
2026-09-20T12:21Z t5 W1-05 done  commit=d429e33 gate=GREEN @TuesdayswithStories declared (25 newest) on the existing source; handle verified, returns 25
2026-09-20T12:25Z t6 W1-06 done  commit=522498e gate=GREEN root-cause: bare except collapsed transient into permanent transcript failures; TimeoutError now propagates, row stays pending
2026-09-20T12:27Z t6 W1-07 done  commit=f426766 gate=GREEN documented channel:/limit: in CLAUDE.md + docs/02-ingest.md
2026-09-20T12:29Z t6 W1-08 done  commit=f426766 gate=GREEN END-TO-END: 25 new ingested, 25 transcripts fetched, 0 failed, no credits. published_at still NULL (yt-dlp flat gives no timestamp) -> inbox
2026-09-20T12:33Z t7 W2-01..03 done commit=3edb43b gate=GREEN Dockerfile+compose api service; container serves real data (224 memories, 215 places)
2026-09-20T12:38Z t8 W2-04..07 done commit=81e71ef gate=GREEN CORS credentials off, 9 async handlers -> sync def, pool_pre_ping, GET /privacy, railway.json; all 14 test_api.sh checks pass
2026-09-20T12:45Z t9  W3-01..02 done commit=8234334 gate=GREEN Node pinned 22 LTS; Expo SDK 57 + react-native-maps + expo-location scaffolded
2026-09-20T12:52Z t10 W3-03..06 done commit=ceab849 gate=GREEN api.ts (null-coord filter), region.ts + 3 node --test asserts, App.tsx map, MemorySheet
2026-09-20T12:58Z t11 W3-07..11 done commit=b183d97 gate=GREEN app.json/eas.json store config; prebuild verified BOTH manifests offline (no Android SDK); blockedPermissions strips SYSTEM_ALERT_WINDOW+storage; icon alpha guard; store copy
2026-09-20T13:02Z t12 W3-12 done  commit=b183d97 gate=GREEN expo export: iOS+Android bundles 1.5MB each, no Metro errors. 28 done / 5 parked / 0 remaining -> TERMINATE
2026-09-20T13:20Z cleanup  test_loop_is_not_on_main moved out of pytest into ml-tick STEP 5. It asserted a property of the environment, not the code, so it would have gone RED forever once this branch merged to main.
2026-09-20T14:05Z t13 W4-01 done  commit=722fd68 gate=GREEN layer/happened_at/attribution/contrast columns + 002_layers.sql; applied to live DB twice, 224 memories intact; drift guard mutation-checked
2026-09-20T14:35Z t14 W4-02 blocked commit=null gate=GREEN dedup tool shipped, auto-merge withheld: coords 1.8km apart on one venue kill the proximity rule, and "Comedy Store" recurring makes frequency call a venue a location; 148->39->25 merges, ~1/3 still wrong; needs structured place fields from extraction
2026-09-20T14:55Z t15 W4-03 done  commit=0c9d699 gate=GREEN ingest_records() text path, body as one t=0 segment so extraction needs no branch; NEAR MISS: tests wrote 3 synthetic history rows to the LIVE db, deleted, ingest_into fixture moved to conftest
2026-09-20T15:00Z t15 finding -      commit=null gate=GREEN 111/186 places sit on 34 points (14 venues on Times Square), 35 of them claiming 50m precision; coordinates are city centroids and do not admit it; reshapes W4-02/W4-04/1.5 and makes clustering mandatory
2026-09-20T15:20Z t16 W4-04 done  commit=b8e1c23 gate=GREEN HISTORICAL_SYSTEM_PROMPT chosen by source_type; both prompts now forbid claiming exact for a city guess; happened_at/attribution/layer actually persisted; queue path prompt gap marked not fixed
2026-09-20T15:50Z t17 W4-05 done  commit=730b786 gate=GREEN contrast_score+note, banded rubric, "fame is not contrast"; OSM enrichment deliberately NOT built (60% of coords are centroids, would describe the wrong corner); NULLS LAST needed in W4-06
2026-09-20T15:55Z t17 hazard -      commit=null gate=GREEN ruff format / IDE watcher rewrites single-line tuple except into python2 syntax in this repo; caught by compileall every time, nothing landed; workaround = exploded tuple w/ trailing comma
2026-09-20T16:15Z t18 W4-06 done  commit=c4c60be gate=GREEN layer filter (422 on unknown) + contrast_score DESC NULLS LAST; response carries the card fields; rebased onto peer b3a9189
2026-09-20T16:15Z t18 W4-08 done  commit=c4c60be gate=GREEN first behavioural coverage of /v1/memories/nearby; NULLS LAST assertion mutation-checked
