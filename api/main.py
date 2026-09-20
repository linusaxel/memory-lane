"""FastAPI application for Memory Lane API."""

import os
import uuid
from datetime import date
from math import asin, cos, radians, sin, sqrt

from fastapi import FastAPI, Form, HTTPException, Query, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field
from sqlalchemy import text

from api.card import router as card_router
from api.embed import router as embed_router
from api.media import MEDIA_DIR, MEDIA_URL_PREFIX, NoSniff, media_url, save_upload
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

# Uploaded photos and recordings, straight off the disk. Not a CDN and not
# object storage: one volume is the whole feature until somebody is paying for
# bandwidth.
# ponytail: swap NoSniff for an S3 bucket + signed URLs when this box stops
# being the only one.
MEDIA_DIR.mkdir(parents=True, exist_ok=True)
app.mount(MEDIA_URL_PREFIX, NoSniff(directory=MEDIA_DIR), name="media")

# How close you have to stand to read a memory. 150m and not 50m because urban
# GPS drifts tens of metres, and a gate that will not open while you are
# standing on the spot is a bug the person blames on themselves.
UNLOCK_RADIUS_METERS = int(os.getenv("UNLOCK_RADIUS_METERS", "150"))

# How many different people have to report a submission before it stops being
# served. Low, because the corpus is small and a wrongly hidden memory is
# recoverable while a libel left up for a week is not. The row survives either
# way - `hidden` is a flag, not a delete.
# ponytail: no appeal, no reinstatement, no queue for a human to look at.
# REPORT_THRESHOLD is the whole moderation system until there is a moderator.
REPORT_THRESHOLD = int(os.getenv("REPORT_THRESHOLD", "3"))


class Coordinates(BaseModel):
    lat: float
    lng: float


class Place(BaseModel):
    id: int
    name: str
    coordinates: Coordinates | None = None
    precision_meters: int


class Author(BaseModel):
    """Who filed this, when a person did rather than a transcript.

    Shown even while the memory is locked: "somebody stood here and wrote this
    down" is part of what makes it worth walking to, and it gives away nothing
    the summary was protecting.
    """

    id: str
    name: str


class MediaItem(BaseModel):
    """A photo or a recording hanging off a memory.

    Withheld entirely while locked - a photograph of the place is the memory as
    much as the text is. `media_count` still travels, because knowing there is a
    picture waiting is the pull, not the leak.
    """

    id: int
    kind: str
    url: str
    duration_seconds: float | None = None


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
    # Null for everything extracted from a video; set for what people file.
    author: Author | None = None
    # Empty while locked. media_count is not, so a locked card can say what is
    # waiting without handing any of it over.
    media: list[MediaItem] = []
    media_count: int = 0
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
#
# Places holding a submission do not count. Each submission mints its own place
# row at the submitter's GPS position, so without this exclusion filing a memory
# outside Katz's would put a second place in that grid cell and silently unlock
# every memory already there - a gate anybody could open by posting next to it.
# A submitted memory is gated on its own terms instead (see is_gated): the person
# was standing there, so the coordinate is real by construction.
#
# NOT EXISTS over a user memory, rather than EXISTS over an extracted one: a
# place with no memories at all still counts, which is what it did before this.
COORDINATE_IS_UNIQUE = """(
        SELECT COUNT(*) = 1 FROM places p2
        WHERE ST_SnapToGrid(p2.coordinates::geometry, 0.0001)
            = ST_SnapToGrid(p.coordinates::geometry, 0.0001)
          AND NOT EXISTS (
              SELECT 1 FROM memories m2 WHERE m2.place_id = p2.id AND m2.user_id IS NOT NULL
          )
    ) as coordinate_is_unique"""

# The 14 columns every memory-shaped response needs. row_to_memory reads the row
# by name, so a query is free to append distance, rank or created_at.
# Everything attached to this memory, in one round trip rather than one query
# per memory. json_agg returns SQL NULL for no rows, hence the COALESCE - a null
# here would make every media-less memory need a guard downstream.
# ponytail: a correlated subquery per row, like COORDINATE_IS_UNIQUE above.
# Fine at this size; a LEFT JOIN LATERAL if a page of 100 ever gets slow.
MEMORY_MEDIA = """COALESCE((
        SELECT json_agg(json_build_object(
                   'id', md.id, 'kind', md.kind, 'path', md.path,
                   'duration_seconds', md.duration_seconds
               ) ORDER BY md.id)
        FROM media md WHERE md.memory_id = m.id
    ), '[]'::json) as media"""

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
    m.user_id,
    au.display_name as author_name,
    {MEMORY_MEDIA},
    {COORDINATE_IS_UNIQUE}"""

# content is LEFT because a submitted memory has none, and users is LEFT because
# an extracted one has no author. Aliased `au` and not `u`: DEVICE_UNLOCKS_QUERY
# already owns `u` for the unlocks table.
MEMORY_JOIN = """
FROM memories m
JOIN places p ON m.place_id = p.id
LEFT JOIN content c ON m.content_id = c.id
LEFT JOIN users au ON m.user_id = au.id"""

# Honoured by every query below that can emit a summary, including the counts.
# A takedown that only covers the endpoint somebody complained about is not one.
VISIBLE = "NOT m.hidden"

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
        (SELECT array_agg(DISTINCT t) FROM memories m2, unnest(m2.tags) t
         WHERE m2.place_id = p.id AND NOT m2.hidden),
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

# A count that does not mirror its result query's WHERE is a wrong meta.total
# and broken pagination. Keep these two in step with the queries above.
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

PLACE_MEMORIES_QUERY = f"""
SELECT {MEMORY_COLUMNS}
{MEMORY_JOIN}
WHERE p.id = :place_id AND {VISIBLE}
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
WHERE c.id = :content_id AND {VISIBLE}
ORDER BY m.timestamp_start ASC
LIMIT :limit OFFSET :offset
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

# One device's collection, newest first. Joined through MEMORY_COLUMNS so an
# unlocked memory serializes exactly like a nearby one - the app should not have
# to know which endpoint a memory arrived from.
DEVICE_UNLOCKS_QUERY = f"""
SELECT {MEMORY_COLUMNS},
    u.unlocked_at
{MEMORY_JOIN}
JOIN unlocks u ON u.memory_id = m.id
WHERE u.device_id = CAST(:device_id AS uuid) AND {VISIBLE}
ORDER BY u.unlocked_at DESC
LIMIT :limit
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

    Two ways to qualify. An extracted memory needs a trustworthy coordinate -
    see COORDINATE_IS_UNIQUE, and most do not have one. A submitted memory
    always has one: it was filed from the phone of somebody standing there, so
    there is no centroid problem to protect anyone from.

    Either way a place with no coordinates has nowhere to walk to.
    """
    if row_coordinates(row) is None:
        return False
    return getattr(row, "user_id", None) is not None or bool(
        getattr(row, "coordinate_is_unique", False)
    )


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


def row_author(row) -> Author | None:
    """A submission with no display name is still somebody. "Anonymous" is the
    honest rendering of a blank one, and it is decided here rather than in the
    app so the card and the API cannot disagree about it."""
    user_id = getattr(row, "user_id", None)
    if user_id is None:
        return None
    return Author(id=str(user_id), name=getattr(row, "author_name", None) or "Anonymous")


def row_media(row) -> list[MediaItem]:
    """json_agg gives back a list of dicts; the URL is built here so the stored
    path stays a path and the client never has to know where media lives."""
    return [
        MediaItem(
            id=item["id"],
            kind=item["kind"],
            url=media_url(item["path"]),
            duration_seconds=item.get("duration_seconds"),
        )
        for item in (getattr(row, "media", None) or [])
    ]


def locked_memory(row, coords: Coordinates | None, distance_meters: float | None) -> Memory:
    """Where it is, how far away, who filed it and how much is waiting - enough
    to decide whether to walk there, which is the only decision a locked memory
    has to support. The photo itself stays behind the gate with the text."""
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
        author=row_author(row),
        media_count=len(getattr(row, "media", None) or []),
        locked=True,
        unlock_radius_meters=UNLOCK_RADIUS_METERS,
    )


def row_to_memory(row, at: Coordinates | None = None, include_distance: bool = True) -> Memory:
    coords = row_coordinates(row)
    distance = row.distance_meters if include_distance and hasattr(row, "distance_meters") else None

    if is_locked(row, at):
        return locked_memory(row, coords, distance)

    # None for a submitted memory: it came from a person, not a recording, and
    # there is nothing to link out to. `author` is what carries the credit there.
    content = None
    if getattr(row, "content_id", None) is not None:
        started = row.timestamp_start or 0
        timestamp_url = row.content_url
        if "youtube.com" in row.content_url or "youtu.be" in row.content_url:
            separator = "&" if "?" in row.content_url else "?"
            timestamp_url = f"{row.content_url}{separator}t={int(started)}"
        content = ContentRef(
            id=row.content_id,
            title=row.content_title,
            url=row.content_url,
            timestamp_start=started,
            timestamp_url=timestamp_url,
            source=row_source(row),
        )

    media = row_media(row)

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
        content=content,
        author=row_author(row),
        media=media,
        media_count=len(media),
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
our servers to look up memories near you, and to check that you are close enough to
unlock one. Coordinates are used for that request and are not stored, profiled, or
linked to you &mdash; an unlock records which memory was opened and when, never where
you were standing.</p>

<h2>Accounts</h2>
<p>There is no sign-in. We do not ask for your email or phone number, and we do not
collect advertising identifiers.</p>
<p>If you post a memory you may give a display name. It is optional, it is shown publicly
under what you post, it is whatever you type, and you can change or clear it at any time.
It is not verified and is not linked to anything else about you.</p>

<h2>What you post</h2>
<p>A memory you file is public. Its text, tags, the place name you give it and the
coordinates you were standing at are shown to anyone who comes to that spot, alongside
the display name you chose or &ldquo;Anonymous&rdquo;. Do not post anything you would
not want a stranger standing there to read.</p>
<p>Photos and recordings you attach are stored on our servers and shown with the memory.
We strip nothing from them beyond re-encoding photos for size, so do not attach a file
whose contents you would not publish.</p>
<p>Anyone can report a memory. Enough reports and it stops being shown to anybody; the
record of it is kept so a dispute can be answered. To have something you posted removed,
open an issue on the project repository.</p>

<h2>Your unlocked memories</h2>
<p>To keep the memories you unlock, your copy of the app generates a random identifier
for itself the first time you unlock something, and sends it with that unlock. We store
the identifier and which memories it has opened, so your collection survives the app
losing its local data.</p>
<p>It is created on your device, not issued by us. It is not linked to your name, your
phone, your advertising identifier, or any other app, and it tells us nothing except
that one installation of Memory Lane unlocked a particular memory. Deleting the app
discards it, and the collection it refers to becomes unreachable.</p>

<h2>Camera, photos and microphone</h2>
<p>Used only when you choose to attach something to a memory you are posting, and only
for that. Nothing is captured in the background and nothing is uploaded that you did not
attach.</p>

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


DEVICE_PATTERN = r"^[0-9a-fA-F-]{36}$"


class UnlockRequest(BaseModel):
    """Everything an unlock needs, and nothing that identifies a person.

    device is a UUID the app generated for itself. The server never issues one,
    so it never hands an identifier to a client that did not already have it.
    """

    device: str = Field(pattern=DEVICE_PATTERN)
    lat: float = Field(ge=-90, le=90)
    lng: float = Field(ge=-180, le=180)


class UnlocksResponse(BaseModel):
    memories: list[Memory]


def touch_device(session, device: str) -> None:
    """Every write path needs the device row to exist first, and every one of
    them also wants last_seen moved. Three callers, one statement."""
    session.execute(
        text("""
            INSERT INTO devices (id, last_seen) VALUES (CAST(:id AS uuid), CURRENT_TIMESTAMP)
            ON CONFLICT (id) DO UPDATE SET last_seen = CURRENT_TIMESTAMP
        """),
        {"id": device},
    )


@app.post("/v1/memories/{memory_id}/unlock", response_model=Memory)
def unlock_memory(memory_id: int, body: UnlockRequest):
    """Earn a memory, and record that it was earned.

    POST rather than GET because it creates something. The gate is the same one
    every read goes through - this endpoint cannot return a summary the plain
    read would have withheld - but it is the only one that writes an unlock, and
    unlocking is the one thing in this product that is supposed to be an act.
    """
    with get_session() as session:
        row = session.execute(text(SINGLE_MEMORY_QUERY), {"memory_id": memory_id}).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Memory not found")

        at = Coordinates(lat=body.lat, lng=body.lng)
        memory = row_to_memory(row, at, include_distance=False)
        if memory.locked:
            # Say how far off, rather than only refusing: the app turns this
            # into "try a few steps nearer".
            if memory.place.coordinates is not None:
                memory.distance_meters = meters_between(at, memory.place.coordinates)
            return memory

        touch_device(session, body.device)
        session.execute(
            text("""
                INSERT INTO unlocks (device_id, memory_id)
                VALUES (CAST(:device AS uuid), :memory_id)
                ON CONFLICT (device_id, memory_id) DO NOTHING
            """),
            {"device": body.device, "memory_id": memory_id},
        )

    return memory


@app.get("/v1/unlocks", response_model=UnlocksResponse)
def get_unlocks(
    device: str = Query(..., pattern=DEVICE_PATTERN),
    limit: int = Query(200, ge=1, le=500),
):
    """What this device has earned.

    Returned unlocked regardless of where the caller is now: re-locking
    something somebody stood in the rain for is a punishment for leaving. The
    device id is the proof, and it is proof of nothing except that this app
    installation was there.
    """
    with get_session() as session:
        rows = session.execute(
            text(DEVICE_UNLOCKS_QUERY), {"device_id": device, "limit": limit}
        ).fetchall()

    # row_to_memory would lock these again - it has no idea they were earned.
    return UnlocksResponse(
        memories=[row_to_memory(row, row_coordinates(row), include_distance=False) for row in rows]
    )


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


# ---------------------------------------------------------------------------
# Writing. Everything above this line reads a corpus somebody else produced.
#
# There is still no account. A user is a display name and a uuid, claimed by a
# device the same way its unlocks are, and the device id is the only credential
# there is - so this authenticates nobody and is not pretending to. What it does
# buy is a stable name to sign a submission with, a row for Google/Apple sign-in
# to attach to later, and a subject for a report to be about.
#
# ponytail: the device id is a bearer token in the request body. Anyone who has
# yours can post as you. That is the same threat model as the unlock's
# self-reported position, and it is what OAuth replaces.
# ---------------------------------------------------------------------------

# A submitted memory mints its own place. Not reusing one by name: two people
# filing at the same cafe would otherwise fight over whose spelling of it wins,
# and the map groups by coordinate anyway, so they land under one pin regardless.
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
    extraction_confidence, layer, happened_at, happened_precision, user_id
)
VALUES (
    :place_id, NULL, NULL, :summary, CAST(:tags AS varchar[]),
    'high', 'stranger', :happened_at, :happened_precision, CAST(:user_id AS uuid)
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

# What a person is allowed to say about where they were. Free text would be a
# tag soup of one-offs within a week; this is the set the corpus already uses.
SUBMISSION_TAGS = [
    "food",
    "drink",
    "music",
    "art",
    "history",
    "nature",
    "sport",
    "nightlife",
    "work",
    "family",
    "strange",
]

# A phone's GPS is good to a few tens of metres in the open and worse between
# buildings. Claiming better would be the same lie the extraction prompt was
# rewritten to stop telling.
SUBMITTED_PRECISION_METERS = 25


class Profile(BaseModel):
    """What this device is, to the extent it is anybody.

    user_id is null until the person does something that needs one - the first
    submission, or naming themselves. Reading the profile does not create one.
    """

    user_id: str | None = None
    display_name: str | None = None
    submitted: int = 0
    unlocked: int = 0


class ProfileRequest(BaseModel):
    device: str = Field(pattern=DEVICE_PATTERN)
    # Blank clears it back to Anonymous, which has to be possible: a name is the
    # one thing here that other people see.
    display_name: str = Field(max_length=60)


class SubmissionRequest(BaseModel):
    """One memory, filed by the person who was standing there.

    lat/lng is both where they are and where the memory goes - one coordinate,
    because two would only ever be used to file something somewhere else.
    """

    device: str = Field(pattern=DEVICE_PATTERN)
    lat: float = Field(ge=-90, le=90)
    lng: float = Field(ge=-180, le=180)
    place_name: str = Field(min_length=1, max_length=200)
    # Ten characters is not a quality bar, it is a fat-finger bar.
    summary: str = Field(min_length=10, max_length=2000)
    tags: list[str] = Field(default_factory=list, max_length=8)
    happened_at: date | None = None
    happened_precision: str | None = Field(None, pattern="^(day|month|year|decade)$")
    media_ids: list[int] = Field(default_factory=list, max_length=6)
    # Sent with the submission rather than requiring a separate profile call, so
    # signing your first memory is one request.
    display_name: str | None = Field(None, max_length=60)


class ReportRequest(BaseModel):
    device: str = Field(pattern=DEVICE_PATTERN)
    reason: str | None = Field(None, max_length=40)


class ReportResponse(BaseModel):
    reports: int
    hidden: bool


def user_for_device(session, device: str) -> str:
    """The user this device acts as, creating one the first time it needs to.

    Created lazily and never on a read: a device that only ever walks around
    unlocking things should not leave a user row behind.
    """
    touch_device(session, device)
    existing = session.execute(
        text("SELECT user_id FROM devices WHERE id = CAST(:id AS uuid)"), {"id": device}
    ).scalar()
    if existing is not None:
        return str(existing)

    fresh = str(uuid.uuid4())
    session.execute(text("INSERT INTO users (id) VALUES (CAST(:id AS uuid))"), {"id": fresh})
    session.execute(
        text("UPDATE devices SET user_id = CAST(:user AS uuid) WHERE id = CAST(:id AS uuid)"),
        {"user": fresh, "id": device},
    )
    return fresh


def set_display_name(session, user_id: str, name: str | None) -> None:
    """Separate from user_for_device because None is two different answers.

    A submission that carries no name is saying nothing about it and must leave
    the existing one alone; a PUT with a blank one is saying "stop calling me
    that", and clearing it has to be possible - the name is the one thing here
    other people see.
    """
    session.execute(
        text("UPDATE users SET display_name = :name WHERE id = CAST(:id AS uuid)"),
        {"name": name, "id": user_id},
    )


def clean_name(raw: str | None) -> str | None:
    """Blank and whitespace are the same thing as not being named."""
    name = (raw or "").strip()
    return name or None


def clean_tags(raw: list[str]) -> list[str]:
    """Lowercased, deduplicated, and only from the known set.

    Dropping an unknown tag rather than rejecting the submission: the tags are a
    filing convenience and losing one is not worth losing the memory.
    """
    seen = []
    for tag in raw:
        normalized = tag.strip().lower()
        if normalized in SUBMISSION_TAGS and normalized not in seen:
            seen.append(normalized)
    return seen


@app.get("/v1/me", response_model=Profile)
def get_profile(device: str = Query(..., pattern=DEVICE_PATTERN)):
    """Who this device is and what it has done. Creates nothing."""
    with get_session() as session:
        row = session.execute(
            text("""
                SELECT u.id, u.display_name,
                    (SELECT COUNT(*) FROM memories m WHERE m.user_id = u.id) AS submitted
                FROM devices d JOIN users u ON d.user_id = u.id
                WHERE d.id = CAST(:id AS uuid)
            """),
            {"id": device},
        ).fetchone()
        unlocked = session.execute(
            text("SELECT COUNT(*) FROM unlocks WHERE device_id = CAST(:id AS uuid)"),
            {"id": device},
        ).scalar()

    if not row:
        return Profile(unlocked=unlocked or 0)
    return Profile(
        user_id=str(row.id),
        display_name=row.display_name,
        submitted=row.submitted,
        unlocked=unlocked or 0,
    )


@app.put("/v1/me", response_model=Profile)
def set_profile(body: ProfileRequest):
    """Name yourself, or stop being named. This is the one call that creates a
    user without a submission attached, because choosing the name before writing
    the memory is the order people do it in."""
    with get_session() as session:
        user_id = user_for_device(session, body.device)
        set_display_name(session, user_id, clean_name(body.display_name))
        submitted = session.execute(
            text("SELECT COUNT(*) FROM memories WHERE user_id = CAST(:id AS uuid)"),
            {"id": user_id},
        ).scalar()
        unlocked = session.execute(
            text("SELECT COUNT(*) FROM unlocks WHERE device_id = CAST(:id AS uuid)"),
            {"id": body.device},
        ).scalar()

    return Profile(
        user_id=user_id,
        display_name=clean_name(body.display_name),
        submitted=submitted or 0,
        unlocked=unlocked or 0,
    )


@app.post("/v1/media", response_model=MediaItem, status_code=201)
async def upload_media(
    # Annotation-only, which is how FastAPI recognises an upload; File(...) in a
    # default is the same thing and ruff's B008 rejects it.
    file: UploadFile,
    device: str = Form(..., pattern=DEVICE_PATTERN),
    duration_seconds: float | None = Form(None, ge=0, le=600),
):
    """Take one photo or recording and hold it until a submission claims it.

    Separate from the submission itself because a phone uploads a 4 MB photo
    while the person is still typing, and because a failed upload should cost
    the text nothing. api/media.py does the deciding about what a file may be.
    """
    path, kind, mime, size = await save_upload(file)

    with get_session() as session:
        touch_device(session, device)
        media_id = session.execute(
            text("""
                INSERT INTO media (device_id, kind, path, mime, bytes, duration_seconds)
                VALUES (CAST(:device AS uuid), :kind, :path, :mime, :bytes, :duration)
                RETURNING id
            """),
            {
                "device": device,
                "kind": kind,
                "path": path,
                "mime": mime,
                "bytes": size,
                # Only meaningful for audio, and only the client knows it - the
                # server does not decode the file to find out.
                "duration": duration_seconds if kind == "audio" else None,
            },
        ).scalar()

    return MediaItem(
        id=media_id,
        kind=kind,
        url=media_url(path),
        duration_seconds=duration_seconds if kind == "audio" else None,
    )


@app.post("/v1/memories", response_model=Memory, status_code=201)
def submit_memory(body: SubmissionRequest):
    """File a memory of where you are standing.

    It lands in the `stranger` layer, gated like everything else with a real
    coordinate - including for the person who wrote it, which is why the unlock
    is recorded here too. Filing something is standing there, so re-locking it
    the moment they walk away would be absurd.
    """
    tags = clean_tags(body.tags)
    # A date with no stated precision is a full date, which is what a phone's
    # date picker produces; the field exists for the 1978 case.
    precision = body.happened_precision or ("day" if body.happened_at else None)

    with get_session() as session:
        user_id = user_for_device(session, body.device)
        if body.display_name is not None:
            set_display_name(session, user_id, clean_name(body.display_name))

        place_id = session.execute(
            text(PLACE_INSERT),
            {
                "name": body.place_name.strip(),
                "place_query": f"user:{uuid.uuid4()}",
                "lat": body.lat,
                "lng": body.lng,
                "precision_meters": SUBMITTED_PRECISION_METERS,
            },
        ).scalar()

        memory_id = session.execute(
            text(SUBMISSION_INSERT),
            {
                "place_id": place_id,
                "summary": body.summary.strip(),
                "tags": tags,
                "happened_at": body.happened_at,
                "happened_precision": precision,
                "user_id": user_id,
            },
        ).scalar()

        if body.media_ids:
            attached = session.execute(
                text(MEDIA_ATTACH),
                {"memory_id": memory_id, "ids": body.media_ids, "device": body.device},
            ).rowcount
            if attached != len(set(body.media_ids)):
                # Silently posting a memory without the photograph somebody
                # chose is worse than refusing: they would never know.
                raise HTTPException(
                    status_code=400, detail="Some attachments are unknown or already used"
                )

        session.execute(
            text("""
                INSERT INTO unlocks (device_id, memory_id)
                VALUES (CAST(:device AS uuid), :memory_id)
                ON CONFLICT (device_id, memory_id) DO NOTHING
            """),
            {"device": body.device, "memory_id": memory_id},
        )

        row = session.execute(text(SINGLE_MEMORY_QUERY), {"memory_id": memory_id}).fetchone()

    return row_to_memory(row, Coordinates(lat=body.lat, lng=body.lng), include_distance=False)


@app.post("/v1/memories/{memory_id}/report", response_model=ReportResponse)
def report_memory(memory_id: int, body: ReportRequest):
    """Say this should not be here.

    One report per device, counted rather than acted on individually, and at
    REPORT_THRESHOLD the memory stops being served by every endpoint at once.
    The row stays: a takedown that destroys the evidence makes the next dispute
    unanswerable.
    """
    with get_session() as session:
        exists = session.execute(
            text("SELECT 1 FROM memories WHERE id = :id"), {"id": memory_id}
        ).scalar()
        if not exists:
            raise HTTPException(status_code=404, detail="Memory not found")

        touch_device(session, body.device)
        session.execute(
            text("""
                INSERT INTO reports (memory_id, device_id, reason)
                VALUES (:memory_id, CAST(:device AS uuid), :reason)
                ON CONFLICT (memory_id, device_id) DO NOTHING
            """),
            {"memory_id": memory_id, "device": body.device, "reason": body.reason},
        )
        count = session.execute(
            text("SELECT COUNT(*) FROM reports WHERE memory_id = :id"), {"id": memory_id}
        ).scalar()

        hidden = count >= REPORT_THRESHOLD
        if hidden:
            session.execute(
                text("UPDATE memories SET hidden = TRUE WHERE id = :id"), {"id": memory_id}
            )

    return ReportResponse(reports=count, hidden=hidden)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
