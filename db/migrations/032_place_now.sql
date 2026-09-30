-- What stands on a place today, from OSM. Written by pipeline/now.py.
--
--   docker compose exec -T db psql -U memorylane -d memorylane -v ON_ERROR_STOP=1 \
--     < db/migrations/032_place_now.sql

ALTER TABLE places ADD COLUMN IF NOT EXISTS now JSONB;
