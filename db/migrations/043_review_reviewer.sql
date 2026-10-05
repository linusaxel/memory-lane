-- Who gave the verdict: a person or an agent. The judge is tuned on agent
-- labels; the few-shot retrieval and its check want a person's. Every row so
-- far is an agent's (the place test's rejects).
--
--   docker compose exec -T db psql -U memorylane -d memorylane -v ON_ERROR_STOP=1 \
--     < db/migrations/043_review_reviewer.sql

ALTER TABLE memory_reviews ADD COLUMN IF NOT EXISTS reviewer VARCHAR(10) NOT NULL DEFAULT 'agent'
    CHECK (reviewer IN ('person', 'agent'));
