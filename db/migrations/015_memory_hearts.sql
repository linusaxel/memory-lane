-- Heart/favorite a memory: say this one mattered.
--
-- One-way, like unlocks and reports: no un-hearting, no DELETE endpoint. A
-- join table rather than a counter column on memories, same reasoning as
-- unlocks - a counter lets one device inflate a count by re-hearting; the
-- composite PK makes a repeat POST a no-op instead.
--
-- Indexed by memory_id, not device_id like unlocks: every read here is
-- "count for this memory," never "this device's hearts."
--
--   docker compose exec -T db psql -U memorylane -d memorylane -v ON_ERROR_STOP=1 \
--     < db/migrations/015_memory_hearts.sql

CREATE TABLE IF NOT EXISTS memory_hearts (
    device_id UUID NOT NULL REFERENCES devices(id) ON DELETE CASCADE,
    memory_id INTEGER NOT NULL REFERENCES memories(id) ON DELETE CASCADE,
    hearted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    -- Hearting twice is not an error and stays one heart - the first time is
    -- the one that counts.
    PRIMARY KEY (device_id, memory_id)
);

CREATE INDEX IF NOT EXISTS idx_memory_hearts_memory ON memory_hearts(memory_id);
