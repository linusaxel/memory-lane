-- Who has paid, and until when. On the account, not the device, so a second
-- phone is covered. A subscriber can open any memory they stand on without a
-- walk, and take more than one walk a day - see
-- docs/10-decisions.md#a-subscription-opens-the-map. Nothing writes it yet: the
-- store webhook that will is TODO.md S3.
--
--   docker compose exec -T db psql -U memorylane -d memorylane -v ON_ERROR_STOP=1 \
--     < db/migrations/028_subscriptions.sql

CREATE TABLE IF NOT EXISTS subscriptions (
    user_id UUID PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
    expires_at TIMESTAMP NOT NULL
);
