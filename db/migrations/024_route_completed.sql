-- When today's walk was finished: set by the unlock that earns its last stop,
-- once. Not derivable from unlocks, because a stop earned on another day also
-- counts toward a walk.
--
--   docker compose exec -T db psql -U memorylane -d memorylane -v ON_ERROR_STOP=1 \
--     < db/migrations/024_route_completed.sql

ALTER TABLE daily_routes ADD COLUMN IF NOT EXISTS completed_at TIMESTAMP;
