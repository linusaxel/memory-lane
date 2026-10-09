-- A walk's mystery stop: also in memory_ids, so it opens like any stop, but
-- not owed and withheld until found (docs/10-decisions.md#a-mystery-stop).
--
--   docker compose exec -T db psql -U memorylane -d memorylane -v ON_ERROR_STOP=1 \
--     < db/migrations/050_route_mystery.sql

ALTER TABLE daily_routes ADD COLUMN IF NOT EXISTS mystery_id INTEGER;
