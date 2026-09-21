"""Every SQL string the API runs, composed from shared fragments.

Deliberately not a query builder: the moment a function takes a WHERE clause,
somebody passes a variable and you have an injection surface plus a query you
cannot read. Real parameters are always :named binds; the interpolated pieces
are module constants evaluated once at import.

tests/test_api_sql.py EXPLAINs every *_QUERY in here against the real schema.
"""

# Whether this coordinate belongs to this place alone, which is what decides
# whether a memory is worth walking to. The NOT EXISTS is what stops a
# submission unlocking its neighbours. Both rules and the reasons:
# docs/10-decisions.md#the-gate. api/card.py keeps a copy - change both.
# ponytail: a correlated scan of ~200 places per row. Materialize it onto
# places if the corpus ever reaches the tens of thousands.
COORDINATE_IS_UNIQUE = """(
        SELECT COUNT(*) = 1 FROM places p2
        WHERE ST_SnapToGrid(p2.coordinates::geometry, 0.0001)
            = ST_SnapToGrid(p.coordinates::geometry, 0.0001)
          AND NOT EXISTS (
              SELECT 1 FROM memories m2 WHERE m2.place_id = p2.id AND m2.user_id IS NOT NULL
          )
    ) as coordinate_is_unique"""

# COALESCE because json_agg returns SQL NULL for no rows, and a null here would
# make every media-less memory need a guard downstream.
# ponytail: a correlated subquery per row. A LEFT JOIN LATERAL if a page of 100
# ever gets slow.
MEMORY_MEDIA = """COALESCE((
        SELECT json_agg(json_build_object(
                   'id', md.id, 'kind', md.kind, 'path', md.path,
                   'duration_seconds', md.duration_seconds
               ) ORDER BY md.id)
        FROM media md WHERE md.memory_id = m.id
    ), '[]'::json) as media"""

# Something happened here on today's date. Day-and-month, so it fires every year
# rather than once. Carried on every memory-shaped row rather than filtered on,
# because it is a reason to look and never a reason to hide anything.
# ponytail: a 29 February memory resurfaces only on a leap day. Nudging it to
# the 28th is a product decision nobody has made.
# UTC explicitly, not CURRENT_DATE. CURRENT_DATE is whatever timezone the
# cluster happens to be set to, which is one deployment setting away from
# disagreeing with api.gate.today() - and the two together decide whether a
# memory is shut and whether it is "on this day". See api/gate.py#today.
ANNIVERSARY = """(
        m.happened_at IS NOT NULL
        AND to_char(m.happened_at, 'MM-DD')
            = to_char((now() AT TIME ZONE 'utc')::date, 'MM-DD')
    ) as anniversary"""

# Every column a memory-shaped response needs. row_to_memory reads the row by
# name, so a query is free to append distance, rank or unlocked_at.
MEMORY_COLUMNS = f"""
    m.id,
    m.summary,
    m.timestamp_start,
    m.timestamp_end,
    m.tags,
    m.extraction_confidence,
    m.layer,
    m.happened_at,
    m.attribution,
    m.source_url,
    m.contrast_score,
    m.contrast_note,
    m.opens_at,
    {ANNIVERSARY},
    p.id as place_id,
    p.name as place_name,
    p.precision_meters,
    ST_Y(p.coordinates::geometry) as lat,
    ST_X(p.coordinates::geometry) as lng,
    c.id as content_id,
    c.title as content_title,
    c.url as content_url,
    c.source_name,
    c.source_url as source_channel_url,
    c.source_icon_url,
    m.user_id,
    au.display_name as author_name,
    {MEMORY_MEDIA},
    {COORDINATE_IS_UNIQUE}"""

# Both LEFT: a submitted memory has no content, an extracted one has no author.
# `au` and not `u` because DEVICE_UNLOCKS_QUERY owns `u` for the unlocks table.
MEMORY_JOIN = """
FROM memories m
JOIN places p ON m.place_id = p.id
LEFT JOIN content c ON m.content_id = c.id
LEFT JOIN users au ON m.user_id = au.id"""

# Every query below that can emit a summary honours this, counts included. A
# takedown that only covers the endpoint somebody complained about is not one.
VISIBLE = "NOT m.hidden"

DISTANCE = "ST_Distance(p.coordinates, ST_MakePoint(:lng, :lat)::geography) as distance_meters"
WITHIN = "ST_DWithin(p.coordinates, ST_MakePoint(:lng, :lat)::geography, :radius_meters)"

# ponytail: spans two tables, so no index can serve it and every search is a
# sequential scan. The obvious OR fix does not work - measured. See
# docs/10-decisions.md#search-is-a-sequential-scan-on-purpose.
SEARCH_VECTOR = "to_tsvector('english', m.summary || ' ' || p.name)"
SEARCH_MATCH = f"{SEARCH_VECTOR} @@ plainto_tsquery('english', :query)"
SEARCH_RANK = f"ts_rank({SEARCH_VECTOR}, plainto_tsquery('english', :query)) as rank"

PLACE_TAGS = """COALESCE(
        (SELECT array_agg(DISTINCT t) FROM memories m2, unnest(m2.tags) t
         WHERE m2.place_id = p.id AND NOT m2.hidden),
        ARRAY[]::varchar[]
    ) as tags"""

CONFIDENCE_FILTER = """(:min_confidence = 'low' OR m.extraction_confidence IN ('medium', 'high'))
    AND (:min_confidence != 'high' OR m.extraction_confidence = 'high')"""

# A no-op when :layer is NULL, so one query serves filtered and unfiltered.
LAYER_FILTER = "(CAST(:layer AS varchar) IS NULL OR m.layer = :layer)"

# Layer before everything else. Friend and stranger content is somebody who was
# standing here; historical is the archive. They must never sort as peers -
# docs/08-ux-flows.md F4. It goes ahead of contrast rather than beside it,
# because a podcast anecdote with a good contrast score would otherwise bury the
# note a person left at the same point, and one point is one feed.
LAYER_ORDER = "CASE m.layer WHEN 'friend' THEN 0 WHEN 'stranger' THEN 1 ELSE 2 END"

# Contrast next, not distance: the gap between the memory and what you are
# looking at now is the product. NULLS LAST is load-bearing and inverts the
# whole ranking if dropped - docs/10-decisions.md#nulls-last-is-load-bearing.
# An anniversary outranks contrast and is outranked by layer. It is the whole of
# what "resurfacing" means here: there are no notifications in this product, so
# the only way a date can surface anything is by sorting it to the top of the
# list somebody is already looking at.
CONTRAST_ORDER = (
    f"ORDER BY {LAYER_ORDER}, anniversary DESC, "
    "m.contrast_score DESC NULLS LAST, distance_meters ASC"
)

NEARBY_MEMORIES_QUERY = f"""
SELECT {MEMORY_COLUMNS},
    {DISTANCE}
{MEMORY_JOIN}
WHERE
    p.coordinates IS NOT NULL
    AND {VISIBLE}
    AND {WITHIN}
    AND {LAYER_FILTER}
    AND {CONFIDENCE_FILTER}
{CONTRAST_ORDER}
LIMIT :limit OFFSET :offset
"""

NEARBY_MEMORIES_WITH_TAGS_QUERY = f"""
SELECT {MEMORY_COLUMNS},
    {DISTANCE}
{MEMORY_JOIN}
WHERE
    p.coordinates IS NOT NULL
    AND {VISIBLE}
    AND {WITHIN}
    AND m.tags && CAST(:tags AS varchar[])
    AND {LAYER_FILTER}
    AND {CONFIDENCE_FILTER}
{CONTRAST_ORDER}
LIMIT :limit OFFSET :offset
"""

# Must mirror the WHERE of the query above it, or meta.total is wrong and
# pagination breaks.
COUNT_QUERY = f"""
SELECT COUNT(*)
FROM memories m
JOIN places p ON m.place_id = p.id
WHERE
    p.coordinates IS NOT NULL
    AND {VISIBLE}
    AND {WITHIN}
    AND {LAYER_FILTER}
    AND {CONFIDENCE_FILTER}
"""

COUNT_WITH_TAGS_QUERY = f"""
SELECT COUNT(*)
FROM memories m
JOIN places p ON m.place_id = p.id
WHERE
    p.coordinates IS NOT NULL
    AND {VISIBLE}
    AND {WITHIN}
    AND m.tags && CAST(:tags AS varchar[])
    AND {LAYER_FILTER}
    AND {CONFIDENCE_FILTER}
"""

NEARBY_PLACES_QUERY = f"""
SELECT
    p.id,
    p.name,
    p.precision_meters,
    ST_Y(p.coordinates::geometry) as lat,
    ST_X(p.coordinates::geometry) as lng,
    {DISTANCE},
    COUNT(m.id) as memory_count,
    {PLACE_TAGS},
    {COORDINATE_IS_UNIQUE},
    (
        SELECT summary FROM memories
        WHERE place_id = p.id AND NOT hidden ORDER BY id LIMIT 1
    ) as sample_memory
FROM places p
JOIN memories m ON m.place_id = p.id
WHERE
    p.coordinates IS NOT NULL
    AND {VISIBLE}
    AND {WITHIN}
GROUP BY p.id, p.name, p.precision_meters, p.coordinates
ORDER BY distance_meters ASC
LIMIT :limit OFFSET :offset
"""

SINGLE_MEMORY_QUERY = f"""
SELECT {MEMORY_COLUMNS},
    m.created_at
{MEMORY_JOIN}
WHERE m.id = :memory_id AND {VISIBLE}
"""

SEARCH_MEMORIES_QUERY = f"""
SELECT {MEMORY_COLUMNS},
    {SEARCH_RANK}
{MEMORY_JOIN}
WHERE
    p.coordinates IS NOT NULL
    AND {VISIBLE}
    AND {SEARCH_MATCH}
ORDER BY rank DESC
LIMIT :limit OFFSET :offset
"""

SEARCH_MEMORIES_WITH_LOCATION_QUERY = f"""
SELECT {MEMORY_COLUMNS},
    {DISTANCE},
    {SEARCH_RANK}
{MEMORY_JOIN}
WHERE
    p.coordinates IS NOT NULL
    AND {VISIBLE}
    AND {SEARCH_MATCH}
    AND {WITHIN}
ORDER BY rank DESC, distance_meters ASC
LIMIT :limit OFFSET :offset
"""

SEARCH_COUNT_QUERY = f"""
SELECT COUNT(*)
FROM memories m
JOIN places p ON m.place_id = p.id
WHERE
    p.coordinates IS NOT NULL
    AND {VISIBLE}
    AND {SEARCH_MATCH}
"""

SEARCH_COUNT_WITH_LOCATION_QUERY = f"""
SELECT COUNT(*)
FROM memories m
JOIN places p ON m.place_id = p.id
WHERE
    p.coordinates IS NOT NULL
    AND {VISIBLE}
    AND {SEARCH_MATCH}
    AND {WITHIN}
"""

# Every device this one shares an account with, and itself. The `d.id` arm keeps
# it working signed out - docs/10-decisions.md#my_devices-keeps-a-did--device_id-arm.
MY_DEVICES = """(
    SELECT d.id FROM devices d
    WHERE d.id = CAST(:device_id AS uuid)
       OR (
           d.user_id IS NOT NULL
           AND d.user_id = (SELECT user_id FROM devices WHERE id = CAST(:device_id AS uuid))
       )
)"""

# One person's collection, newest first. Through MEMORY_COLUMNS so an unlocked
# memory serializes exactly like a nearby one. MIN(unlocked_at) because two
# phones on one account can both have earned it and the first time is the one
# that counts - without the grouping it would also appear twice.
DEVICE_UNLOCKS_QUERY = f"""
WITH earned AS (
    SELECT memory_id, MIN(unlocked_at) AS unlocked_at
    FROM unlocks
    WHERE device_id IN {MY_DEVICES}
    GROUP BY memory_id
)
SELECT {MEMORY_COLUMNS},
    earned.unlocked_at
{MEMORY_JOIN}
JOIN earned ON earned.memory_id = m.id
WHERE {VISIBLE}
ORDER BY earned.unlocked_at DESC
LIMIT :limit
"""

UNLOCK_COUNT_QUERY = (
    f"SELECT COUNT(DISTINCT memory_id) FROM unlocks WHERE device_id IN {MY_DEVICES}"
)

# Where the corpus actually is, for somebody standing where it is not.
# DBSCAN and not a grid, and how the label is picked:
# docs/10-decisions.md#hotspots-use-dbscan-not-a-rounded-grid.
HOTSPOTS_QUERY = """
WITH clustered AS (
    SELECT
        p.name,
        p.coordinates::geometry AS geom,
        ST_ClusterDBSCAN(p.coordinates::geometry, eps := 0.5, minpoints := 1) OVER () AS cluster_id
    FROM memories m
    JOIN places p ON m.place_id = p.id
    WHERE p.coordinates IS NOT NULL AND NOT m.hidden
)
SELECT
    ST_Y(ST_Centroid(ST_Collect(geom))) AS lat,
    ST_X(ST_Centroid(ST_Collect(geom))) AS lng,
    COUNT(*) AS memories,
    mode() WITHIN GROUP (ORDER BY btrim(split_part(name, ',', -1))) AS label
FROM clustered
GROUP BY cluster_id
ORDER BY memories DESC
LIMIT :limit
"""

# places/nearby is grouped, so its total is the number of GROUPS, not rows.
PLACES_COUNT_QUERY = f"""
SELECT COUNT(DISTINCT p.id)
FROM places p
JOIN memories m ON m.place_id = p.id
WHERE
    p.coordinates IS NOT NULL
    AND {VISIBLE}
    AND {WITHIN}
"""


# Its own place per submission - docs/10-decisions.md#a-submission-mints-its-own-place.
PLACE_INSERT = """
INSERT INTO places (name, place_query, coordinates, precision_meters, geocode_status)
VALUES (
    :name, :place_query,
    ST_SetSRID(ST_MakePoint(:lng, :lat), 4326)::geography,
    :precision_meters, 'user'
)
RETURNING id
"""

SUBMISSION_INSERT = """
INSERT INTO memories (
    place_id, content_id, timestamp_start, summary, tags,
    extraction_confidence, layer, happened_at, happened_precision, opens_at, user_id
)
VALUES (
    :place_id, NULL, NULL, :summary, CAST(:tags AS varchar[]),
    'high', 'stranger', :happened_at, :happened_precision, :opens_at,
    CAST(:user_id AS uuid)
)
RETURNING id
"""

# Only this device's own uploads, and only ones not already spoken for. Both
# halves matter: ids are sequential, so without the device check a submission
# could adopt the photo somebody else uploaded a second earlier.
MEDIA_ATTACH = """
UPDATE media SET memory_id = :memory_id
WHERE id = ANY(CAST(:ids AS integer[]))
  AND device_id = CAST(:device AS uuid)
  AND memory_id IS NULL
"""

# Closed list: free text would be a tag soup of one-offs within a week.
