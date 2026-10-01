-- A profile photo, shown beside the name on what you file. A path under
-- MEDIA_DIR, not a media row: a media row with no memory is what
-- pipeline/sweep.py reaps.
--
--   docker compose exec -T db psql -U memorylane -d memorylane -v ON_ERROR_STOP=1 \
--     < db/migrations/036_avatar.sql

ALTER TABLE users ADD COLUMN IF NOT EXISTS avatar_path TEXT;
