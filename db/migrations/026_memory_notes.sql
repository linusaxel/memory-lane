-- A note on a memory: one per device, and only from a device that unlocked it.
-- Standing there is the price of a note, the way buying a record is on
-- Bandcamp - see docs/10-decisions.md#notes-are-gated-like-a-purchase.
--
-- `id` so the app can name a note without naming the device that wrote it: a
-- device UUID is a credential and never leaves its owner.
--
--   docker compose exec -T db psql -U memorylane -d memorylane -v ON_ERROR_STOP=1 \
--     < db/migrations/026_memory_notes.sql

CREATE TABLE IF NOT EXISTS memory_notes (
    id SERIAL PRIMARY KEY,
    device_id UUID NOT NULL REFERENCES devices(id) ON DELETE CASCADE,
    memory_id INTEGER NOT NULL REFERENCES memories(id) ON DELETE CASCADE,
    body VARCHAR(280) NOT NULL,
    -- Taken down by the memory's author. A flag, not a delete, like memories.hidden.
    hidden BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (device_id, memory_id)
);

CREATE INDEX IF NOT EXISTS idx_memory_notes_memory ON memory_notes(memory_id);
