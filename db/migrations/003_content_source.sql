-- Attribution for the publisher, not the item. The app showed a memory with no
-- indication of where it came from, which reads as the app asserting it - and
-- "the speaker" in half the summaries had no referent anywhere on screen.
--
-- Run once against an existing database. Fresh ones get this from schema.sql.
--
--   docker compose exec -T db psql -U memorylane -d memorylane -v ON_ERROR_STOP=1 \
--     < db/migrations/003_content_source.sql
--
-- Backfilling the values is a separate step, because it needs the network:
--
--   python -m pipeline.ingest --refresh-sources

ALTER TABLE content ADD COLUMN IF NOT EXISTS source_url VARCHAR(1024);
ALTER TABLE content ADD COLUMN IF NOT EXISTS source_icon_url VARCHAR(1024);
