-- Walks earn XP, counted from daily_routes and never stored; the key balance
-- goes. key_purchases stays as history
-- (docs/10-decisions.md#walks-earn-xp-rare-memories-wait-for-a-level).
--
--   docker compose exec -T db psql -U memorylane -d memorylane -v ON_ERROR_STOP=1 \
--     < db/migrations/038_xp_not_keys.sql

ALTER TABLE users DROP COLUMN IF EXISTS keys;
