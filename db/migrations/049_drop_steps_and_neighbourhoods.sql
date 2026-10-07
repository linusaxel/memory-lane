-- Steps bought nothing once the app became a walk planner, and "Where stories
-- wait" went with the account menu (docs/10-decisions.md#the-journal-is-you).
--
--   docker compose exec -T db psql -U memorylane -d memorylane -v ON_ERROR_STOP=1 \
--     < db/migrations/049_drop_steps_and_neighbourhoods.sql

ALTER TABLE users DROP COLUMN IF EXISTS steps;
ALTER TABLE users DROP COLUMN IF EXISTS steps_counted_until;
DROP TABLE IF EXISTS neighbourhoods;
