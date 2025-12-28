CREATE EXTENSION IF NOT EXISTS postgis;

CREATE TABLE content (
    id SERIAL PRIMARY KEY,
    url VARCHAR(1024) UNIQUE NOT NULL,
    platform VARCHAR(50) NOT NULL,
    platform_id VARCHAR(255),
    source_name VARCHAR(255),
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
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes
CREATE INDEX idx_memories_place ON memories(place_id);
CREATE INDEX idx_memories_content ON memories(content_id);
CREATE INDEX idx_places_coordinates ON places USING GIST(coordinates);
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
