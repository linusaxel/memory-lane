-- One line in the teller's own words, copied from the source and checked
-- against it (pipeline/extract.py, grounded). Shown only once it is open.
--
--   docker compose exec -T db psql -U memorylane -d memorylane -v ON_ERROR_STOP=1 \
--     < db/migrations/035_memory_quote.sql

ALTER TABLE memories ADD COLUMN IF NOT EXISTS quote TEXT;
ALTER TABLE memories ADD COLUMN IF NOT EXISTS quote_by TEXT;
