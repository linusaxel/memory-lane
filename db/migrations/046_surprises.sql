-- A surprise: one memory opened off a walk, for half an hour, once a week
-- (docs/10-decisions.md#a-surprise-once-a-week).
--
--   docker compose exec -T db psql -U memorylane -d memorylane -v ON_ERROR_STOP=1 \
--     < db/migrations/046_surprises.sql

CREATE TABLE IF NOT EXISTS surprises (
    id SERIAL PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    memory_id INTEGER NOT NULL REFERENCES memories(id) ON DELETE CASCADE,
    granted_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_surprises_user ON surprises (user_id, granted_at DESC);
