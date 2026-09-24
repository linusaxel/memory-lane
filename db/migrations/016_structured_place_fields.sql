-- Structured place identity: venue + locality, exact-matched, instead of
-- parsing one place_query blob. See
-- docs/10-decisions.md#place-dedup-matches-on-names-not-coordinates for why
-- the string heuristic in pipeline/dedup.py cannot separate two real venues
-- that share a street or neighborhood (Andaz West Hollywood vs Comedy Store
-- Sunset Boulevard - 4 of the 7 rejected 2026-09-20 merges were this shape).
--
-- Additive and backward compatible: existing rows get NULL in all three new
-- columns. Postgres never matches NULL against NULL under this index's WHERE
-- clause, so it simply never fires for them - they keep relying on
-- idx_places_place_query and the human-reviewed pipeline/dedup.py merges
-- already applied. Nothing here touches place_query: it stays the identity
-- column api/write.py's human submissions use ("user:<uuid>"), which this
-- migration must not disturb.
--
--   docker compose exec -T db psql -U memorylane -d memorylane -v ON_ERROR_STOP=1 \
--     < db/migrations/016_structured_place_fields.sql

ALTER TABLE places ADD COLUMN IF NOT EXISTS venue VARCHAR(255);
ALTER TABLE places ADD COLUMN IF NOT EXISTS locality VARCHAR(255);
ALTER TABLE places ADD COLUMN IF NOT EXISTS region VARCHAR(255);

-- Case/whitespace-folded exact match, not a fuzzy one. Partial: legacy rows
-- have NULL in both columns and must not collide with each other.
CREATE UNIQUE INDEX IF NOT EXISTS idx_places_venue_locality
    ON places (lower(btrim(venue)), lower(btrim(locality)))
    WHERE venue IS NOT NULL AND locality IS NOT NULL;
