-- Sign in with Google or Apple, and nothing else.
--
-- No passwords, so there is nothing to store, reset or leak. Apple is not a
-- preference: App Store review requires Sign in with Apple as soon as any other
-- third-party sign-in exists on iOS.
--
-- A separate table rather than two columns on users, because one person having
-- both is the normal case here and not a hypothetical - an iPhone user offered
-- Google will often also have tapped Apple once.
--
-- Note what is NOT here: no session tokens, no refresh tokens, no password
-- hashes. The device id the app already sends stays the only credential;
-- signing in binds devices.user_id, so a second phone becomes a second device
-- on the same user and the collection follows the person instead of the handset.
--
--   docker compose exec -T db psql -U memorylane -d memorylane -v ON_ERROR_STOP=1 \
--     < db/migrations/006_identities.sql

CREATE TABLE IF NOT EXISTS identities (
    provider VARCHAR(10) NOT NULL CHECK (provider IN ('google', 'apple')),
    -- The provider's stable id for this account. Apple's is per-app and Google's
    -- is per-account; neither is an email and neither should be treated as one.
    subject VARCHAR(255) NOT NULL,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    -- Recorded, never used to match. Linking two identities because they share
    -- an address is the classic account-takeover: an address can be reassigned,
    -- and Apple's may be a relay that forwards somewhere we cannot see.
    email VARCHAR(320),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (provider, subject)
);

CREATE INDEX IF NOT EXISTS idx_identities_user ON identities(user_id);
