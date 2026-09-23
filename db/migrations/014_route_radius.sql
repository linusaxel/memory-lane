-- Records what radius today's route was actually searched within, so
-- GET /v1/routes/today can accept an optional radius_meters instead of every
-- device being stuck on the process-wide ROUTE_RADIUS_METERS default.
--
-- The default (4000) mirrors that env default: a row from before this column
-- existed was searched at exactly that radius, so backfilling it here is the
-- true value, not a placeholder.
--
--   docker compose exec -T db psql -U memorylane -d memorylane -v ON_ERROR_STOP=1 \
--     < db/migrations/014_route_radius.sql

-- 022 renamed it to budget_meters; replayed after that, this adds nothing.
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'daily_routes' AND column_name = 'budget_meters'
    ) THEN
        ALTER TABLE daily_routes ADD COLUMN IF NOT EXISTS radius_meters INTEGER NOT NULL DEFAULT 4000;
    END IF;
END $$;
