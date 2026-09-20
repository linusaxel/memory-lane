CREATE EXTENSION IF NOT EXISTS postgis;

CREATE TABLE content (
    id SERIAL PRIMARY KEY,
    url VARCHAR(1024) UNIQUE NOT NULL,
    platform VARCHAR(50) NOT NULL,
    platform_id VARCHAR(255),
    -- Not CHECKed: the set grows with every source we ingest (archive,
    -- newspaper, registry, oral_history), unlike memories.layer which is
    -- closed. 'video' rows are the only ones with a transcript.
    source_type VARCHAR(20) NOT NULL DEFAULT 'video',
    -- Who published this, not what it is: the channel, paper or archive. A
    -- memory without it is an anonymous assertion, and the channel is also the
    -- only reliable answer to "who is the speaker" when the transcript never
    -- says. source_url is the channel; memories.source_url is the item.
    source_name VARCHAR(255),
    source_url VARCHAR(1024),
    source_icon_url VARCHAR(1024),
    title VARCHAR(512),
    published_at TIMESTAMP,
    transcript_fetched BOOLEAN DEFAULT FALSE,
    transcript_failed BOOLEAN DEFAULT FALSE,
    memories_extracted BOOLEAN DEFAULT FALSE,
    extraction_failed BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE transcripts (
    id SERIAL PRIMARY KEY,
    content_id INTEGER UNIQUE REFERENCES content(id) ON DELETE CASCADE,
    segments JSONB NOT NULL,
    full_text TEXT,
    language VARCHAR(10),
    fetched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE places (
    id SERIAL PRIMARY KEY,
    name VARCHAR(512) NOT NULL,
    place_query VARCHAR(512) NOT NULL,
    coordinates GEOGRAPHY(POINT, 4326),
    precision_meters INTEGER DEFAULT 200,
    geocode_status VARCHAR(20) DEFAULT 'pending',
    geocode_response JSONB,
    geocoded_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE memories (
    id SERIAL PRIMARY KEY,
    place_id INTEGER NOT NULL REFERENCES places(id) ON DELETE CASCADE,
    content_id INTEGER NOT NULL REFERENCES content(id) ON DELETE CASCADE,
    timestamp_start REAL NOT NULL,
    timestamp_end REAL,
    summary TEXT NOT NULL,
    tags VARCHAR(50)[],
    extraction_confidence VARCHAR(20),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    -- Which of the three content layers this belongs to. The layers render
    -- differently and must never appear at equal weight in one feed: friend
    -- memories are intimate and ephemeral, historical cards public and
    -- permanent. CHECKed because the set is closed and the product rules
    -- depend on it; a typo here silently hides content.
    layer VARCHAR(20) NOT NULL DEFAULT 'historical'
        CHECK (layer IN ('historical', 'friend', 'stranger')),

    -- WHEN it happened, as opposed to timestamp_start, which is where it sits
    -- in a video. A 1978 gig needs somewhere to record 1978. Null when the
    -- source does not say; precision records how much of the date to trust.
    happened_at DATE,
    happened_precision VARCHAR(10)
        CHECK (happened_precision IN ('day', 'month', 'year', 'decade')),

    -- Per-memory credit and a deep link back to the source. Not derivable from
    -- the content join: one archive record can carry its own attribution, and
    -- the card must show it even when pasted into a group chat.
    attribution TEXT,
    source_url TEXT,

    -- The gap between this memory and what the user is looking at now. Scored
    -- once at extraction and never recomputed - extraction is a one-time cost
    -- per place, amortized across everyone who stands there.
    contrast_score REAL,
    contrast_note TEXT
);

-- Indexes
CREATE INDEX idx_memories_place ON memories(place_id);
CREATE INDEX idx_memories_content ON memories(content_id);
CREATE INDEX idx_places_coordinates ON places USING GIST(coordinates);
-- The ON CONFLICT (place_query) in pipeline/extract.py needs this to fire. Without
-- it the clause is a silent no-op and every memory mints a duplicate place. Keep it
-- on the bare column: extract.py's fallback SELECT matches on place_query exactly,
-- and an expression index it cannot match means place_id comes back NULL and the
-- memory is dropped. Existing databases: db/migrations/001_places_unique.sql.
CREATE UNIQUE INDEX idx_places_place_query ON places(place_query);
CREATE INDEX idx_places_geocode_status ON places(geocode_status);
CREATE INDEX idx_content_platform ON content(platform);
CREATE INDEX idx_content_pending_transcript ON content(transcript_fetched) WHERE transcript_fetched = FALSE AND transcript_failed = FALSE;
CREATE INDEX idx_content_pending_extraction ON content(memories_extracted) WHERE memories_extracted = FALSE AND extraction_failed = FALSE AND transcript_fetched = TRUE;

-- Trigger for updated_at
CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER content_updated_at
    BEFORE UPDATE ON content
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at();
