-- The claims in a summary its chunk doesn't make, listed for review and never
-- edited in. NULL is never checked, {} is checked and clean. See
-- docs/10-decisions.md#a-summary-is-checked-against-its-chunk-not-corrected.
--
--   docker compose exec -T db psql -U memorylane -d memorylane -v ON_ERROR_STOP=1 \
--     < db/migrations/031_unsupported.sql

ALTER TABLE memories ADD COLUMN IF NOT EXISTS unsupported TEXT[];
