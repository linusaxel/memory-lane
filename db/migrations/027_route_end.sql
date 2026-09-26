-- A walk can be ended, and another planned the same day (docs/10, "A walk can
-- be ended"). One walk in progress per device per day, not one walk: the key
-- (device_id, route_date) becomes a partial unique index over the rows not
-- ended, and an ended walk keeps its row, so the journal and the streak keep it.
--
--   docker compose exec -T db psql -U memorylane -d memorylane -v ON_ERROR_STOP=1 \
--     < db/migrations/027_route_end.sql

ALTER TABLE daily_routes ADD COLUMN IF NOT EXISTS ended_at TIMESTAMP;
ALTER TABLE daily_routes DROP CONSTRAINT IF EXISTS daily_routes_pkey;
ALTER TABLE daily_routes ADD COLUMN IF NOT EXISTS id SERIAL PRIMARY KEY;
CREATE UNIQUE INDEX IF NOT EXISTS daily_routes_in_progress
    ON daily_routes (device_id, route_date) WHERE ended_at IS NULL;
