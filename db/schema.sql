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
    geocoded_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- A person, as far as this product needs one: a name to sign a submission with.
-- No password column and never one - sign-in is Google and Apple only, and it
-- hangs off `identities` rather than replacing this table. The device id stays
-- the only credential. See docs/10-decisions.md#identity.
CREATE TABLE users (
    id UUID PRIMARY KEY,
    -- Nullable: contributing without being named is allowed, and the API
    -- renders those "Anonymous".
    display_name VARCHAR(60),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- How a person proves they are the same person on a new phone. Google and
-- Apple only: no passwords to store, reset or leak, and Apple is required by
-- App Store review once any other third-party sign-in exists.
--
-- No session tokens anywhere. The device id stays the only credential; signing
-- in binds devices.user_id, so a second phone is a second device on one user.
CREATE TABLE identities (
    provider VARCHAR(10) NOT NULL CHECK (provider IN ('google', 'apple')),
    -- The provider's stable id for the account. Not an email, and not to be
    -- treated as one.
    subject VARCHAR(255) NOT NULL,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    -- Recorded, never used to match. Linking two identities because they share
    -- an address is the classic account takeover.
    email VARCHAR(320),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (provider, subject)
);

CREATE INDEX idx_identities_user ON identities(user_id);

CREATE TABLE memories (
    id SERIAL PRIMARY KEY,
    place_id INTEGER NOT NULL REFERENCES places(id) ON DELETE CASCADE,
    content_id INTEGER REFERENCES content(id) ON DELETE CASCADE,
    -- Seconds into the recording. Null for a memory somebody filed themselves
    -- (it came from a person standing there, not from an offset) and null for
    -- an archival source, which has no recording to be an offset into.
    -- api.gate.source_link decides what that means for a link.
    timestamp_start REAL,
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
    contrast_note TEXT,

    -- A memory nobody may read until this date, including whoever filed it.
    -- Null for everything that opens on arrival, which is almost everything.
    -- Enforced in api/gate.py ahead of the proximity check, so standing on the
    -- spot does not open it and neither does having it in your collection.
    opens_at DATE,

    -- Who filed it, when a person did. Null for everything extracted.
    user_id UUID REFERENCES users(id) ON DELETE SET NULL,

    -- Set when enough people report it. A column rather than a delete: a
    -- takedown that destroys the evidence makes the next dispute
    -- unanswerable. Every query that can emit a summary honours it.
    hidden BOOLEAN NOT NULL DEFAULT FALSE,

    -- The searchable text of this memory AND the name of the place it is
    -- filed at, stored rather than computed. An expression spanning two
    -- tables cannot be indexed, so search was a sequential scan over the
    -- whole corpus; splitting the predicate per table would have indexed it
    -- and quietly stopped matching queries whose words straddle the two.
    -- Maintained by triggers on both tables - see db/migrations/010.
    search_vector tsvector
);

-- Who has earned what. No accounts: a device claims an opaque UUID it generated
-- itself, which is enough to make a collection durable and to give a future
-- sign-in something to attach to, and not enough to identify anybody.
CREATE TABLE devices (
    id UUID PRIMARY KEY,
    -- One device, one user. The column is here and not the other way round
    -- because a person will eventually have several devices, and this is the
    -- side that has to change when they do.
    user_id UUID REFERENCES users(id) ON DELETE SET NULL,
    first_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE unlocks (
    device_id UUID NOT NULL REFERENCES devices(id) ON DELETE CASCADE,
    memory_id INTEGER NOT NULL REFERENCES memories(id) ON DELETE CASCADE,
    unlocked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    -- Unlocking twice must not move the date: the first time is the earned one.
    PRIMARY KEY (device_id, memory_id)
);

CREATE INDEX idx_unlocks_device ON unlocks(device_id, unlocked_at DESC);

-- A photo or a recording attached to a submitted memory. A memory of a place is
-- a thin thing in text alone.
CREATE TABLE media (
    id SERIAL PRIMARY KEY,
    -- Null between the upload and the submission it belongs to, and for ever
    -- if nobody ever posts it. `python -m pipeline.sweep` is the reaper;
    -- ponytail: it is run by hand, because there is no scheduler here to hang
    -- it on. Until something calls it, an abandoned upload still costs disk -
    -- it is just now a command away rather than a rewrite away.
    memory_id INTEGER REFERENCES memories(id) ON DELETE CASCADE,
    -- Who uploaded it, so a submission cannot attach somebody else's file.
    device_id UUID REFERENCES devices(id) ON DELETE SET NULL,
    kind VARCHAR(10) NOT NULL CHECK (kind IN ('photo', 'audio')),
    -- Relative to MEDIA_DIR, and generated by the server. A client filename
    -- never reaches the filesystem.
    path VARCHAR(255) NOT NULL,
    mime VARCHAR(80) NOT NULL,
    bytes INTEGER NOT NULL,
    duration_seconds REAL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_media_memory ON media(memory_id);

-- What makes public submissions defensible. Anything anyone can post needs a
-- way to take it down.
CREATE TABLE reports (
    memory_id INTEGER NOT NULL REFERENCES memories(id) ON DELETE CASCADE,
    device_id UUID NOT NULL REFERENCES devices(id) ON DELETE CASCADE,
    reason VARCHAR(40),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    -- One per device, so the auto-hide threshold counts people not presses.
    PRIMARY KEY (memory_id, device_id)
);

CREATE INDEX idx_memories_place ON memories(place_id);
CREATE INDEX idx_memories_search ON memories USING GIN (search_vector);
CREATE INDEX idx_memories_user ON memories(user_id);
-- MY_DEVICES runs on every /v1/unlocks and every /v1/me.
CREATE INDEX idx_devices_user ON devices(user_id);
CREATE INDEX idx_memories_content ON memories(content_id);
CREATE INDEX idx_places_coordinates ON places USING GIST(coordinates);
-- The gate's uniqueness question, which is asked once per row returned and
-- scanned every place in the table without this. See db/migrations/011 for the
-- measurement; the expression must match api/queries.py's exactly.
CREATE INDEX idx_places_grid ON places (ST_SnapToGrid(coordinates::geometry, 0.0001));
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

-- Search. One definition of a memory's searchable text, used by the trigger
-- that maintains it and by db/migrations/010's backfill. See that file for why
-- this is a stored column rather than an expression index.
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

CREATE TRIGGER memories_search_vector_trg
    BEFORE INSERT OR UPDATE OF summary, place_id ON memories
    FOR EACH ROW
    EXECUTE FUNCTION memories_refresh_search_vector();

-- Without this half, a renamed place answers to its old name for ever.
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

CREATE TRIGGER places_search_vector_trg
    AFTER UPDATE OF name ON places
    FOR EACH ROW
    WHEN (OLD.name IS DISTINCT FROM NEW.name)
    EXECUTE FUNCTION places_refresh_memory_search_vectors();
