-- A route is now planned: the device picks a walk length, previews it, and
-- accepts it (POST /v1/routes/today). The search radius is derived from that
-- length, so the column records the length instead. Old rows are daily and
-- expire on their own; their radius stands in as a length.
--
--   docker compose exec -T db psql -U memorylane -d memorylane -v ON_ERROR_STOP=1 \
--     < db/migrations/022_route_budget.sql

DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'daily_routes' AND column_name = 'radius_meters'
    ) THEN
        ALTER TABLE daily_routes RENAME COLUMN radius_meters TO budget_meters;
    END IF;
END $$;
