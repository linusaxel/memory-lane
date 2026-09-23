-- How long a video is, from the channel listing, so clips cut from full
-- episodes can be skipped before their transcript is fetched. Null for
-- hand-listed videos and for rows ingested before this; backfill those with
-- `python -m pipeline.ingest --refresh-sources`. See MIN_VIDEO_MINUTES in
-- pipeline/config.py.
--
--   docker compose exec -T db psql -U memorylane -d memorylane -v ON_ERROR_STOP=1 \
--     < db/migrations/020_content_duration.sql

ALTER TABLE content ADD COLUMN IF NOT EXISTS duration_seconds INTEGER;
