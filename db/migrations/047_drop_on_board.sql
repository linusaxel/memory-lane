-- The city board is gone (docs/10-decisions.md#a-city-board-by-opens), and
-- with it the switch that left it.
--
--   docker compose exec -T db psql -U memorylane -d memorylane -v ON_ERROR_STOP=1 \
--     < db/migrations/047_drop_on_board.sql

ALTER TABLE users DROP COLUMN IF EXISTS on_board;
