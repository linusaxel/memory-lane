"""FastAPI application for Memory Lane API."""

import os
from datetime import date
from math import asin, cos, radians, sin, sqrt

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from sqlalchemy import text

from api.card import router as card_router
from api.embed import router as embed_router
from pipeline.db import get_session

app = FastAPI(
    title="Memory Lane API",
    description="Query location-based memories from video content",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    # A wildcard origin with credentials is rejected by browsers anyway, and the
    # mobile app sends no cookies. Set CORS_ORIGINS to lock this down for a web client.
    allow_origins=os.getenv("CORS_ORIGINS", "*").split(","),
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(card_router)
app.include_router(embed_router)

# How close you have to stand to read a memory. 150m and not 50m because urban
# GPS drifts tens of metres, and a gate that will not open while you are
# standing on the spot is a bug the person blames on themselves.
UNLOCK_RADIUS_METERS = int(os.getenv("UNLOCK_RADIUS_METERS", "150"))


class Coordinates(BaseModel):
    lat: float
    lng: float


class Place(BaseModel):
    id: int
    name: str
    coordinates: Coordinates | None = None
    precision_meters: int


class Source(BaseModel):
    """Who published the thing this memory came out of.

    Not the memory's own attribution (`Memory.attribution`, which credits an
    archive for an archival item) - this is the channel or publication, and it
    is what stops a summary reading as the app's own assertion.
    """

    name: str
    url: str | None = None
    icon_url: str | None = None


class ContentRef(BaseModel):
    id: int
    title: str | None
    url: str
    timestamp_start: float
    timestamp_url: str
    source: Source | None = None


class Memory(BaseModel):
    id: int
    summary: str
    place: Place
    distance_meters: float | None = None
    # Absent on a locked memory: the source is part of what standing there buys.
    content: ContentRef | None = None
    tags: list[str]
    confidence: str
    locked: bool = False
    unlock_radius_meters: int | None = None
    layer: str = "historical"
    happened_at: date | None = None
    attribution: str | None = None
    source_url: str | None = None
    contrast_score: float | None = None
    contrast_note: str | None = None


class NearbyMeta(BaseModel):
    total: int
    limit: int
    offset: int
    center: Coordinates
    radius_km: float


class NearbyResponse(BaseModel):
    memories: list[Memory]
    meta: NearbyMeta


class SearchMeta(BaseModel):
    total: int
    limit: int
    offset: int
    query: str
    center: Coordinates | None = None
    radius_km: float | None = None


class SearchResponse(BaseModel):
    memories: list[Memory]
    meta: SearchMeta


class PlaceWithCount(BaseModel):
    id: int
    name: str
    coordinates: Coordinates | None = None
    distance_meters: float | None = None
    memory_count: int
    tags: list[str]
    sample_memory: str | None = None


class PlacesResponse(BaseModel):
    places: list[PlaceWithCount]
    meta: NearbyMeta


class PlaceDetail(BaseModel):
    id: int
    name: str
    place_query: str
    coordinates: Coordinates | None = None
    precision_meters: int
    geocode_status: str
    memory_count: int
    tags: list[str]


# Whether this coordinate belongs to this place alone. 111 of 186 memories sit
# on 34 city centroids the model emitted when it did not know the address (see
# F6), and a memory filed 2km from where it happened cannot be gated on standing
# there. So only a coordinate no other place shares is trustworthy enough to
# make somebody walk to it; the rest stay open rather than lie about where they
# are. 0.0001 degrees is ~11m, the same grid the app clusters on.
# ponytail: a correlated scan of ~200 places per row. Materialize it onto
# places if the corpus ever reaches the tens of thousands.
COORDINATE_IS_UNIQUE = """(
        SELECT COUNT(*) = 1 FROM places p2
        WHERE ST_SnapToGrid(p2.coordinates::geometry, 0.0001)
            = ST_SnapToGrid(p.coordinates::geometry, 0.0001)
    ) as coordinate_is_unique"""

# The 14 columns every memory-shaped response needs. row_to_memory reads the row
# by name, so a query is free to append distance, rank or created_at.
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
    {COORDINATE_IS_UNIQUE}"""

MEMORY_JOIN = """
FROM memories m
JOIN places p ON m.place_id = p.id
JOIN content c ON m.content_id = c.id"""

DISTANCE = "ST_Distance(p.coordinates, ST_MakePoint(:lng, :lat)::geography) as distance_meters"
WITHIN = "ST_DWithin(p.coordinates, ST_MakePoint(:lng, :lat)::geography, :radius_meters)"

# ponytail: this spans two tables, so no expression index can serve it and every
# search is a sequential scan. At 224 memories that is microseconds and nothing
# calls this endpoint yet.
#
# Splitting it into `to_tsvector(m.summary) @@ q OR to_tsvector(p.name) @@ q`
# looks like the fix and is not: an OR across two tables still cannot use either
# index, because a row can qualify from the other side. Measured - the planner
# keeps scanning. The two designs that would work are in TODO.md; both cost more
# than this corpus is worth.
SEARCH_VECTOR = "to_tsvector('english', m.summary || ' ' || p.name)"
SEARCH_MATCH = f"{SEARCH_VECTOR} @@ plainto_tsquery('english', :query)"
SEARCH_RANK = f"ts_rank({SEARCH_VECTOR}, plainto_tsquery('english', :query)) as rank"

# Tags aggregated across every memory at a place.
PLACE_TAGS = """COALESCE(
        (SELECT array_agg(DISTINCT t) FROM memories m2, unnest(m2.tags) t WHERE m2.place_id = p.id),
        ARRAY[]::varchar[]
    ) as tags"""

CONFIDENCE_FILTER = """(:min_confidence = 'low' OR m.extraction_confidence IN ('medium', 'high'))
    AND (:min_confidence != 'high' OR m.extraction_confidence = 'high')"""

# A no-op when :layer is NULL, so one query serves filtered and unfiltered rather
# than doubling the variants again.
LAYER_FILTER = "(CAST(:layer AS varchar) IS NULL OR m.layer = :layer)"

# Contrast first: the point of the product is the gap between the memory and what
# you are looking at now, not which pin is nearest. NULLS LAST is load-bearing -
# Postgres sorts NULL FIRST under DESC, and every memory extracted before contrast
# scoring existed has none, so without it the unscored ones outrank every scored
# one and the ranking is exactly inverted.
CONTRAST_ORDER = "ORDER BY m.contrast_score DESC NULLS LAST, distance_meters ASC"

NEARBY_MEMORIES_QUERY = f"""
SELECT {MEMORY_COLUMNS},
    {DISTANCE}
{MEMORY_JOIN}
WHERE
    p.coordinates IS NOT NULL
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
    AND {WITHIN}
    AND m.tags && CAST(:tags AS varchar[])
    AND {LAYER_FILTER}
    AND {CONFIDENCE_FILTER}
{CONTRAST_ORDER}
LIMIT :limit OFFSET :offset
"""

# A count that does not mirror its result query's WHERE is a wrong meta.total
# and broken pagination. Keep these two in step with the queries above.
COUNT_QUERY = f"""
SELECT COUNT(*)
FROM memories m
JOIN places p ON m.place_id = p.id
WHERE
    p.coordinates IS NOT NULL
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
    (SELECT summary FROM memories WHERE place_id = p.id ORDER BY id LIMIT 1) as sample_memory
FROM places p
JOIN memories m ON m.place_id = p.id
WHERE
    p.coordinates IS NOT NULL
    AND {WITHIN}
GROUP BY p.id, p.name, p.precision_meters, p.coordinates
ORDER BY distance_meters ASC
LIMIT :limit OFFSET :offset
"""

SINGLE_MEMORY_QUERY = f"""
SELECT {MEMORY_COLUMNS},
    m.created_at
{MEMORY_JOIN}
WHERE m.id = :memory_id
"""

PLACE_MEMORIES_QUERY = f"""
SELECT {MEMORY_COLUMNS}
{MEMORY_JOIN}
WHERE p.id = :place_id
ORDER BY m.created_at DESC
LIMIT :limit OFFSET :offset
"""

SINGLE_PLACE_QUERY = f"""
SELECT
    p.id,
    p.name,
    p.place_query,
    p.precision_meters,
    p.geocode_status,
    ST_Y(p.coordinates::geometry) as lat,
    ST_X(p.coordinates::geometry) as lng,
    p.created_at,
    COUNT(m.id) as memory_count,
    {PLACE_TAGS}
FROM places p
LEFT JOIN memories m ON m.place_id = p.id
WHERE p.id = :place_id
GROUP BY p.id, p.name, p.place_query, p.precision_meters, p.geocode_status, p.coordinates, p.created_at
"""

CONTENT_MEMORIES_QUERY = f"""
SELECT {MEMORY_COLUMNS}
{MEMORY_JOIN}
WHERE c.id = :content_id
ORDER BY m.timestamp_start ASC
LIMIT :limit OFFSET :offset
"""

SEARCH_MEMORIES_QUERY = f"""
SELECT {MEMORY_COLUMNS},
    {SEARCH_RANK}
{MEMORY_JOIN}
WHERE
    p.coordinates IS NOT NULL
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
    AND {SEARCH_MATCH}
"""

SEARCH_COUNT_WITH_LOCATION_QUERY = f"""
SELECT COUNT(*)
FROM memories m
JOIN places p ON m.place_id = p.id
WHERE
    p.coordinates IS NOT NULL
    AND {SEARCH_MATCH}
    AND {WITHIN}
"""

# Where the corpus actually is, for somebody standing where it is not. The app
# is a map of nothing outside New York, and "No memories here yet" is true and
# useless - this is what turns it into somewhere to go.
#
# DBSCAN rather than a rounded grid: 0.5 degrees is roughly a metro area, and a
# grid splits any city that happens to straddle a cell boundary. New York's
# places span 40.70-40.82 and a 0.1 grid cut them into two "hotspots".
#
# The label is the most common trailing component of the place names in the
# cluster - "Gotham Comedy Club, New York" -> "New York". Crude, and it reads
# correctly for every cluster in the corpus, which is the bar for a hint.
HOTSPOTS_QUERY = """
WITH clustered AS (
    SELECT
        p.name,
        p.coordinates::geometry AS geom,
        ST_ClusterDBSCAN(p.coordinates::geometry, eps := 0.5, minpoints := 1) OVER () AS cluster_id
    FROM memories m
    JOIN places p ON m.place_id = p.id
    WHERE p.coordinates IS NOT NULL
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
    AND {WITHIN}
"""


def row_source(row) -> Source | None:
    """None only when nothing knows who published it - four hand-listed videos
    from channels the config never names. A name with no link is still worth
    showing; a link with no name is not."""
    name = getattr(row, "source_name", None)
    if not name:
        return None
    return Source(
        name=name,
        url=getattr(row, "source_channel_url", None),
        icon_url=getattr(row, "source_icon_url", None),
    )


def row_coordinates(row) -> Coordinates | None:
    """A place with no coordinates is filtered out of most queries, not all."""
    if row.lat is None or row.lng is None:
        return None
    return Coordinates(lat=row.lat, lng=row.lng)


def viewer_position(lat: float | None, lng: float | None) -> Coordinates | None:
    """Half a position is no position."""
    return Coordinates(lat=lat, lng=lng) if lat is not None and lng is not None else None


def meters_between(a: Coordinates, b: Coordinates) -> float:
    """Haversine. Postgres could do this, but the row already carries the
    coordinate, and this keeps the viewer's position out of every query's binds."""
    lat1, lat2 = radians(a.lat), radians(b.lat)
    dlat, dlng = lat2 - lat1, radians(b.lng - a.lng)
    h = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlng / 2) ** 2
    return 2 * 6_371_000 * asin(sqrt(h))


def is_gated(row) -> bool:
    """Whether this memory is worth making somebody walk to.

    Only a trustworthy coordinate qualifies - see COORDINATE_IS_UNIQUE. A place
    with no coordinates has nowhere to walk to.
    """
    return bool(getattr(row, "coordinate_is_unique", False)) and row_coordinates(row) is not None


def is_locked(row, at: Coordinates | None) -> bool:
    """A client-side gate is not a gate. The summary does not leave the server
    until the caller asks for this one memory from inside the radius, so every
    memory-shaped response goes through here rather than the one endpoint the
    app happens to call.

    `at` is only ever supplied by the single-memory read. The list endpoints
    hand out nothing readable however close you are standing: walking into range
    must *offer* the unlock, not perform it, or there is no moment to press and
    the whole mechanic is a proximity query with extra steps.

    ponytail: the position is self-reported, so this stops curl, not a
    determined spoofer. Attestation needs accounts - Phase 3.
    """
    if not is_gated(row):
        return False
    coords = row_coordinates(row)
    return at is None or coords is None or meters_between(at, coords) > UNLOCK_RADIUS_METERS


def locked_memory(row, coords: Coordinates | None, distance_meters: float | None) -> Memory:
    """Where it is and how far away, and nothing else - enough to decide whether
    to walk there, which is the only decision a locked memory has to support."""
    return Memory(
        id=row.id,
        summary="",
        place=Place(
            id=row.place_id,
            name=row.place_name,
            coordinates=coords,
            precision_meters=row.precision_meters,
        ),
        distance_meters=distance_meters,
        content=None,
        tags=[],
        confidence=row.extraction_confidence or "medium",
        layer=getattr(row, "layer", None) or "historical",
        locked=True,
        unlock_radius_meters=UNLOCK_RADIUS_METERS,
    )


def row_to_memory(row, at: Coordinates | None = None, include_distance: bool = True) -> Memory:
    coords = row_coordinates(row)
    distance = row.distance_meters if include_distance and hasattr(row, "distance_meters") else None

    if is_locked(row, at):
        return locked_memory(row, coords, distance)

    timestamp_url = row.content_url
    if "youtube.com" in row.content_url or "youtu.be" in row.content_url:
        separator = "&" if "?" in row.content_url else "?"
        timestamp_url = f"{row.content_url}{separator}t={int(row.timestamp_start)}"

    return Memory(
        id=row.id,
        summary=row.summary,
        place=Place(
            id=row.place_id,
            name=row.place_name,
            coordinates=coords,
            precision_meters=row.precision_meters,
        ),
        distance_meters=distance,
        content=ContentRef(
            id=row.content_id,
            title=row.content_title,
            url=row.content_url,
            timestamp_start=row.timestamp_start,
            timestamp_url=timestamp_url,
            source=row_source(row),
        ),
        tags=row.tags or [],
        confidence=row.extraction_confidence or "medium",
        layer=getattr(row, "layer", None) or "historical",
        happened_at=getattr(row, "happened_at", None),
        attribution=getattr(row, "attribution", None),
        source_url=getattr(row, "source_url", None),
        contrast_score=getattr(row, "contrast_score", None),
        contrast_note=getattr(row, "contrast_note", None),
    )


PRIVACY_HTML = """<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Memory Lane - Privacy Policy</title>
<style>body{font-family:system-ui,sans-serif;max-width:40rem;margin:3rem auto;padding:0 1rem;line-height:1.6;color:#222}h1{font-size:1.5rem}h2{font-size:1.05rem;margin-top:2rem}</style>
</head><body>
<h1>Memory Lane - Privacy Policy</h1>
<p>Memory Lane shows travel memories drawn from publicly available video transcripts,
on a map near you.</p>

<h2>Location</h2>
<p>If you grant location permission, your device's approximate coordinates are sent to
our servers solely to look up memories near you. Coordinates are used for that request
and are not stored, profiled, or linked to you.</p>

<h2>Accounts</h2>
<p>There are none. We do not ask for your name, email, or phone number, and we do not
collect device identifiers for advertising.</p>

<h2>What we do keep</h2>
<p>Our servers keep standard technical request logs (timestamp, coarse IP, endpoint)
for reliability and abuse prevention.</p>

<h2>Third parties</h2>
<p>We sell nothing and share nothing. Opening a memory's source video hands you off to
YouTube, whose own privacy policy then applies.</p>

<h2>Contact</h2>
<p>Questions: open an issue on the project repository.</p>
</body></html>"""


@app.get("/privacy", response_class=HTMLResponse, include_in_schema=False)
def privacy_policy():
    """Both app stores require a publicly reachable privacy policy URL."""
    return PRIVACY_HTML


@app.get("/")
def root():
    """API root - health check."""
    return {"status": "ok", "service": "memory-lane"}


@app.get("/v1/memories/nearby", response_model=NearbyResponse)
def get_nearby_memories(
    lat: float = Query(..., ge=-90, le=90, description="Latitude"),
    lng: float = Query(..., ge=-180, le=180, description="Longitude"),
    radius_km: float = Query(10, ge=0.1, le=100, description="Search radius in km"),
    limit: int = Query(20, ge=1, le=100, description="Max results"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
    tags: str | None = Query(None, description="Comma-separated tags to filter"),
    layer: str | None = Query(
        None,
        pattern="^(historical|friend|stranger)$",
        description="Restrict to one content layer. Omit for all.",
    ),
    min_confidence: str = Query(
        "medium", pattern="^(low|medium|high)$", description="Minimum confidence"
    ),
):
    """Find memories near a location.

    Gated memories always come back locked, however close you are standing.
    Unlocking is one deliberate act against /v1/memories/{id}, not a side effect
    of the map happening to be pointed at you.
    """
    radius_meters = radius_km * 1000

    with get_session() as session:
        params = {
            "lat": lat,
            "lng": lng,
            "radius_meters": radius_meters,
            "limit": limit,
            "offset": offset,
            "min_confidence": min_confidence,
            "layer": layer,
        }

        if tags:
            params["tags"] = [t.strip() for t in tags.split(",")]
            result = session.execute(text(NEARBY_MEMORIES_WITH_TAGS_QUERY), params)
            count_sql = COUNT_WITH_TAGS_QUERY
        else:
            result = session.execute(text(NEARBY_MEMORIES_QUERY), params)
            count_sql = COUNT_QUERY

        rows = result.fetchall()

        # Same params as the result query: the count has to see the same filters.
        total = session.execute(text(count_sql), params).scalar() or 0

    memories = [row_to_memory(row) for row in rows]

    return NearbyResponse(
        memories=memories,
        meta=NearbyMeta(
            total=total,
            limit=limit,
            offset=offset,
            center=Coordinates(lat=lat, lng=lng),
            radius_km=radius_km,
        ),
    )


@app.get("/v1/memories/search", response_model=SearchResponse)
def search_memories(
    q: str = Query(..., min_length=2, description="Search query"),
    lat: float | None = Query(
        None, ge=-90, le=90, description="Optional latitude for location filter"
    ),
    lng: float | None = Query(
        None, ge=-180, le=180, description="Optional longitude for location filter"
    ),
    radius_km: float = Query(
        50, ge=0.1, le=500, description="Search radius in km (if location provided)"
    ),
    limit: int = Query(20, ge=1, le=100, description="Max results"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
):
    """Full-text search across memory summaries and place names.

    Optionally filter by location using lat/lng parameters.
    """
    with get_session() as session:
        if lat is not None and lng is not None:
            radius_meters = radius_km * 1000
            result = session.execute(
                text(SEARCH_MEMORIES_WITH_LOCATION_QUERY),
                {
                    "query": q,
                    "lat": lat,
                    "lng": lng,
                    "radius_meters": radius_meters,
                    "limit": limit,
                    "offset": offset,
                },
            )
            rows = result.fetchall()
            center = Coordinates(lat=lat, lng=lng)
        else:
            result = session.execute(
                text(SEARCH_MEMORIES_QUERY), {"query": q, "limit": limit, "offset": offset}
            )
            rows = result.fetchall()
            center = None
            radius_km = None

        if center is not None:
            total = (
                session.execute(
                    text(SEARCH_COUNT_WITH_LOCATION_QUERY),
                    {"query": q, "lat": lat, "lng": lng, "radius_meters": radius_meters},
                ).scalar()
                or 0
            )
        else:
            total = session.execute(text(SEARCH_COUNT_QUERY), {"query": q}).scalar() or 0

    memories = [row_to_memory(row, include_distance=(lat is not None)) for row in rows]

    return SearchResponse(
        memories=memories,
        meta=SearchMeta(
            total=total, limit=limit, offset=offset, query=q, center=center, radius_km=radius_km
        ),
    )


@app.get("/v1/memories/{memory_id}", response_model=Memory)
def get_memory(
    memory_id: int,
    at_lat: float | None = Query(
        None, ge=-90, le=90, description="Where you actually are; unlocks this memory if near"
    ),
    at_lng: float | None = Query(
        None, ge=-180, le=180, description="Where you actually are; unlocks this memory if near"
    ),
):
    """One memory. This is the unlock read: supply a position inside the radius
    and the summary, tags and source come back. Without one, a gated memory
    returns its place and nothing else."""
    with get_session() as session:
        result = session.execute(text(SINGLE_MEMORY_QUERY), {"memory_id": memory_id})
        row = result.fetchone()

    if not row:
        raise HTTPException(status_code=404, detail="Memory not found")

    at = viewer_position(at_lat, at_lng)
    memory = row_to_memory(row, at, include_distance=False)
    if memory.locked and at is not None and memory.place.coordinates is not None:
        # It failed the gate, so say by how much rather than just refusing.
        memory.distance_meters = meters_between(at, memory.place.coordinates)
    return memory


@app.get("/v1/places/nearby", response_model=PlacesResponse)
def get_nearby_places(
    lat: float = Query(..., ge=-90, le=90, description="Latitude"),
    lng: float = Query(..., ge=-180, le=180, description="Longitude"),
    radius_km: float = Query(10, ge=0.1, le=100, description="Search radius in km"),
    limit: int = Query(20, ge=1, le=100, description="Max results"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
):
    """Get places with memory counts near a location."""
    radius_meters = radius_km * 1000

    with get_session() as session:
        result = session.execute(
            text(NEARBY_PLACES_QUERY),
            {
                "lat": lat,
                "lng": lng,
                "radius_meters": radius_meters,
                "limit": limit,
                "offset": offset,
            },
        )
        rows = result.fetchall()

        # len(places) is the page size, not the result size - it made every
        # page look like the last one.
        total = (
            session.execute(
                text(PLACES_COUNT_QUERY),
                {"lat": lat, "lng": lng, "radius_meters": radius_meters},
            ).scalar()
            or 0
        )

    places = []
    for row in rows:
        coords = row_coordinates(row)

        places.append(
            PlaceWithCount(
                id=row.id,
                name=row.name,
                coordinates=coords,
                distance_meters=row.distance_meters,
                memory_count=row.memory_count,
                tags=row.tags or [],
                # Verbatim summary: the same thing /v1/memories/nearby gates, so
                # it gates here too or the gate has a side door.
                sample_memory=None if is_gated(row) else row.sample_memory,
            )
        )

    return PlacesResponse(
        places=places,
        meta=NearbyMeta(
            total=total,
            limit=limit,
            offset=offset,
            center=Coordinates(lat=lat, lng=lng),
            radius_km=radius_km,
        ),
    )


@app.get("/v1/places/{place_id}", response_model=PlaceDetail)
def get_place(place_id: int):
    """Get details for a specific place."""
    with get_session() as session:
        result = session.execute(text(SINGLE_PLACE_QUERY), {"place_id": place_id})
        row = result.fetchone()

    if not row:
        raise HTTPException(status_code=404, detail="Place not found")

    coords = row_coordinates(row)

    return PlaceDetail(
        id=row.id,
        name=row.name,
        place_query=row.place_query,
        coordinates=coords,
        precision_meters=row.precision_meters,
        geocode_status=row.geocode_status,
        memory_count=row.memory_count,
        tags=row.tags or [],
    )


@app.get("/v1/places/{place_id}/memories", response_model=list[Memory])
def get_place_memories(
    place_id: int, limit: int = Query(50, ge=1, le=100), offset: int = Query(0, ge=0)
):
    """Get all memories for a specific place."""
    with get_session() as session:
        result = session.execute(
            text(PLACE_MEMORIES_QUERY), {"place_id": place_id, "limit": limit, "offset": offset}
        )
        rows = result.fetchall()

    if not rows:
        raise HTTPException(status_code=404, detail="Place not found or has no memories")

    return [row_to_memory(row, include_distance=False) for row in rows]


@app.get("/v1/content/{content_id}/memories", response_model=list[Memory])
def get_content_memories(
    content_id: int, limit: int = Query(50, ge=1, le=100), offset: int = Query(0, ge=0)
):
    """Get all memories extracted from a specific video/content."""
    with get_session() as session:
        result = session.execute(
            text(CONTENT_MEMORIES_QUERY),
            {"content_id": content_id, "limit": limit, "offset": offset},
        )
        rows = result.fetchall()

    if not rows:
        raise HTTPException(status_code=404, detail="Content not found or has no memories")

    return [row_to_memory(row, include_distance=False) for row in rows]


class Hotspot(BaseModel):
    """A place worth flying the map to when there is nothing where you are."""

    label: str
    lat: float
    lng: float
    memories: int


class Stats(BaseModel):
    memories: int
    places_with_coordinates: int
    processed_videos: int
    hotspots: list[Hotspot]


@app.get("/v1/stats", response_model=Stats)
def get_stats(
    hotspots: int = Query(5, ge=0, le=20, description="How many of the busiest areas to name"),
):
    """Database statistics, and where the memories actually are.

    The second part is not a statistic, it is the answer to an empty map. The
    corpus is one comedy podcast's touring history, so it is New York and then a
    long tail - and somebody opening this in Copenhagen sees nothing at all.
    """
    with get_session() as session:
        memories_count = session.execute(text("SELECT COUNT(*) FROM memories")).scalar()
        places_count = session.execute(
            text("SELECT COUNT(*) FROM places WHERE coordinates IS NOT NULL")
        ).scalar()
        content_count = session.execute(
            text("SELECT COUNT(*) FROM content WHERE memories_extracted = TRUE")
        ).scalar()
        rows = (
            session.execute(text(HOTSPOTS_QUERY), {"limit": hotspots}).fetchall()
            if hotspots
            else []
        )

    return Stats(
        memories=memories_count,
        places_with_coordinates=places_count,
        processed_videos=content_count,
        # A cluster whose place names give no trailing component has no label
        # worth showing, and a hint with no name is not a hint.
        hotspots=[
            Hotspot(label=r.label, lat=r.lat, lng=r.lng, memories=r.memories)
            for r in rows
            if r.label
        ],
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
