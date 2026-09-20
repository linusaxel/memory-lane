-- Run ONCE by hand against an existing database:
--   docker compose exec -T db psql -U memorylane -d memorylane -v ON_ERROR_STOP=1 \
--     < db/migrations/001_places_unique.sql
--
-- Fresh databases get the index from db/schema.sql instead; the compose mount at
-- docker-entrypoint-initdb.d only runs on first volume init, so an existing
-- volume never sees schema.sql changes.
--
-- Why this exists: places had no unique constraint, so the ON CONFLICT DO NOTHING
-- in pipeline/extract.py could never fire and every extracted memory minted a new
-- place row. 224 places / 194 distinct place_query; one venue appeared six times,
-- which is six stacked pins on the map.
BEGIN;

-- 1. Coordinates first. The keeper is the lowest id, but id ordering has nothing
--    to do with which duplicate got geocoded, so an un-geocoded keeper would
--    otherwise discard the only coordinates in the group.
UPDATE places k
SET coordinates = d.coordinates,
    geocode_status = d.geocode_status
FROM (
    SELECT DISTINCT ON (place_query) place_query, coordinates, geocode_status
    FROM places
    WHERE coordinates IS NOT NULL
    ORDER BY place_query, id
) d
WHERE k.place_query = d.place_query
  AND k.coordinates IS NULL
  AND k.id = (SELECT min(id) FROM places WHERE place_query = k.place_query);

-- 2. Repoint every memory at the keeper.
UPDATE memories m
SET place_id = keep.id
FROM places p
JOIN LATERAL (
    SELECT min(id) AS id FROM places WHERE place_query = p.place_query
) keep ON TRUE
WHERE m.place_id = p.id
  AND m.place_id <> keep.id;

-- 3. Delete only orphans. memories.place_id is ON DELETE CASCADE, so this guard
--    is what makes a bug in step 2 fail loud instead of silently eating memories.
DELETE FROM places p
WHERE p.id <> (SELECT min(id) FROM places WHERE place_query = p.place_query)
  AND NOT EXISTS (SELECT 1 FROM memories WHERE place_id = p.id);

-- 4. Now it can be unique.
CREATE UNIQUE INDEX idx_places_place_query ON places (place_query);

COMMIT;
