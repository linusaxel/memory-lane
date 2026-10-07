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
# docs/10-decisions.md#the-gate. api/card.py interpolates this same constant,
# so there is one copy.
#
# Indexed by idx_places_grid, and it has to stay written exactly this way to
# stay indexed - ST_SnapToGrid(geom, size) and ST_SnapToGrid(geom, 0, 0, size,
# size) are the same answer and different expressions. Unindexed this scanned
# every place once per row returned: 305ms of a 338ms /v1/memories/nearby at
# 50k memories. `python -m pipeline.perf` is how to check that again.
# The bare boolean, for reuse inside a WHERE - an aliased column expression
# (below) is not legal there. ROUTE_CANDIDATES_QUERY is the one other caller.
COORDINATE_IS_UNIQUE_EXPR = """(
        SELECT COUNT(*) = 1 FROM places p2
        WHERE ST_SnapToGrid(p2.coordinates::geometry, 0.0001)
            = ST_SnapToGrid(p.coordinates::geometry, 0.0001)
          AND NOT EXISTS (
              SELECT 1 FROM memories m2 WHERE m2.place_id = p2.id AND m2.user_id IS NOT NULL
          )
    )"""
COORDINATE_IS_UNIQUE = f"{COORDINATE_IS_UNIQUE_EXPR} as coordinate_is_unique"

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

# COUNT never returns SQL NULL, so no COALESCE needed the way MEMORY_MEDIA
# above needs one for json_agg.
MEMORY_HEART_COUNT = """(
        SELECT COUNT(*) FROM memory_hearts mh WHERE mh.memory_id = m.id
    ) as heart_count"""

# Hidden notes are the author's takedowns, so they do not count.
MEMORY_NOTE_COUNT = """(
        SELECT COUNT(*) FROM memory_notes mn WHERE mn.memory_id = m.id AND NOT mn.hidden
    ) as note_count"""

# Something happened here on today's date. Day-and-month, so it fires every year
# rather than once. Day precision only: a year-only date is stored as 1 January
# and would fire every New Year's Day. Carried on every memory-shaped row rather
# than filtered on, because it is a reason to look and never a reason to hide
# anything.
# ponytail: a 29 February memory resurfaces only on a leap day. Nudging it to
# the 28th is a product decision nobody has made.
# UTC explicitly, not CURRENT_DATE. CURRENT_DATE is whatever timezone the
# cluster happens to be set to, which is one deployment setting away from
# disagreeing with api.gate.today() - and the two together decide whether a
# memory is shut and whether it is "on this day". See api/gate.py#today.
ANNIVERSARY = """(
        m.happened_at IS NOT NULL
        AND m.happened_precision IS NOT DISTINCT FROM 'day'
        AND to_char(m.happened_at, 'MM-DD')
            = to_char((now() AT TIME ZONE 'utc')::date, 'MM-DD')
    ) as anniversary"""

# Every column a memory-shaped response needs. row_to_memory reads the row by
# name, so a query is free to append distance, rank or unlocked_at.
MEMORY_COLUMNS = f"""
    m.id,
    m.summary,
    m.timestamp_start,
    m.tags,
    m.extraction_confidence,
    m.layer,
    m.happened_at,
    m.happened_precision,
    m.attribution,
    m.source_url,
    m.contrast_score,
    m.contrast_note,
    m.quote,
    m.quote_by,
    m.links,
    m.locket,
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
    c.source_type,
    c.published_at,
    m.user_id,
    au.display_name as author_name,
    au.avatar_path as author_avatar,
    {MEMORY_MEDIA},
    {MEMORY_HEART_COUNT},
    {MEMORY_NOTE_COUNT},
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


def not_blocked(author: str) -> str:
    """Nothing by someone the viewer's account blocked. The viewer is
    :device_id, and a NULL one (a read that does not know who asks) blocks
    nothing. App Store 1.2; docs/10-decisions.md#posts-are-screened-reports-need-an-account."""
    return f"""NOT EXISTS (
        SELECT 1 FROM blocks b JOIN devices bd ON bd.id = b.device_id
        WHERE b.blocked_user_id = {author}
          AND (bd.id = CAST(:device_id AS uuid)
               OR bd.user_id = (SELECT user_id FROM devices WHERE id = CAST(:device_id AS uuid))))"""


NOT_BLOCKED = not_blocked("m.user_id")

DISTANCE = "ST_Distance(p.coordinates, ST_MakePoint(:lng, :lat)::geography) as distance_meters"
WITHIN = "ST_DWithin(p.coordinates, ST_MakePoint(:lng, :lat)::geography, :radius_meters)"

# A stored column, not an expression. The expression it replaced spanned two
# tables - m.summary with p.name - so no index could cover it and every search
# was a sequential scan of the corpus. It holds exactly the same concatenation,
# maintained by triggers on both tables, so search still matches queries whose
# words straddle the summary and the place name. db/migrations/010 has the
# reasoning and the cost.
SEARCH_VECTOR = "m.search_vector"
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

# Layer before everything else. Stranger content is somebody who was standing
# here; historical is the archive. They must never sort as peers -
# docs/08-ux-flows.md F4. It goes ahead of contrast rather than beside it,
# because a podcast anecdote with a good contrast score would otherwise bury the
# note a person left at the same point, and one point is one feed.
LAYER_ORDER = "CASE m.layer WHEN 'stranger' THEN 0 ELSE 1 END"

# Contrast next, not distance: the gap between the memory and what you are
# looking at now is the product. NULLS LAST is load-bearing and inverts the
# whole ranking if dropped - docs/10-decisions.md#nulls-last-in-contrast_order-is-load-bearing.
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
    AND {NOT_BLOCKED}
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
    AND {NOT_BLOCKED}
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
    AND {NOT_BLOCKED}
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
    AND {NOT_BLOCKED}
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
    AND {NOT_BLOCKED}
"""

# Author-facing only, so VISIBLE is deliberately absent: a reported memory
# must stay on the one screen that explains its own moderation state, or it
# just vanishes with no explanation to the person who filed it.
MY_MEMORIES_QUERY = f"""
SELECT {MEMORY_COLUMNS},
    m.created_at,
    m.hidden,
    -- Stored naive, in UTC: sent with its zone so a phone reads it as UTC.
    (
        SELECT MAX(hearted_at) AT TIME ZONE 'UTC' FROM memory_hearts mh
        WHERE mh.memory_id = m.id
    ) AS last_hearted_at,
    -- People, not phones, and never the author: filing opens it for them.
    (
        SELECT COUNT(DISTINCT COALESCE(d.user_id, d.id)) FROM unlocks un
        JOIN devices d ON d.id = un.device_id
        WHERE un.memory_id = m.id AND d.user_id IS DISTINCT FROM m.user_id
    ) AS opened_by
{MEMORY_JOIN}
WHERE m.user_id = (SELECT user_id FROM devices WHERE id = CAST(:device AS uuid))
ORDER BY m.created_at DESC
LIMIT :limit
OFFSET :offset
"""

MY_MEMORIES_COUNT_QUERY = """
SELECT COUNT(*)
FROM memories m
WHERE m.user_id = (SELECT user_id FROM devices WHERE id = CAST(:device AS uuid))
"""

# Same shape as SINGLE_MEMORY_QUERY, minus VISIBLE and plus the ownership
# check baked into the WHERE - an edit or delete of somebody else's memory, or
# one that no longer exists, is the same 404 as a look-up for a bad id.
OWNED_MEMORY_QUERY = f"""
SELECT {MEMORY_COLUMNS},
    m.hidden
{MEMORY_JOIN}
WHERE m.id = :memory_id
  AND m.user_id = (SELECT user_id FROM devices WHERE id = CAST(:device AS uuid))
"""

# Only ever removes attachments the memory already owns - the caller has
# already proved it owns the memory by the time this runs.
MEDIA_DETACH_QUERY = """
DELETE FROM media
WHERE id = ANY(CAST(:ids AS integer[]))
  AND memory_id = :memory_id
RETURNING path
"""

# Both search queries rank a page out of `memories` first and fetch the columns
# afterwards. Ranking cannot use an index - ts_rank has to be evaluated on every
# row the tsquery matches - so a common word matches the whole corpus, and
# joining `content` and `users` before the LIMIT built 200,000 wide rows to
# throw 199,980 of them away. Measured by `python -m pipeline.perf --rows
# 200000`: 245ms before, 59ms after, same twenty rows. The join to `places`
# stays inside, because `coordinates IS NOT NULL` decides which rows are
# eligible and so has to run before the LIMIT, not after it.
SEARCH_PAGE = f"""
    SELECT m.id, {SEARCH_RANK}
    FROM memories m
    JOIN places p ON m.place_id = p.id
    WHERE
        p.coordinates IS NOT NULL
        AND {VISIBLE}
        AND {SEARCH_MATCH}"""

SEARCH_MEMORIES_QUERY = f"""
WITH page AS (
{SEARCH_PAGE}
    ORDER BY rank DESC
    LIMIT :limit OFFSET :offset
)
SELECT {MEMORY_COLUMNS},
    page.rank
{MEMORY_JOIN}
JOIN page ON page.id = m.id
ORDER BY page.rank DESC
"""

SEARCH_MEMORIES_WITH_LOCATION_QUERY = f"""
WITH page AS (
{SEARCH_PAGE}
        AND {WITHIN}
    ORDER BY rank DESC, ST_Distance(p.coordinates, ST_MakePoint(:lng, :lat)::geography) ASC
    LIMIT :limit OFFSET :offset
)
SELECT {MEMORY_COLUMNS},
    {DISTANCE},
    page.rank
{MEMORY_JOIN}
JOIN page ON page.id = m.id
ORDER BY page.rank DESC, distance_meters ASC
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

# Notes open when the memory does: unlocked on any of this account's devices.
# The author always qualifies, because filing records the author's unlock.
# See docs/10-decisions.md#notes-are-gated-like-a-purchase.
NOTE_ALLOWED_QUERY = f"""
SELECT EXISTS (
    SELECT 1 FROM unlocks WHERE memory_id = :memory_id AND device_id IN {MY_DEVICES}
)"""

MEMORY_NOTES_QUERY = f"""
SELECT n.id, n.body, n.created_at, d.user_id, u.display_name,
    n.device_id IN {MY_DEVICES} AS mine
FROM memory_notes n
JOIN devices d ON d.id = n.device_id
LEFT JOIN users u ON u.id = d.user_id
WHERE n.memory_id = :memory_id AND NOT n.hidden AND {not_blocked("d.user_id")}
ORDER BY n.created_at
"""

# Its writer, or the memory's author, may take a note down.
NOTE_HIDE_QUERY = f"""
UPDATE memory_notes n SET hidden = TRUE
WHERE n.id = :note_id AND n.memory_id = :memory_id
  AND (
      n.device_id IN {MY_DEVICES}
      OR EXISTS (
          SELECT 1 FROM memories m
          WHERE m.id = n.memory_id
            AND m.user_id = (SELECT user_id FROM devices WHERE id = CAST(:device_id AS uuid))
      )
  )
RETURNING n.id
"""

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
    earned.unlocked_at,
    EXISTS (
        SELECT 1 FROM memory_hearts mh
        WHERE mh.memory_id = m.id AND mh.device_id IN {MY_DEVICES}
    ) AS hearted
{MEMORY_JOIN}
JOIN earned ON earned.memory_id = m.id
WHERE {VISIBLE}
    AND {NOT_BLOCKED}
ORDER BY earned.unlocked_at DESC
LIMIT :limit
"""

UNLOCK_COUNT_QUERY = (
    f"SELECT COUNT(DISTINCT memory_id) FROM unlocks WHERE device_id IN {MY_DEVICES}"
)

# The distinct calendar days this account unlocked a stop of that day's walk,
# newest first. Filing records an unlock too and must not count, or a streak
# is kept by posting anything. api.accounts.current_streak turns this into a
# number - no stored counter, so nothing to keep in sync across devices.
STREAK_DAYS_QUERY = f"""
    SELECT DISTINCT u.unlocked_at::date AS d
    FROM unlocks u
    JOIN daily_routes r
      ON r.device_id IN {MY_DEVICES}
     AND r.route_date = u.unlocked_at::date
     AND u.memory_id = ANY(r.memory_ids)
    WHERE u.device_id IN {MY_DEVICES}
    ORDER BY d DESC
"""

# Has this account opened this memory already, on any of its devices? Opening
# it again costs nothing (docs/10, "Pick one to start, then where you
# stand").
EARNED_QUERY = f"""
    SELECT EXISTS (
        SELECT 1 FROM unlocks WHERE memory_id = :memory_id AND device_id IN {MY_DEVICES}
    )
"""

# Is this memory a stop of today's walk in progress, on any of this account's
# devices? Standing on one opens it for nothing (docs/10, "Keys open a lock,
# and today's walk is free"). An ended walk's stops cost a key again.
ON_TODAYS_ROUTE_QUERY = f"""
    SELECT EXISTS (
        SELECT 1 FROM daily_routes
        WHERE device_id IN {MY_DEVICES}
          AND route_date = CAST(:today AS date)
          AND ended_at IS NULL
          AND :memory_id = ANY(memory_ids)
    )
"""

# An unexpired surprise for this memory, on this account
# (docs/10-decisions.md#a-surprise-once-a-week): the one other thing that opens.
SURPRISE_OPEN_QUERY = """
    SELECT EXISTS (
        SELECT 1 FROM surprises
        WHERE memory_id = :memory_id
          AND expires_at > LOCALTIMESTAMP
          AND user_id = (SELECT user_id FROM devices WHERE id = CAST(:device_id AS uuid))
    )
"""

# Has this account had a surprise in the last :days days?
SURPRISED_LATELY_QUERY = """
    SELECT EXISTS (
        SELECT 1 FROM surprises
        WHERE user_id = :user_id
          AND granted_at > LOCALTIMESTAMP - make_interval(days => :days)
    )
"""

# Has this account already had today's walk? Any walk today on any of its
# devices, bar this device's own in progress. An ended walk that opened nothing
# was deleted by ROUTE_PRUNE, so it never counts: a bad plan or rain before the
# first stop does not spend the day.
WALKED_TODAY_QUERY = f"""
    SELECT EXISTS (
        SELECT 1 FROM daily_routes
        WHERE device_id IN {MY_DEVICES}
          AND route_date = CAST(:today AS date)
          AND NOT (device_id = CAST(:device_id AS uuid) AND ended_at IS NULL)
    )
"""

# Every finished walk this account took, oldest first, one a day: a
# subscriber's second walk earns nothing more (api.progression).
FINISHED_WALKS_QUERY = f"""
    SELECT DISTINCT ON (route_date) id, cardinality(memory_ids) AS stops, budget_meters
    FROM daily_routes
    WHERE device_id IN {MY_DEVICES} AND completed_at IS NOT NULL
    ORDER BY route_date, completed_at
"""


# Credit the steps the phone counted since the watermark, and move it to now.
# Only if `since` is still the watermark, so a retried or raced sync is
# credited once. No more than MAX_STEPS_PER_SECOND over the window: the count
# is self-reported, like the position.
CREDIT_STEPS = """
    UPDATE users
    SET steps = steps + LEAST(
            :steps,
            CAST(:max_rate * EXTRACT(EPOCH FROM CURRENT_TIMESTAMP - steps_counted_until) AS integer)
        ),
        steps_counted_until = CURRENT_TIMESTAMP
    WHERE id = CAST(:user_id AS uuid) AND steps_counted_until = :since
    RETURNING id
"""

# Is this device's account paid up? A device with no account never is. Only
# the store's webhook writes the row (docs/10, "A walk planner, nothing else").
SUBSCRIBED_QUERY = """
    SELECT EXISTS (
        SELECT 1 FROM subscriptions s JOIN devices d ON d.user_id = s.user_id
        WHERE d.id = CAST(:device_id AS uuid) AND s.expires_at > CURRENT_TIMESTAMP
    )
"""

# Today's route candidates: nearby, not already earned, and actually worth the
# walk. Four predicates that exist nowhere else in this file:
#   - not already unlocked - the inverse of DEVICE_UNLOCKS_QUERY's `earned` CTE,
#     over the same MY_DEVICES so a second phone on one account sees the same
#     route rather than re-discovering what its sibling already earned.
#   - only walk-to-unlock memories - a centroid a route sent you to would open
#     the moment you arrived, which is not a stop, it is scenery.
# `preferred` counts how many of a subscriber's choices a memory meets, its theme
# and its era (an undated memory meets no era): they lean the walk, never
# filter it (docs/10, "Subscribers shape the walk").
# Ordered by distance and not CONTRAST_ORDER on purpose: a route is where to
# walk next, not a feed to rank.
ROUTE_CANDIDATES_QUERY = f"""
SELECT {MEMORY_COLUMNS},
    m.walk_score,
    COALESCE(m.tags && CAST(:tags AS varchar[]), false)::int
    + COALESCE(
        (CAST(:year_from AS integer) IS NOT NULL OR CAST(:year_to AS integer) IS NOT NULL)
        AND EXTRACT(YEAR FROM m.happened_at)
            BETWEEN COALESCE(CAST(:year_from AS integer), -9999)
            AND COALESCE(CAST(:year_to AS integer), 9999),
        false
    )::int AS preferred,
    {DISTANCE}
{MEMORY_JOIN}
WHERE
    p.coordinates IS NOT NULL
    AND {VISIBLE}
    AND {NOT_BLOCKED}
    AND {WITHIN}
    AND (m.user_id IS NOT NULL OR {COORDINATE_IS_UNIQUE_EXPR})
    AND NOT EXISTS (
        SELECT 1 FROM unlocks u WHERE u.memory_id = m.id AND u.device_id IN {MY_DEVICES}
    )
-- A stack's memories share one distance: the preferred, then the best scored
-- stands for the place, and the id makes that the same on every call, so a
-- preview and its accept agree.
ORDER BY distance_meters ASC, preferred DESC, m.walk_score DESC NULLS LAST, m.id ASC
LIMIT :limit
"""

# Today's route, rendered. No DISTANCE here - lat/lng are only ever supplied
# on the day's first call, and a stop's distance from wherever the phone is
# right now is exactly what reach.ts already computes client-side from GPS.
# array_position keeps the read in the order the route was stored in, the same
# way the array itself preserves it on write - no join table needed either
# direction for at most a handful of stops.
ROUTE_QUERY = f"""
SELECT {MEMORY_COLUMNS}
{MEMORY_JOIN}
WHERE m.id = ANY(CAST(:ids AS integer[])) AND {VISIBLE}
ORDER BY array_position(CAST(:ids AS integer[]), m.id)
"""

# Mark today's walk finished when this unlock earned its last visible stop.
# Earned across MY_DEVICES, like the route's candidates; hidden stops are not
# owed, because the walk drops them (ROUTE_QUERY). Set once, never moved.
ROUTE_COMPLETED_QUERY = f"""
UPDATE daily_routes r SET completed_at = CURRENT_TIMESTAMP
WHERE r.device_id = CAST(:device_id AS uuid)
  AND r.route_date = CAST(:today AS date)
  AND r.ended_at IS NULL
  AND r.completed_at IS NULL
  AND :memory_id = ANY(r.memory_ids)
  AND NOT EXISTS (
      SELECT 1 FROM memories m
      WHERE m.id = ANY(r.memory_ids) AND {VISIBLE}
        AND m.id NOT IN (SELECT memory_id FROM unlocks WHERE device_id IN {MY_DEVICES})
  )
RETURNING r.id
"""

# Every walk this account took that opened something, newest first - across
# MY_DEVICES, so a new phone signed in gets its history the way it gets its
# unlocks (F22). Ended walks too: what was earned on one was walked. The
# filter is here, not in Python, so LIMIT counts only walks that are listed;
# it is what keeps today's walk out until its first unlock.
WALKED_QUERY = f"""
SELECT route_date, memory_ids, budget_meters, legs, loop, completed_at
FROM daily_routes r
WHERE device_id IN {MY_DEVICES}
  AND EXISTS (
      SELECT 1 FROM unlocks u JOIN memories m ON m.id = u.memory_id
      WHERE u.device_id IN {MY_DEVICES} AND u.memory_id = ANY(r.memory_ids) AND {VISIBLE}
  )
ORDER BY route_date DESC, created_at DESC
LIMIT :limit
"""

# This device's walks that opened nothing and never will: every one but
# today's in progress (docs/10, "A walk that opened nothing is deleted").
# Hidden memories count here, unlike the journal: the streak counts their
# unlocks, so a walk with one is not empty.
ROUTE_PRUNE = f"""
DELETE FROM daily_routes r
WHERE r.device_id = CAST(:device_id AS uuid)
  AND NOT (r.route_date = :route_date AND r.ended_at IS NULL)
  AND NOT EXISTS (
      SELECT 1 FROM unlocks u
      WHERE u.device_id IN {MY_DEVICES} AND u.memory_id = ANY(r.memory_ids)
  )
"""

# Those walks' stops, and whether this account has earned each one.
WALKED_STOPS_QUERY = f"""
SELECT {MEMORY_COLUMNS},
    m.id IN (SELECT memory_id FROM unlocks WHERE device_id IN {MY_DEVICES}) AS earned
{MEMORY_JOIN}
WHERE m.id = ANY(CAST(:ids AS integer[])) AND {VISIBLE}
"""

# Where the corpus actually is, for somebody standing where it is not.
# DBSCAN and not a grid, and how the label is picked:
# docs/10-decisions.md#hotspots-use-dbscan-not-a-rounded-grid.
# Clusters places, not memories, and sums the counts afterwards.
#
# It used to feed DBSCAN one point per memory, so a place with fifty memories
# handed it fifty identical points - and DBSCAN is the one thing here whose
# cost is superlinear in its input. Measured on 50,000 memories across 20,000
# places: 10.9s per memory, 1.2s per place, and the same four hotspots with the
# same counts.
#
# Two things move slightly as a result, both for the better. The centroid is
# now the centre of the places in a cluster rather than one dragged toward the
# busiest venue in it, and the label is the modal trailing name-component
# across places rather than across memories. This answers "the closest
# memories are in New York", which is a question about an area.
HOTSPOTS_QUERY = """
WITH placed AS (
    SELECT
        p.id,
        p.name,
        p.coordinates::geometry AS geom,
        COUNT(m.id) AS memories
    FROM places p
    JOIN memories m ON m.place_id = p.id
    WHERE p.coordinates IS NOT NULL AND NOT m.hidden
    GROUP BY p.id, p.name, p.coordinates
),
clustered AS (
    SELECT
        placed.*,
        ST_ClusterDBSCAN(geom, eps := 0.5, minpoints := 1) OVER () AS cluster_id
    FROM placed
)
SELECT
    ST_Y(ST_Centroid(ST_Collect(geom))) AS lat,
    ST_X(ST_Centroid(ST_Collect(geom))) AS lng,
    SUM(memories)::bigint AS memories,
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
    extraction_confidence, layer, happened_at, happened_precision, user_id, locket
)
VALUES (
    :place_id, NULL, NULL, :summary, CAST(:tags AS varchar[]),
    'high', 'stranger', :happened_at, :happened_precision,
    CAST(:user_id AS uuid), COALESCE(:locket, random_locket())
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

# A submission's place is 1:1 with it and never shared - see PLACE_INSERT's
# place_query - so once its one memory is gone the place is just clutter.
# `place_query LIKE 'user:%'` is the same prefix PLACE_INSERT writes, and it
# is what stops this from ever touching an extraction-owned place.
DELETE_ORPHAN_SUBMITTED_PLACE = """
DELETE FROM places
WHERE id = :place_id
  AND place_query LIKE 'user:%'
  AND NOT EXISTS (SELECT 1 FROM memories WHERE place_id = :place_id)
"""

# Closed list: free text would be a tag soup of one-offs within a week.

# The city board: distinct memories each account opened inside the city this
# calendar month (UTC), ranked. Per account, not per device, so a second phone
# adds nothing. Only accounts still on_board. A monthly reset keeps it winnable
# (docs/10-decisions.md#a-city-board-by-opens).
BOARD_QUERY = """
WITH counts AS (
    SELECT d.user_id, COUNT(DISTINCT un.memory_id) AS opens
    FROM unlocks un
    JOIN devices d ON d.id = un.device_id
    JOIN users u ON u.id = d.user_id
    JOIN memories m ON m.id = un.memory_id
    JOIN places p ON p.id = m.place_id
    WHERE u.on_board
      AND un.unlocked_at >= date_trunc('month', now() AT TIME ZONE 'utc')
      AND ST_DWithin(p.coordinates, ST_MakePoint(:city_lng, :city_lat)::geography, :city_radius)
    GROUP BY d.user_id
), ranked AS (
    SELECT user_id, opens, RANK() OVER (ORDER BY opens DESC) AS rank FROM counts
)
SELECT r.rank, r.opens, u.display_name, u.avatar_path,
    u.id = (SELECT user_id FROM devices WHERE id = CAST(:device_id AS uuid)) AS mine
FROM ranked r JOIN users u ON u.id = r.user_id
WHERE r.rank <= :top
   OR u.id = (SELECT user_id FROM devices WHERE id = CAST(:device_id AS uuid))
ORDER BY r.rank, u.id
"""
