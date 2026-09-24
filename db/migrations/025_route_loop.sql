-- Whether an accepted walk comes back to its start. It was the server-wide
-- ROUTE_LOOP; the plan page chooses it per walk now, so the stored walk has to
-- say which it was to be drawn again tomorrow, or in the Walks list.
--
--   docker compose exec -T db psql -U memorylane -d memorylane -v ON_ERROR_STOP=1 \
--     < db/migrations/025_route_loop.sql

ALTER TABLE daily_routes ADD COLUMN IF NOT EXISTS loop BOOLEAN NOT NULL DEFAULT TRUE;
