-- What a free account has to open memories with: three on the house, then
-- steps. docs/10-decisions.md#steps-open-a-memory. Only a balance and when it
-- was last counted to, never a day's count: see that entry for why.
--
--   docker compose exec -T db psql -U memorylane -d memorylane -v ON_ERROR_STOP=1 \
--     < db/migrations/033_steps.sql

ALTER TABLE users ADD COLUMN IF NOT EXISTS free_unlocks INTEGER NOT NULL DEFAULT 3;
ALTER TABLE users ADD COLUMN IF NOT EXISTS steps INTEGER NOT NULL DEFAULT 0;
ALTER TABLE users ADD COLUMN IF NOT EXISTS steps_counted_until TIMESTAMP NOT NULL
    DEFAULT CURRENT_TIMESTAMP;
