-- Search could not use an index, and the reason was structural.
--
-- SEARCH_VECTOR was to_tsvector(m.summary || ' ' || p.name) - an expression
-- spanning two tables, which no expression index can cover. Every search was
-- therefore a sequential scan over every memory joined to every place, and it
-- was going to stay that way: `loop/TASKS.yaml`'s inbox says as much.
--
-- The obvious fix - splitting the predicate into an OR of two single-table
-- expressions - is indexable and silently changes what search means. A query
-- whose words straddle the two fields ("cellar heckler", where the place is
-- the Comedy Cellar and the heckler is in the summary) matches the joined
-- vector and matches neither half of the OR. tests/test_api_search.py pins
-- that behaviour on purpose and says in as many words that indexing work has
-- to break it.
--
-- So the vector is materialised instead of recomputed: the same concatenation,
-- stored on the row, maintained by triggers on both sides, and indexed. Search
-- means exactly what it meant before and can now use a GIN index.
--
-- The cost is honest and worth naming: a place rename rewrites the vector of
-- every memory filed there. Renames come from pipeline/dedup.py, in batches a
-- human has reviewed, and touch a handful of rows at a time.

ALTER TABLE memories ADD COLUMN IF NOT EXISTS search_vector tsvector;

-- One definition of what a memory's searchable text is, so the trigger that
-- maintains it and the backfill that seeds it cannot drift apart.
CREATE OR REPLACE FUNCTION memory_search_vector(summary TEXT, place_name TEXT)
RETURNS tsvector
LANGUAGE sql
IMMUTABLE
AS $$
    SELECT to_tsvector('english', summary || ' ' || COALESCE(place_name, ''))
$$;

CREATE OR REPLACE FUNCTION memories_refresh_search_vector()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
    NEW.search_vector := memory_search_vector(
        NEW.summary,
        (SELECT name FROM places WHERE id = NEW.place_id)
    );
    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS memories_search_vector_trg ON memories;
CREATE TRIGGER memories_search_vector_trg
    BEFORE INSERT OR UPDATE OF summary, place_id ON memories
    FOR EACH ROW
    EXECUTE FUNCTION memories_refresh_search_vector();

-- The other half. Without it a renamed place keeps answering to its old name
-- for ever, which is worse than the sequential scan was.
CREATE OR REPLACE FUNCTION places_refresh_memory_search_vectors()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
    UPDATE memories
    SET search_vector = memory_search_vector(summary, NEW.name)
    WHERE place_id = NEW.id;
    RETURN NULL;
END;
$$;

DROP TRIGGER IF EXISTS places_search_vector_trg ON places;
CREATE TRIGGER places_search_vector_trg
    AFTER UPDATE OF name ON places
    FOR EACH ROW
    WHEN (OLD.name IS DISTINCT FROM NEW.name)
    EXECUTE FUNCTION places_refresh_memory_search_vectors();

UPDATE memories m
SET search_vector = memory_search_vector(m.summary, p.name)
FROM places p
WHERE p.id = m.place_id
  AND m.search_vector IS NULL;

CREATE INDEX IF NOT EXISTS idx_memories_search ON memories USING GIN (search_vector);
