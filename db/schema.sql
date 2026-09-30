CREATE EXTENSION IF NOT EXISTS postgis;

-- Where memories come from, as rows. See
-- docs/10-decisions.md#sources-are-rows-with-a-status.
CREATE TABLE sources (
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
    -- From the channel listing; null for hand-listed videos. Anything shorter
    -- than MIN_VIDEO_MINUTES is a clip and is never transcribed or extracted.
    duration_seconds INTEGER,
    source_id INTEGER REFERENCES sources(id) ON DELETE SET NULL,
    transcript_fetched BOOLEAN DEFAULT FALSE,
    transcript_failed BOOLEAN DEFAULT FALSE,
    memories_extracted BOOLEAN DEFAULT FALSE,
    extraction_failed BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_content_source ON content(source_id);

CREATE TABLE transcripts (
    id SERIAL PRIMARY KEY,
    content_id INTEGER UNIQUE REFERENCES content(id) ON DELETE CASCADE,
    segments JSONB NOT NULL,
    full_text TEXT,
    language VARCHAR(10),
    fetched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Every chunk's raw model reply, so nothing is paid for twice. See
-- pipeline/extract.py:extract_chunk_stored.
CREATE TABLE extraction_chunks (
    request_hash CHAR(64) PRIMARY KEY,
    content_id INTEGER NOT NULL REFERENCES content(id) ON DELETE CASCADE,
    chunk_index INTEGER NOT NULL,
    prompt_hash CHAR(64) NOT NULL,
    model VARCHAR(100) NOT NULL,
    response TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_extraction_chunks_content ON extraction_chunks(content_id);

-- What the Haiku pre-filter decided about each chunk, and why. A rejection is
-- otherwise invisible. See pipeline/classifier_audit.py.
CREATE TABLE classifier_verdicts (
    content_id INTEGER NOT NULL REFERENCES content(id) ON DELETE CASCADE,
    chunk_index INTEGER NOT NULL,
    model VARCHAR(100) NOT NULL,
    has_memories BOOLEAN NOT NULL,
    reason TEXT,
    chunk_text TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (content_id, chunk_index, model)
);

CREATE TABLE places (
    id SERIAL PRIMARY KEY,
    name VARCHAR(512) NOT NULL,
    place_query VARCHAR(512) NOT NULL,
    -- Structured identity, W4-02. Nullable: rows written before this existed,
    -- and any place_query synthesized by api/write.py for a human submission,
    -- have none. save_memories keys the ON CONFLICT on these when present,
    -- falling back to place_query only when they are not. See
    -- idx_places_venue_locality below.
    venue VARCHAR(255),
    locality VARCHAR(255),
    region VARCHAR(255),
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

    -- Claims its chunk doesn't make, for review; never edited in. NULL is
    -- never checked, {} is clean (migration 031).
    unsupported TEXT[],

    -- Unused since 2026-09-26: the time capsule was removed and every memory
    -- is public (docs/10, "Every memory is public"). Kept so migration 009
    -- still replays against this schema.
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

-- Say this one mattered. One-way like unlocks: no un-hearting. A join table
-- rather than a counter column on memories, so one device can't inflate a
-- count by re-hearting. See db/migrations/015_memory_hearts.sql.
CREATE TABLE memory_hearts (
    device_id UUID NOT NULL REFERENCES devices(id) ON DELETE CASCADE,
    memory_id INTEGER NOT NULL REFERENCES memories(id) ON DELETE CASCADE,
    hearted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (device_id, memory_id)
);

-- Every read here is "count for this memory," never "this device's hearts" -
-- the opposite of idx_unlocks_device above.
CREATE INDEX idx_memory_hearts_memory ON memory_hearts(memory_id);

-- A note on a memory, one per device, only from a device that unlocked it. `id`
-- so a note can be named without naming its device. See
-- db/migrations/026_memory_notes.sql.
CREATE TABLE memory_notes (
    id SERIAL PRIMARY KEY,
    device_id UUID NOT NULL REFERENCES devices(id) ON DELETE CASCADE,
    memory_id INTEGER NOT NULL REFERENCES memories(id) ON DELETE CASCADE,
    body VARCHAR(280) NOT NULL,
    hidden BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (device_id, memory_id)
);

CREATE INDEX idx_memory_notes_memory ON memory_notes(memory_id);

-- Today's route: a fixed set of nearby, not-yet-earned stops, computed once
-- per device per calendar day and stored so a relaunch sees the same route
-- rather than a fresh roll of the dice. The first calendar-day-keyed table
-- here - SPENT_TODAY/FILED_TODAY (api/write.py) are rolling 24h windows, not
-- stored rows, which cannot give a route the stability a reopen needs.
-- memory_ids is an array, not a child table: it preserves stop order natively
-- for at most a handful of ids. See db/migrations/013_daily_routes.sql.
-- budget_meters is the walk length the device asked for when it accepted the
-- route - see db/migrations/022_route_budget.sql. legs is the street shape between
-- consecutive stops, null without a routing sidecar - see 021_route_legs.sql.
-- completed_at is set once, by the unlock that earns the last stop - see 024.
-- loop is whether the walk comes back to its start, chosen per walk - see 025.
-- ended_at is set by "End walk"; one walk in progress per device per day - see 027.
CREATE TABLE daily_routes (
    id SERIAL PRIMARY KEY,
    device_id UUID NOT NULL REFERENCES devices(id) ON DELETE CASCADE,
    route_date DATE NOT NULL,
    memory_ids INTEGER[] NOT NULL,
    budget_meters INTEGER NOT NULL DEFAULT 4000,
    legs JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP,
    loop BOOLEAN NOT NULL DEFAULT TRUE,
    ended_at TIMESTAMP
);
CREATE UNIQUE INDEX daily_routes_in_progress
    ON daily_routes (device_id, route_date) WHERE ended_at IS NULL;

-- Who has paid, and until when: on the account, so every device of it is
-- covered. See db/migrations/028_subscriptions.sql.
CREATE TABLE subscriptions (
    user_id UUID PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
    expires_at TIMESTAMP NOT NULL
);

-- An authored walk, served by GET /v1/routes/{id} once published. A join
-- table here, unlike daily_routes: it is long-lived, ordered and edited. See
-- db/migrations/023_authored_routes.sql.
CREATE TABLE routes (
    id SERIAL PRIMARY KEY,
    title VARCHAR(200) NOT NULL,
    status VARCHAR(10) NOT NULL DEFAULT 'draft' CHECK (status IN ('draft', 'published')),
    is_loop BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE route_stops (
    route_id INTEGER NOT NULL REFERENCES routes(id) ON DELETE CASCADE,
    position INTEGER NOT NULL,
    memory_id INTEGER NOT NULL REFERENCES memories(id) ON DELETE CASCADE,
    PRIMARY KEY (route_id, position),
    UNIQUE (route_id, memory_id)
);

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
    -- Set when a reviewer reinstates the memory: kept as evidence, no longer
    -- counted. db/migrations/030_moderation.sql.
    cleared_at TIMESTAMP,
    -- One per device; the threshold counts the accounts behind them.
    PRIMARY KEY (memory_id, device_id)
);

-- Someone this device's account never wants to read again (App Store 1.2).
CREATE TABLE blocks (
    device_id UUID NOT NULL REFERENCES devices(id) ON DELETE CASCADE,
    blocked_user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (device_id, blocked_user_id)
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
-- Structured-field identity, W4-02: an exact match on venue+locality once
-- extraction supplies them, so two mentions of the same real place collide at
-- insert time instead of needing pipeline/dedup.py's string heuristic, which
-- cannot tell two venues on the same street apart. Partial: legacy rows have
-- NULL in both columns and never match here. See
-- db/migrations/016_structured_place_fields.sql.
CREATE UNIQUE INDEX idx_places_venue_locality
    ON places (lower(btrim(venue)), lower(btrim(locality)))
    WHERE venue IS NOT NULL AND locality IS NOT NULL;
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

-- A person's verdict on an extracted memory: the known-good set, and the edit
-- rate that says whether a prompt change helped. SET NULL, not CASCADE, so
-- reprocessing a video keeps the reviews. See pipeline/review.py.
CREATE TABLE memory_reviews (
    id SERIAL PRIMARY KEY,
    memory_id INTEGER UNIQUE REFERENCES memories(id) ON DELETE SET NULL,
    content_id INTEGER REFERENCES content(id) ON DELETE SET NULL,
    verdict VARCHAR(10) NOT NULL CHECK (verdict IN ('accept', 'edit', 'reject')),
    before TEXT NOT NULL,
    after TEXT,
    extracted_at TIMESTAMP,
    reviewed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- The promote-or-reject number. `screened` is the Haiku pass rate, which is
-- known before a cent goes to Sonnet; fail-open verdicts are not judgements.
CREATE VIEW source_yield AS
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

-- Which db/migrations/ files this database has. Written by pipeline/migrate.py.
CREATE TABLE schema_migrations (
    name TEXT PRIMARY KEY,
    applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
