-- The lockets as a table, and every memory keeps its own: one the pipeline
-- files draws one at random, and every memory that had none draws one now
-- (docs/10-decisions.md#lockets-one-per-memory-chosen-by-its-author-earned-by-level).
--
--   docker compose exec -T db psql -U memorylane -d memorylane -v ON_ERROR_STOP=1 \
--     < db/migrations/041_locket_random.sql

CREATE TABLE IF NOT EXISTS lockets (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    level SMALLINT NOT NULL
);
INSERT INTO lockets (id, name, level) VALUES
    ('hunter-compass', 'Hunter compass', 1),
    ('guilloche-oval', 'Guilloché oval', 3),
    ('deco-sunburst', 'Deco sunburst', 5),
    ('monogram-cushion', 'Monogram cushion', 7),
    ('gold-line-night', 'Gold line, night', 9),
    ('victorian-garnet', 'Victorian garnet', 11)
ON CONFLICT (id) DO NOTHING;

CREATE OR REPLACE FUNCTION random_locket() RETURNS TEXT LANGUAGE sql VOLATILE AS
$$ SELECT id FROM lockets ORDER BY random() LIMIT 1 $$;

ALTER TABLE memories ALTER COLUMN locket SET DEFAULT random_locket();
UPDATE memories SET locket = DEFAULT WHERE locket IS NULL;
ALTER TABLE memories ALTER COLUMN locket SET NOT NULL;
DO $$ BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'memories_locket_fkey') THEN
        ALTER TABLE memories ADD CONSTRAINT memories_locket_fkey
            FOREIGN KEY (locket) REFERENCES lockets(id);
    END IF;
END $$;
