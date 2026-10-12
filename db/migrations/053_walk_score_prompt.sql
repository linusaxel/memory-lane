-- Which walk-score prompt gave the score: one scored by an older prompt is
-- stale, and `walk_score --all` scores it again (pipeline/walk_score.py).
--
--   docker compose exec -T db psql -U memorylane -d memorylane -v ON_ERROR_STOP=1 \
--     < db/migrations/053_walk_score_prompt.sql

ALTER TABLE memories ADD COLUMN IF NOT EXISTS walk_score_prompt TEXT;
