-- The names in a summary that link to Wikipedia. Written by pipeline/links.py.
--
--   docker compose exec -T db psql -U memorylane -d memorylane -v ON_ERROR_STOP=1 \
--     < db/migrations/031_memory_links.sql

ALTER TABLE memories ADD COLUMN IF NOT EXISTS links JSONB;
