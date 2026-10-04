-- What a new memory's story doesn't tell: its people, more of their words,
-- then and now, asides and pictures, each from a page fetched to check it
-- (pipeline/enrich.py; docs/10-decisions.md#a-memory-is-enriched-when-it-is-made).
-- Null until looked at. Not served yet: the app shows it later.
--
--   docker compose exec -T db psql -U memorylane -d memorylane -v ON_ERROR_STOP=1 \
--     < db/migrations/042_enrichment.sql

ALTER TABLE memories ADD COLUMN IF NOT EXISTS enrichment JSONB;
