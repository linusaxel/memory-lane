-- A memory's fact sheet: who, what, when, where, each claim with its quote,
-- and the excerpt the card is written from. One row per extraction, never
-- overwritten; the newest is current (docs/10-decisions.md#a-card-is-rendered-from-its-fact-sheet).
--
--   docker compose exec -T db psql -U memorylane -d memorylane -v ON_ERROR_STOP=1 \
--     < db/migrations/051_memory_sheets.sql

CREATE TABLE IF NOT EXISTS memory_sheets (
    id SERIAL PRIMARY KEY,
    memory_id INTEGER NOT NULL REFERENCES memories(id) ON DELETE CASCADE,
    content_id INTEGER REFERENCES content(id) ON DELETE CASCADE,
    sheet JSONB COMPRESSION lz4 NOT NULL CHECK (sheet ? 'schema_version'),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_memory_sheets_memory ON memory_sheets (memory_id);
