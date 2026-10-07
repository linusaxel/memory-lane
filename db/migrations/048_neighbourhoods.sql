-- Neighbourhood outlines from OpenStreetMap, for "Where stories wait"
-- (docs/10-decisions.md#where-stories-wait).
--
--   docker compose exec -T db psql -U memorylane -d memorylane -v ON_ERROR_STOP=1 \
--     < db/migrations/048_neighbourhoods.sql

-- The neighbourhoods table was created here;
-- 049_drop_steps_and_neighbourhoods.sql drops it again.
SELECT 1;
