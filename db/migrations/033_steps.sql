-- The steps an account opens memories with: a balance and when it was last
-- counted to, never a day's count (docs/10-decisions.md#steps-open-a-memory).
-- Its three free unlocks were a column here until 034 made them three a day;
-- 034 drops the column where this once added it.
--
--   docker compose exec -T db psql -U memorylane -d memorylane -v ON_ERROR_STOP=1 \
--     < db/migrations/033_steps.sql

-- users.steps and users.steps_counted_until were added here;
-- 049_drop_steps_and_neighbourhoods.sql drops them again.
SELECT 1;
