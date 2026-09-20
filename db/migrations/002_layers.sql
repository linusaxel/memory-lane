-- Run ONCE by hand against an existing database:
--   docker compose exec -T db psql -U memorylane -d memorylane -v ON_ERROR_STOP=1 \
--     < db/migrations/002_layers.sql
--
-- Fresh databases get these columns from db/schema.sql instead; the compose mount
-- at docker-entrypoint-initdb.d only runs on first volume init, so an existing
-- volume never sees schema.sql changes.
--
-- Why this exists: the product is three content layers (historical, friend,
-- stranger) ranked by contrast rather than distance, and none of that had
-- anywhere to live. memories could say where a story sits in a video but not
-- when the thing happened, could not carry its own attribution, and had no
-- score to order by. See TODO.md Phase 1.
--
-- Additive only. Every column is nullable or defaulted, so this cannot fail on
-- existing rows and nothing needs backfilling beyond the defaults.
BEGIN;

ALTER TABLE content
    ADD COLUMN IF NOT EXISTS source_type VARCHAR(20) NOT NULL DEFAULT 'video';

ALTER TABLE memories
    ADD COLUMN IF NOT EXISTS layer VARCHAR(20) NOT NULL DEFAULT 'historical',
    ADD COLUMN IF NOT EXISTS happened_at DATE,
    ADD COLUMN IF NOT EXISTS happened_precision VARCHAR(10),
    ADD COLUMN IF NOT EXISTS attribution TEXT,
    ADD COLUMN IF NOT EXISTS source_url TEXT,
    ADD COLUMN IF NOT EXISTS contrast_score REAL,
    ADD COLUMN IF NOT EXISTS contrast_note TEXT;

-- The CHECKs go on separately: ADD COLUMN IF NOT EXISTS carries no constraint
-- when the column already exists, so a half-applied run would otherwise leave
-- the set open. Dropping first makes the whole file re-runnable.
ALTER TABLE memories DROP CONSTRAINT IF EXISTS memories_layer_check;
ALTER TABLE memories ADD CONSTRAINT memories_layer_check
    CHECK (layer IN ('historical', 'friend', 'stranger'));

ALTER TABLE memories DROP CONSTRAINT IF EXISTS memories_happened_precision_check;
ALTER TABLE memories ADD CONSTRAINT memories_happened_precision_check
    CHECK (happened_precision IN ('day', 'month', 'year', 'decade'));

COMMIT;
