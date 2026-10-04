-- The locket a memory's pin and unlock are drawn as, chosen by its author.
-- NULL is the default locket (api/progression.py, LOCKET_DEFAULT)
-- (docs/10-decisions.md#lockets-one-per-memory-chosen-by-its-author-earned-by-level).
--
--   docker compose exec -T db psql -U memorylane -d memorylane -v ON_ERROR_STOP=1 \
--     < db/migrations/040_locket.sql

ALTER TABLE memories ADD COLUMN IF NOT EXISTS locket TEXT;
