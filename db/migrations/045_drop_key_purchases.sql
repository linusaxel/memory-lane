-- The key packs' history. Production never sold one, so there is nothing to
-- keep (docs/10-decisions.md#the-schema-keeps-only-what-is-read).
--
--   docker compose exec -T db psql -U memorylane -d memorylane -v ON_ERROR_STOP=1 \
--     < db/migrations/045_drop_key_purchases.sql

DROP TABLE IF EXISTS key_purchases;
