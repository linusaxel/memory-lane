-- Unlocks, server-side.
--
-- Until now the only record that somebody had earned a memory lived in that
-- phone's AsyncStorage. Clear the app's data and the walking was undone; the
-- server had no idea any of it had happened.
--
-- No accounts, and deliberately not yet: a device claims an opaque UUID it
-- generated itself. That is enough to make the collection durable and to give a
-- future sign-in something to attach to, and it is not enough to identify
-- anybody, which is the trade this product wants until Phase 3.
--
--   docker compose exec -T db psql -U memorylane -d memorylane -v ON_ERROR_STOP=1 \
--     < db/migrations/004_unlocks.sql

CREATE TABLE IF NOT EXISTS devices (
    -- Generated on the device. The server never issues one, so it never has to
    -- hand an identifier to a client that did not already have it.
    id UUID PRIMARY KEY,
    first_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS unlocks (
    device_id UUID NOT NULL REFERENCES devices(id) ON DELETE CASCADE,
    memory_id INTEGER NOT NULL REFERENCES memories(id) ON DELETE CASCADE,
    unlocked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    -- Unlocking twice is not an error and must not move the date: the first
    -- time is the one that was earned.
    PRIMARY KEY (device_id, memory_id)
);

-- The collection query: everything one device has earned, newest first.
CREATE INDEX IF NOT EXISTS idx_unlocks_device ON unlocks(device_id, unlocked_at DESC);
