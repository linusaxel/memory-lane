-- Two leftovers found by a sweep.
--
-- geocode_response held the raw response from a Google Places integration that
-- docs/05-geocode.md described and nobody ever built. Coordinates come out of
-- the extraction prompt; nothing has ever written this column or read it.
--
-- idx_devices_user is the index that should have arrived with 006. MY_DEVICES
-- is inlined into every GET /v1/unlocks and every GET/PUT /v1/me, and without
-- it that OR is a sequential scan over the one table that grows with installs.
-- idx_memories_user and idx_identities_user already exist for the same pattern.
--
--   docker compose exec -T db psql -U memorylane -d memorylane -v ON_ERROR_STOP=1 \
--     < db/migrations/007_tidy.sql

ALTER TABLE places DROP COLUMN IF EXISTS geocode_response;

CREATE INDEX IF NOT EXISTS idx_devices_user ON devices(user_id);
