-- Three free unlocks a day, not three ever: which day they were counted on,
-- and how many of that day's are used. A new day starts again at nothing
-- used. docs/10-decisions.md#three-free-a-day-then-steps-where-you-stand.
--
--   docker compose exec -T db psql -U memorylane -d memorylane -v ON_ERROR_STOP=1 \
--     < db/migrations/034_free_a_day.sql

ALTER TABLE users DROP COLUMN IF EXISTS free_unlocks;
ALTER TABLE users ADD COLUMN IF NOT EXISTS free_day DATE;
ALTER TABLE users ADD COLUMN IF NOT EXISTS free_used INTEGER NOT NULL DEFAULT 0;
