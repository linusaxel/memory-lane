-- Every chunk's raw model reply, committed as it lands, keyed on the exact
-- request. A retry, a re-merge or a crashed run reads it back instead of
-- paying again; a prompt edit misses. See pipeline/extract.py:extract_chunk_stored.
--
--   docker compose exec -T db psql -U memorylane -d memorylane -v ON_ERROR_STOP=1 \
--     < db/migrations/017_extraction_chunks.sql

CREATE TABLE IF NOT EXISTS extraction_chunks (
    request_hash CHAR(64) PRIMARY KEY,
    content_id INTEGER NOT NULL REFERENCES content(id) ON DELETE CASCADE,
    chunk_index INTEGER NOT NULL,
    prompt_hash CHAR(64) NOT NULL,
    model VARCHAR(100) NOT NULL,
    response TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_extraction_chunks_content ON extraction_chunks(content_id);
