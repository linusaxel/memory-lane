-- The profile photo is gone: your Collector is the one picture of you
-- (docs/10-decisions.md#one-you). The files are left for pipeline/sweep.py,
-- which reaps a file nothing references once it is old enough.
--
--   docker compose exec -T db psql -U memorylane -d memorylane -v ON_ERROR_STOP=1 \
--     < db/migrations/054_drop_avatar.sql

ALTER TABLE users DROP COLUMN IF EXISTS avatar_path;
