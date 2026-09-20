# JOURNAL — append-only, one line per tick. Never rewrite a line.
# format: <time> t<tick> <task> <state> commit=<sha> gate=<GREEN|RED|INFRA> <note>
2026-09-20T00:00Z t0 W0-01 done  commit=b7fc77b gate=GREEN bootstrap: loop harness written by hand; venv rebuilt on py3.12 (brew py3.14 pyexpat broken, pip unusable); measured old crawler returns 0 videos for every channel
2026-09-20T12:05Z t1 W1-01 done  commit=4a36a4b gate=GREEN yt-dlp 2026.08.19 declared+installed; verify green, 18 tests pass
2026-09-20T12:09Z t2 W1-02 done  commit=099a12c gate=GREEN crawler 139->85 lines, discovery only; 12 offline tests; deleted transcript dupes + unsafe extract_video_id
2026-09-20T12:13Z t3 W1-03 done  commit=2b2f5c5 gate=GREEN live proof: 150/150 videos from @veritasium (was 0); 2 live tests deselected by gate
2026-09-20T12:17Z t4 W1-04 done  commit=d79700c gate=GREEN channel: source wired into Stage 1 ingest; published_at now populated; 10 real-PostGIS tests; run_all.py unchanged
2026-09-20T12:21Z t5 W1-05 done  commit=d429e33 gate=GREEN @TuesdayswithStories declared (25 newest) on the existing source; handle verified, returns 25
