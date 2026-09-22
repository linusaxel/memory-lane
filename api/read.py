"""Reading the corpus. Nothing here writes, and nothing here unlocks.

The list endpoints never pass a position to `row_to_memory`: walking into range
must *offer* the unlock, not perform it, or there is no moment to press.
"""

import os
import time

from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import text

from api import gate
from api.gate import (
    UNLOCK_RADIUS_METERS,
    meters_between,
    row_coordinates,
    row_to_memory,
    viewer_position,
)
from api.models import (
    DEVICE_PATTERN,
    Coordinates,
    Hotspot,
    Memory,
    MyMemoriesMeta,
    MyMemoriesResponse,
    NearbyMeta,
    NearbyResponse,
    PlacesResponse,
    PlaceWithCount,
    SearchMeta,
    SearchResponse,
    Stats,
    UnlocksResponse,
)
from api.queries import (
    COUNT_QUERY,
    COUNT_WITH_TAGS_QUERY,
    DEVICE_UNLOCKS_QUERY,
    HOTSPOTS_QUERY,
    MY_MEMORIES_COUNT_QUERY,
    MY_MEMORIES_QUERY,
    NEARBY_MEMORIES_QUERY,
    NEARBY_MEMORIES_WITH_TAGS_QUERY,
    NEARBY_PLACES_QUERY,
    PLACES_COUNT_QUERY,
    SEARCH_COUNT_QUERY,
    SEARCH_COUNT_WITH_LOCATION_QUERY,
    SEARCH_MEMORIES_QUERY,
    SEARCH_MEMORIES_WITH_LOCATION_QUERY,
    SINGLE_MEMORY_QUERY,
)
from pipeline.db import get_session

router = APIRouter()


@router.get("/v1/memories/nearby", response_model=NearbyResponse)
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


@router.get("/v1/memories/search", response_model=SearchResponse)
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


@router.get("/v1/memories/{memory_id}", response_model=Memory)
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


@router.get("/v1/places/nearby", response_model=PlacesResponse)
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
                sample_memory=None if gate.is_gated(row) else row.sample_memory,
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


@router.get("/v1/unlocks", response_model=UnlocksResponse)
def get_unlocks(
    device: str = Query(..., pattern=DEVICE_PATTERN),
    limit: int = Query(200, ge=1, le=500),
):
    """What this device, and anything signed in alongside it, has earned.

    Returned unlocked regardless of where the caller is now: re-locking
    something somebody stood in the rain for is a punishment for leaving.
    """
    with get_session() as session:
        rows = session.execute(
            text(DEVICE_UNLOCKS_QUERY), {"device_id": device, "limit": limit}
        ).fetchall()

    # row_to_memory would lock these again - it has no idea they were earned.
    return UnlocksResponse(
        memories=[row_to_memory(row, row_coordinates(row), include_distance=False) for row in rows]
    )


@router.get("/v1/me/memories", response_model=MyMemoriesResponse)
def get_my_memories(
    device: str = Query(..., pattern=DEVICE_PATTERN),
    limit: int = Query(200, ge=1, le=500),
    offset: int = Query(0, ge=0, description="Pagination offset"),
):
    """Everything this account has filed, newest first - including memories
    reported by others (hidden) and memories still sealed. Neither is a reason
    to hide a memory from the one screen that manages it; row_to_memory still
    renders a sealed one as shut, seal included, the author included.

    Paginated like /v1/memories/nearby - a filer past `limit` gets more by
    asking again with a higher `offset`, not by being silently cut off.
    """
    with get_session() as session:
        rows = session.execute(
            text(MY_MEMORIES_QUERY), {"device": device, "limit": limit, "offset": offset}
        ).fetchall()
        total = session.execute(text(MY_MEMORIES_COUNT_QUERY), {"device": device}).scalar()

    return MyMemoriesResponse(
        memories=[row_to_memory(row, row_coordinates(row), include_distance=False) for row in rows],
        meta=MyMemoriesMeta(total=total, limit=limit, offset=offset),
    )


# How long an answer to /v1/stats is allowed to be old.
#
# That endpoint is four unbounded counts and a DBSCAN over every placed memory
# in the corpus - ST_ClusterDBSCAN(...) OVER () is one partition, so there is
# no index to help and no filter to shrink it. It also happens to be the
# endpoint every phone calls when the map comes back empty, which is most of
# the planet, so the cheapest way to make the corpus look big is to stand
# somewhere it is not.
#
# None of its answers change between pipeline runs. Caching them is not a
# micro-optimisation, it is the difference between a query whose cost grows
# with the corpus running once per request and running once per window.
STATS_TTL_SECONDS = int(os.getenv("STATS_TTL_SECONDS", "300"))

#: {hotspot count: (monotonic seconds, answer)}. Keyed because the count is a
#: query parameter, and small because it is bounded at 21 values.
_stats_cache: dict[int, tuple[float, Stats]] = {}


def reset_stats_cache() -> None:
    """Tests share a process and would otherwise read each other's answers."""
    _stats_cache.clear()


@router.get("/v1/stats", response_model=Stats)
def get_stats(
    hotspots: int = Query(5, ge=0, le=20, description="How many of the busiest areas to name"),
):
    """Database statistics, and where the memories actually are.

    The second part is not a statistic, it is the answer to an empty map. The
    corpus is one comedy podcast's touring history, so it is New York and then a
    long tail - and somebody opening this in Copenhagen sees nothing at all.

    Served from a short-lived cache; see STATS_TTL_SECONDS for why.
    """
    now = time.monotonic()
    cached = _stats_cache.get(hotspots)
    if cached is not None and now - cached[0] < STATS_TTL_SECONDS:
        return cached[1]

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

    stats = Stats(
        memories=memories_count,
        unlock_radius_meters=UNLOCK_RADIUS_METERS,
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
    # Last write wins. Two threads can compute this at once and the loser has
    # simply done some work twice, which is cheaper than holding a lock across
    # a query this long.
    _stats_cache[hotspots] = (now, stats)
    return stats
