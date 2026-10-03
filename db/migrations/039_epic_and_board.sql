-- Epic memories and the city board
-- (docs/10-decisions.md#epic-memories-scored-by-rubric-kept-by-hearts-hidden-until-opened,
-- docs/10-decisions.md#a-city-board-by-opens).
--
--   docker compose exec -T db psql -U memorylane -d memorylane -v ON_ERROR_STOP=1 \
--     < db/migrations/039_epic_and_board.sql

ALTER TABLE memories ADD COLUMN IF NOT EXISTS walk_score SMALLINT
    CHECK (walk_score BETWEEN 0 AND 12);
ALTER TABLE users ADD COLUMN IF NOT EXISTS on_board BOOLEAN NOT NULL DEFAULT TRUE;
CREATE INDEX IF NOT EXISTS idx_unlocks_memory ON unlocks(memory_id);
