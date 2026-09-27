-- Where memories come from, as rows: the candidates, the rejects and why, and
-- the ones polled. Replaces config/content.yaml and the candidate lists in
-- TODO.md. See docs/10-decisions.md#sources-are-rows-with-a-status.
--
--   docker compose exec -T db psql -U memorylane -d memorylane -v ON_ERROR_STOP=1 \
--     < db/migrations/029_sources.sql

CREATE TABLE IF NOT EXISTS sources (
    id SERIAL PRIMARY KEY,
    kind VARCHAR(20) NOT NULL
        CHECK (kind IN ('youtube_channel', 'text', 'book', 'podcast_feed', 'institution')),
    -- youtube_channel: https://www.youtube.com/channel/<id>, never an @handle,
    -- so a search hit and a hand-added row dedup. text and book:
    -- "<crawler.sources key>:<query>".
    locator VARCHAR(1024) UNIQUE NOT NULL,
    name VARCHAR(255) NOT NULL,
    language VARCHAR(10),
    city VARCHAR(40) NOT NULL DEFAULT 'copenhagen',
    -- candidate: found, nothing spent. trial: one item extracted by hand.
    -- active: ingest polls it. candidate and rejected are never extracted in
    -- bulk (PENDING_EXTRACTION).
    status VARCHAR(12) NOT NULL DEFAULT 'candidate'
        CHECK (status IN ('candidate', 'trial', 'active', 'paused', 'rejected')),
    note TEXT,
    licence VARCHAR(40),
    found_via VARCHAR(255) NOT NULL DEFAULT 'human',
    poll_limit INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

ALTER TABLE content ADD COLUMN IF NOT EXISTS source_id INTEGER REFERENCES sources(id) ON DELETE SET NULL;
CREATE INDEX IF NOT EXISTS idx_content_source ON content(source_id);

-- The promote-or-reject number. `screened` is the Haiku pass rate, which is
-- known before a cent goes to Sonnet; fail-open verdicts are not judgements.
CREATE OR REPLACE VIEW source_yield AS
SELECT s.id, s.name, s.kind, s.status,
       c.items, c.extracted, c.hours_extracted, m.memories,
       round(m.memories / NULLIF(c.hours_extracted, 0), 1) AS memories_per_hour,
       v.screened
FROM sources s
LEFT JOIN LATERAL (
    -- A hand-added video has no duration; its last caption is near enough.
    SELECT count(*) AS items,
           count(*) FILTER (WHERE memories_extracted) AS extracted,
           round(sum(coalesce(duration_seconds, (t.segments->-1->>'start')::numeric))
                 FILTER (WHERE memories_extracted AND source_type = 'video') / 3600.0, 1)
               AS hours_extracted
    FROM content LEFT JOIN transcripts t ON t.content_id = content.id
    WHERE source_id = s.id
) c ON TRUE
LEFT JOIN LATERAL (
    SELECT count(*) AS memories
    FROM memories JOIN content ON content.id = memories.content_id
    WHERE content.source_id = s.id AND NOT memories.hidden
) m ON TRUE
LEFT JOIN LATERAL (
    SELECT round(avg(v.has_memories::int), 2) AS screened
    FROM classifier_verdicts v JOIN content ON content.id = v.content_id
    WHERE content.source_id = s.id AND v.reason NOT LIKE 'fail-open: %'
) v ON TRUE
-- The app's own people, as one row to hold every other source against.
UNION ALL
SELECT NULL, 'People, in the app', 'people', 'active', NULL, NULL, NULL, count(*), NULL, NULL
FROM memories WHERE user_id IS NOT NULL AND NOT hidden;

INSERT INTO sources (kind, locator, name, language, status, poll_limit, licence, note) VALUES
    ('youtube_channel', 'https://www.youtube.com/channel/UCsE74YJvPJpaquzTPMO8hAA',
     'Tuesdays with Stories', 'en', 'active', 25, NULL,
     'Comedians telling their own stories about named spots. The benchmark.'),
    ('youtube_channel', 'https://www.youtube.com/channel/UCCFj7xrd0DOIuG_NjC4NWhg',
     'Københavnerliv', 'da', 'trial', NULL, NULL,
     'Owners and regulars telling stories about their own pub or shop.'),
    ('youtube_channel', 'https://www.youtube.com/channel/UChECi5hBPRvzcbR9Ws2Lytw',
     'Københavnerglimt', 'da', 'candidate', NULL, NULL,
     'A historian walks each district. Most places per minute, but history, not memory.'),
    ('youtube_channel', 'https://www.youtube.com/channel/UCheihgOocMv9oxvarD3x5Lg',
     'Fantino & Bonde', 'da', 'candidate', NULL, NULL,
     'Comedians at one named hot-dog stand or pub per episode.'),
    ('youtube_channel', 'https://www.youtube.com/channel/UC_qkc7yR9vGqI-tbHDTJ9fQ',
     'Erin in Copenhagen', 'en', 'candidate', NULL, NULL,
     'A spot per video; dormant since 2023.'),
    ('youtube_channel', 'https://www.youtube.com/channel/UCPT_rwsYQ67F1CO_pJhEu5Q',
     'What Are You Doing in Denmark?', 'en', 'candidate', NULL, NULL,
     'Expat comedians'' stories, few named spots.'),
    ('youtube_channel', 'https://www.youtube.com/channel/UCzEQ47zTuaY-NshfJK6YwnQ',
     'Christiania1', 'da', 'candidate', NULL, NULL,
     'Residents'' memories; Christiania only.'),
    ('youtube_channel', 'https://www.youtube.com/channel/UCkLidpONkXfGcYtZKFIYedw',
     'How to Live in Denmark', 'en', 'candidate', NULL, NULL,
     'The "On the Road" episodes.'),
    ('text', 'kb-aviser:', 'KB Labs / Mediestream', 'da', 'trial', NULL, 'public domain',
     'Newspapers over 140 years old, searched by street. Rough Fraktur OCR.'),
    ('text', 'historisk-atlas:', 'Historisk Atlas', 'da', 'trial', NULL, 'ask first',
     'Title and intro only until they grant API access (it@historiskatlas.dk).'),
    ('book', 'gutenberg:3529 Copenhagen', 'Mary Wollstonecraft, Letters (1796)',
     'en', 'candidate', NULL, 'public domain',
     'Letters Written in Sweden, Norway, and Denmark: Copenhagen just after the 1795 fire.'),
    ('book', 'ditlevsen:copenhagen-trilogy', 'The Copenhagen Trilogy', 'da', 'paused', NULL,
     'ask first', 'Tove Ditlevsen. In copyright until 2046: a publisher licence or nothing.'),
    ('institution', 'https://kbhbilleder.dk', 'kbhbilleder', 'da', 'candidate', NULL,
     'ask first', '41,779 photos, ~5,000 out of copyright. Bot-protected: ask, never scrape.'),
    ('institution', 'https://arkiv.dk', 'arkiv.dk', 'da', 'paused', NULL, 'unknown',
     '550+ archives, no public API. Institutional conversation only.'),
    ('institution', 'https://www.dr.dk', 'DR podcasts', 'da', 'rejected', NULL, 'no',
     'DR''s terms reserve text and data mining.'),
    ('institution', 'https://www.reddit.com', 'Reddit', NULL, 'rejected', NULL, 'no',
     'Commercial and AI use need a contract.'),
    ('institution', 'https://www.setlist.fm', 'setlist.fm', NULL, 'rejected', NULL,
     'non-commercial', 'Commercial use means asking Live Nation. Revisit with a licence.'),
    ('institution', 'https://indenforvoldene.dk', 'indenforvoldene.dk', 'da', 'rejected', NULL,
     'no', 'One author, all rights reserved.')
ON CONFLICT (locator) DO NOTHING;

UPDATE content SET source_id = s.id
FROM sources s
WHERE content.source_id IS NULL AND content.source_name = s.name;
