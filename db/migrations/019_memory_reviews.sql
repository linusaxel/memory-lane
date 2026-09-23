-- A person's verdict on an extracted memory: accept, edit (a before/after
-- pair) or reject. The known-good set, and the edit rate over time. SET NULL
-- rather than CASCADE so reprocessing a video keeps the reviews.
-- See pipeline/review.py.
--
--   docker compose exec -T db psql -U memorylane -d memorylane -v ON_ERROR_STOP=1 \
--     < db/migrations/019_memory_reviews.sql

CREATE TABLE IF NOT EXISTS memory_reviews (
    id SERIAL PRIMARY KEY,
    memory_id INTEGER UNIQUE REFERENCES memories(id) ON DELETE SET NULL,
    content_id INTEGER REFERENCES content(id) ON DELETE SET NULL,
    verdict VARCHAR(10) NOT NULL CHECK (verdict IN ('accept', 'edit', 'reject')),
    before TEXT NOT NULL,
    after TEXT,
    extracted_at TIMESTAMP,
    reviewed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
