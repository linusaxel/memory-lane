-- What nothing reads any more: the welcome unlock's day counter, the time
-- capsule's date, authored walks nobody wrote, and a friend layer with no
-- friends (docs/10-decisions.md#the-schema-keeps-only-what-is-read). Plus the
-- two lookups that had no index.
--
--   docker compose exec -T db psql -U memorylane -d memorylane -v ON_ERROR_STOP=1 \
--     < db/migrations/044_schema_cleanup.sql

ALTER TABLE users DROP COLUMN IF EXISTS free_day, DROP COLUMN IF EXISTS free_used;
ALTER TABLE memories DROP COLUMN IF EXISTS opens_at;
DROP TABLE IF EXISTS route_stops, routes;

ALTER TABLE memories DROP CONSTRAINT IF EXISTS memories_layer_check;
ALTER TABLE memories ADD CONSTRAINT memories_layer_check
    CHECK (layer IN ('historical', 'stranger'));

-- Walked today, finished walks, the Walks list: all by device, and the
-- in-progress index is partial, so it serves none of the ended ones.
CREATE INDEX IF NOT EXISTS idx_daily_routes_device ON daily_routes (device_id, route_date);
-- ingest's "have we listed this video?", once per video in a channel listing.
CREATE INDEX IF NOT EXISTS idx_content_platform_id ON content (platform_id);
