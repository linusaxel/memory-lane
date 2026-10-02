-- Keys open memories: one per walk finished a day, or bought. A balance on
-- the account, and every store purchase credited once by its transaction id
-- (docs/10-decisions.md#keys-open-a-lock-and-todays-walk-is-free).
--
--   docker compose exec -T db psql -U memorylane -d memorylane -v ON_ERROR_STOP=1 \
--     < db/migrations/037_keys.sql

-- users.keys was added here; 038_xp_not_keys.sql drops it again.

CREATE TABLE IF NOT EXISTS key_purchases (
    transaction_id TEXT PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    keys INTEGER NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
