-- Neighbourhood outlines from OpenStreetMap, for "Where stories wait"
-- (docs/10-decisions.md#where-stories-wait). pipeline/neighbourhoods.py fills it.
--
--   docker compose exec -T db psql -U memorylane -d memorylane -v ON_ERROR_STOP=1 \
--     < db/migrations/048_neighbourhoods.sql

CREATE TABLE IF NOT EXISTS neighbourhoods (
    id BIGINT PRIMARY KEY,
    name TEXT NOT NULL,
    outline GEOGRAPHY(MULTIPOLYGON, 4326) NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_neighbourhoods_outline ON neighbourhoods USING GIST (outline);
