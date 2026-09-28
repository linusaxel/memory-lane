-- App Store 1.2: block a person, and a report that a reviewer can clear. See
-- docs/10-decisions.md#posts-are-screened-reports-need-an-account.
--
--   docker compose exec -T db psql -U memorylane -d memorylane -v ON_ERROR_STOP=1 \
--     < db/migrations/030_moderation.sql

-- Keyed on the blocker's device, like unlocks, and read across its account.
CREATE TABLE IF NOT EXISTS blocks (
    device_id UUID NOT NULL REFERENCES devices(id) ON DELETE CASCADE,
    blocked_user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (device_id, blocked_user_id)
);

-- Set when a reviewer reinstates the memory: the row stays as evidence and
-- stops counting toward REPORT_THRESHOLD.
ALTER TABLE reports ADD COLUMN IF NOT EXISTS cleared_at TIMESTAMP;
