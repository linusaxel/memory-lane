-- Plain lockets: named spots from OpenStreetMap, collected on a walk. No story,
-- so no gate (docs/10-decisions.md#the-locket-keeper-most-stops-are-plain-lockets).
-- Loaded by pipeline/waypoints.py.
--
--   docker compose exec -T db psql -U memorylane -d memorylane -v ON_ERROR_STOP=1 \
--     < db/migrations/053_waypoints.sql

CREATE TABLE IF NOT EXISTS waypoints (
    id SERIAL PRIMARY KEY,
    osm_id TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL,
    kind TEXT NOT NULL,
    coordinates GEOGRAPHY(POINT, 4326) NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_waypoints_coordinates ON waypoints USING GIST(coordinates);
