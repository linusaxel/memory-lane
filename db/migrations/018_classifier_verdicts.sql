-- What the Haiku pre-filter decided about each chunk, and why. A rejected chunk
-- used to leave no trace, so the filter's misses could not be measured.
-- pipeline/classifier_audit.py re-extracts a sample of rejections.
--
--   docker compose exec -T db psql -U memorylane -d memorylane -v ON_ERROR_STOP=1 \
--     < db/migrations/018_classifier_verdicts.sql

CREATE TABLE IF NOT EXISTS classifier_verdicts (
    content_id INTEGER NOT NULL REFERENCES content(id) ON DELETE CASCADE,
    chunk_index INTEGER NOT NULL,
    model VARCHAR(100) NOT NULL,
    has_memories BOOLEAN NOT NULL,
    reason TEXT,
    chunk_text TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (content_id, chunk_index, model)
);
