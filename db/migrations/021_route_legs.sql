-- The street shape of today's route between consecutive stops, from the OSRM
-- sidecar (api/streets.py). Null when there was none: the app draws straight.
-- Stop to stop only - a leg from the start would store the start, which
-- nothing here does (docs/10-decisions.md § Routes).
--
--   docker compose exec -T db psql -U memorylane -d memorylane -v ON_ERROR_STOP=1 \
--     < db/migrations/021_route_legs.sql

ALTER TABLE daily_routes ADD COLUMN IF NOT EXISTS legs JSONB;
