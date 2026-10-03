"""Reading the corpus. Nothing here unlocks.

The list endpoints never pass a position to `row_to_memory`: walking into range
must *offer* the unlock, not perform it, or there is no moment to press.

The exceptions to "nothing here writes": POST /v1/routes/today stores the walk
a device accepts, next to the preview (both call api/route_solver.py),
POST /v1/routes/today/skip drops a stop from it, and POST /v1/routes/today/end
ends it. None records an unlock - that stays write.py's alone.
"""

import json
import os
import time

from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import text

from api import gate
from api.accounts import touch_device
from api.gate import (
    UNLOCK_RADIUS_METERS,
    meters_between,
    row_coordinates,
    row_to_memory,
    viewer_position,
)
from api.models import (
    DEVICE_PATTERN,
    ROUTE_AGAIN_MAX,
    ROUTE_BUDGET_MAX_METERS,
    ROUTE_BUDGET_MIN_METERS,
    AuthoredRouteResponse,
    Coordinates,
    DeviceRequest,
    Hotspot,
    Memory,
    MyMemoriesMeta,
    MyMemoriesResponse,
    NearbyMeta,
    NearbyResponse,
    NotesResponse,
    PlacesResponse,
    PlaceWithCount,
    RouteMeta,
    RouteRequest,
    RouteResponse,
    SearchMeta,
    SearchResponse,
    SkipRequest,
    Stats,
    UnlocksResponse,
    WalkedMeta,
    WalkedResponse,
    WalkedRoute,
)
from api.queries import (
    AUTHORED_ROUTE_QUERY,
    AUTHORED_ROUTE_STOPS_QUERY,
    COUNT_QUERY,
    COUNT_WITH_TAGS_QUERY,
    DEVICE_UNLOCKS_QUERY,
    EARNED_QUERY,
    HOTSPOTS_QUERY,
    MEMORY_NOTES_QUERY,
    MY_MEMORIES_COUNT_QUERY,
    MY_MEMORIES_QUERY,
    NEARBY_MEMORIES_QUERY,
    NEARBY_MEMORIES_WITH_TAGS_QUERY,
    NEARBY_PLACES_QUERY,
    NOTE_ALLOWED_QUERY,
    PLACES_COUNT_QUERY,
    ROUTE_COMPLETED_QUERY,
    ROUTE_PRUNE,
    ROUTE_QUERY,
    SEARCH_COUNT_QUERY,
    SEARCH_COUNT_WITH_LOCATION_QUERY,
    SEARCH_MEMORIES_QUERY,
    SEARCH_MEMORIES_WITH_LOCATION_QUERY,
    SINGLE_MEMORY_QUERY,
    SUBSCRIBED_QUERY,
    WALKED_QUERY,
    WALKED_STOPS_QUERY,
    WALKED_TODAY_QUERY,
)
from api.route_solver import ROUTE_LOOP, _plan_route
from pipeline.config import UNLIMITED_WALKS
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
    device: str | None = Query(
        None, pattern=DEVICE_PATTERN, description="Leaves out who it blocked"
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
            "device_id": device,
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
        result = session.execute(
            text(SINGLE_MEMORY_QUERY), {"memory_id": memory_id, "device_id": None}
        )
        row = result.fetchone()

    if not row:
        raise HTTPException(status_code=404, detail="Memory not found")

    at = viewer_position(at_lat, at_lng)
    memory = row_to_memory(row, at, include_distance=False)
    if memory.locked and at is not None and memory.place.coordinates is not None:
        # It failed the gate, so say by how much rather than just refusing.
        memory.distance_meters = meters_between(at, memory.place.coordinates)
    return memory


@router.get("/v1/memories/{memory_id}/notes", response_model=NotesResponse)
def get_notes(memory_id: int, device: str = Query(..., pattern=DEVICE_PATTERN)):
    """The notes on a memory, oldest first, for anyone who has unlocked it. A
    note can quote the memory, so it stays behind the same gate; everyone else
    gets `note_count` on the memory and nothing more.
    """
    params = {"memory_id": memory_id, "device_id": device}
    with get_session() as session:
        if not session.execute(text(NOTE_ALLOWED_QUERY), params).scalar():
            raise HTTPException(status_code=403, detail="Stand here first")
        rows = session.execute(text(MEMORY_NOTES_QUERY), params).fetchall()
    return gate.notes_response(rows)


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


ROUTE_LOOKUP = """
    SELECT memory_ids, budget_meters, legs, loop FROM daily_routes
    WHERE device_id = CAST(:device AS uuid) AND route_date = :route_date AND ended_at IS NULL
"""

ROUTE_INSERT = """
    INSERT INTO daily_routes (device_id, route_date, memory_ids, budget_meters, legs, loop)
    VALUES (
        CAST(:device AS uuid), :route_date, CAST(:ids AS integer[]), :budget_meters,
        CAST(:legs AS jsonb), :loop
    )
    ON CONFLICT (device_id, route_date) WHERE ended_at IS NULL DO NOTHING
"""

ROUTE_END = """
    UPDATE daily_routes SET ended_at = CURRENT_TIMESTAMP
    WHERE device_id = CAST(:device AS uuid) AND route_date = :route_date AND ended_at IS NULL
"""


ROUTE_SKIP_LOOKUP = ROUTE_LOOKUP.rstrip() + " FOR UPDATE"

ROUTE_SKIP = """
    UPDATE daily_routes SET memory_ids = CAST(:ids AS integer[]), legs = CAST(:legs AS jsonb)
    WHERE device_id = CAST(:device AS uuid) AND route_date = :route_date AND ended_at IS NULL
"""


def _route_response(
    route_date, rows, memory_ids, budget_meters, legs, loop, ends=None, earned=frozenset()
) -> RouteResponse:
    # No position: these are unwalked stops, and rendering them locked is the
    # point - the same rule every other list endpoint here follows. `earned`
    # stops are forced open, the way get_unlocks does it.
    by_id = {r.id: row_to_memory(r, row_coordinates(r) if r.id in earned else None) for r in rows}
    memories = [by_id[i] for i in memory_ids if i in by_id]
    return RouteResponse(
        memories=memories,
        meta=RouteMeta(
            route_date=route_date,
            size=len(memory_ids),
            budget_meters=budget_meters,
            loop=loop,
            # A stop hidden since would shift every leg after it onto the wrong
            # pair; straight lines are the honest fallback.
            legs=legs if len(memories) == len(memory_ids) else None,
            out_leg=ends and ends["out"],
            home_leg=ends and ends["home"],
        ),
    )


def _refuse_second_walk(session, device: str, route_date) -> None:
    """One walk a day per account; a subscriber has no limit (docs/10, "A walk
    planner, nothing else"). A walk's stops are the only thing that opens, so
    without it End walk and plan again would open any memory for nothing."""
    if UNLIMITED_WALKS:
        return
    binds = {"device_id": device, "today": route_date}
    if session.execute(text(WALKED_TODAY_QUERY), binds).scalar() and not (
        session.execute(text(SUBSCRIBED_QUERY), binds).scalar()
    ):
        raise HTTPException(status_code=403, detail={"reason": "walked_today"})


def _legs_json(legs):
    return [[c.model_dump() for c in leg] for leg in legs] if legs else None


@router.get("/v1/routes/preview", response_model=RouteResponse)
def preview_route(
    device: str = Query(..., pattern=DEVICE_PATTERN),
    lat: float = Query(..., ge=-90, le=90),
    lng: float = Query(..., ge=-180, le=180),
    budget_meters: int = Query(..., ge=ROUTE_BUDGET_MIN_METERS, le=ROUTE_BUDGET_MAX_METERS),
    loop: bool = Query(ROUTE_LOOP),
    again: int = Query(0, ge=0, le=ROUTE_AGAIN_MAX),
    end_lat: float | None = Query(None, ge=-90, le=90),
    end_lng: float | None = Query(None, ge=-180, le=180),
):
    """The walk POST /v1/routes/today would store, stored nowhere. A device that
    already accepted today's walk still gets a preview; accepting returns the
    walk it already has. `end_lat`/`end_lng` go together: where a one-way walk
    finishes."""
    if (end_lat is None) != (end_lng is None):
        raise HTTPException(status_code=422, detail="end_lat and end_lng go together")
    end = Coordinates(lat=end_lat, lng=end_lng) if end_lat is not None else None
    loop = loop and not end
    route_date = gate.today()
    with get_session() as session:
        _refuse_second_walk(session, device, route_date)
        picked, legs, ends = _plan_route(
            session,
            device,
            Coordinates(lat=lat, lng=lng),
            budget_meters,
            route_date,
            loop,
            again,
            end,
        )
    return _route_response(
        route_date, picked, [r.id for r in picked], budget_meters, _legs_json(legs), loop, ends
    )


@router.post("/v1/routes/today", response_model=RouteResponse)
def accept_route(body: RouteRequest):
    """Accept today's walk. One a day per account, bar a subscriber, and one in
    progress per device: the first accept is stored and every later one gets it
    back, whatever it asked for, until POST /v1/routes/today/end ends it.

    An empty walk is not stored: stored, it would pin the whole day to
    "nothing here" even after the device reaches somewhere stocked. Nor is an
    old one that opened nothing kept: this sweeps a past day's walk that was
    never ended."""
    route_date = gate.today()
    with get_session() as session:
        session.execute(text(ROUTE_PRUNE), {"device_id": body.device, "route_date": route_date})
        row = session.execute(
            text(ROUTE_LOOKUP), {"device": body.device, "route_date": route_date}
        ).fetchone()
        if row is None:
            _refuse_second_walk(session, body.device, route_date)
            loop = ROUTE_LOOP if body.loop is None else body.loop
            loop = loop and not body.end
            picked, legs, _ = _plan_route(
                session,
                body.device,
                Coordinates(lat=body.lat, lng=body.lng),
                body.budget_meters,
                route_date,
                loop,
                body.again,
                body.end,
            )
            if not picked:
                return _route_response(route_date, [], [], body.budget_meters, None, loop)
            touch_device(session, body.device)
            session.execute(
                text(ROUTE_INSERT),
                {
                    "device": body.device,
                    "route_date": route_date,
                    "ids": [r.id for r in picked],
                    "budget_meters": body.budget_meters,
                    "legs": json.dumps(_legs_json(legs)) if legs else None,
                    "loop": loop,
                },
            )
            # Somebody else's accept this second may have won the race - read
            # back whichever array actually landed.
            row = session.execute(
                text(ROUTE_LOOKUP), {"device": body.device, "route_date": route_date}
            ).fetchone()
        return _stored_route(session, route_date, row)


@router.post("/v1/routes/today/end", status_code=204)
def end_route(body: DeviceRequest):
    """End today's walk, finished or not, so another can be accepted. If it
    opened something its row stays: the journal lists it and what it earned
    still counts. If it opened nothing it is deleted. Its unearned stops lock
    again. Nothing to end is not an error: the same tap twice."""
    route_date = gate.today()
    with get_session() as session:
        session.execute(text(ROUTE_END), {"device": body.device, "route_date": route_date})
        session.execute(text(ROUTE_PRUNE), {"device_id": body.device, "route_date": route_date})


def _legs_without(legs, i: int):
    """legs[k] runs stop k to stop k+1. Dropping stop i joins the two legs
    through it, so the walk still follows streets, past the dropped spot."""
    if not legs:
        return legs
    if i == 0:
        return legs[1:]
    if i == len(legs):
        return legs[:-1]
    return legs[: i - 1] + [legs[i - 1] + legs[i][1:]] + legs[i + 1 :]


@router.post("/v1/routes/today/skip", response_model=RouteResponse)
def skip_stop(body: SkipRequest):
    """Drop a stop from today's walk without ending it (docs/10, "A stop can be
    dropped"). It leaves memory_ids, so the walk is finished without it and
    earns as a walk of one stop fewer. An opened stop, or the walk's only one,
    stays."""
    route_date = gate.today()
    binds = {"device": body.device, "route_date": route_date}
    with get_session() as session:
        row = session.execute(text(ROUTE_SKIP_LOOKUP), binds).fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="No walk accepted today")
        ids = list(row.memory_ids)
        if body.memory_id not in ids:
            raise HTTPException(status_code=404, detail={"reason": "not_on_walk"})
        earned = {"memory_id": body.memory_id, "device_id": body.device}
        if session.execute(text(EARNED_QUERY), earned).scalar():
            raise HTTPException(status_code=409, detail={"reason": "already_opened"})
        if len(ids) == 1:
            raise HTTPException(status_code=409, detail={"reason": "last_stop"})
        i = ids.index(body.memory_id)
        ids.pop(i)
        legs = _legs_without(row.legs, i)
        session.execute(
            text(ROUTE_SKIP),
            {**binds, "ids": ids, "legs": json.dumps(legs) if legs else None},
        )
        # The dropped stop may have been the last one owed.
        session.execute(
            text(ROUTE_COMPLETED_QUERY),
            {"device_id": body.device, "memory_id": ids[0], "today": route_date},
        )
        row = session.execute(text(ROUTE_LOOKUP), binds).fetchone()
        return _stored_route(session, route_date, row)


@router.get("/v1/routes/today", response_model=RouteResponse)
def get_todays_route(device: str = Query(..., pattern=DEVICE_PATTERN)):
    """Today's accepted walk, or 404 when this device has not accepted one."""
    route_date = gate.today()
    with get_session() as session:
        row = session.execute(
            text(ROUTE_LOOKUP), {"device": device, "route_date": route_date}
        ).fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="No walk accepted today")
        return _stored_route(session, route_date, row)


def _stored_route(session, route_date, row) -> RouteResponse:
    memory_ids = list(row.memory_ids)
    rows = session.execute(text(ROUTE_QUERY), {"ids": memory_ids}).fetchall()
    return _route_response(route_date, rows, memory_ids, row.budget_meters, row.legs, row.loop)


@router.get("/v1/routes/walked", response_model=WalkedResponse)
def get_walked_routes(
    device: str = Query(..., pattern=DEVICE_PATTERN),
    limit: int = Query(100, ge=1, le=500),
):
    """Every walk this account took that opened something, newest first. Earned
    stops come back open, like /v1/unlocks. The start was never stored, so a
    past loop draws stop to stop (docs/10-decisions.md § Routes)."""
    with get_session() as session:
        walks = session.execute(
            text(WALKED_QUERY), {"device_id": device, "limit": limit}
        ).fetchall()
        ids = sorted({i for w in walks for i in w.memory_ids})
        stops = {
            r.id: r
            for r in session.execute(
                text(WALKED_STOPS_QUERY), {"device_id": device, "ids": ids}
            ).fetchall()
        }
    earned = {i for i, r in stops.items() if r.earned}

    def walked(w) -> WalkedRoute:
        ids = list(w.memory_ids)
        rows = [stops[i] for i in ids if i in stops]
        route = _route_response(
            w.route_date, rows, ids, w.budget_meters, w.legs, w.loop, earned=earned
        )
        meta = route.meta.model_dump() | {"size": len(route.memories)}
        return WalkedRoute(
            memories=route.memories,
            meta=WalkedMeta(
                **meta,
                earned=sum(m.id in earned for m in route.memories),
                completed_at=w.completed_at,
            ),
        )

    return WalkedResponse(walks=[walked(w) for w in walks])


# After /today, /preview and /walked, which would otherwise read as an id.
@router.get("/v1/routes/{route_id}", response_model=AuthoredRouteResponse)
def get_authored_route(route_id: int):
    """An authored walk, or 404 while it is a draft."""
    with get_session() as session:
        route = session.execute(text(AUTHORED_ROUTE_QUERY), {"route_id": route_id}).fetchone()
        if route is None:
            raise HTTPException(status_code=404, detail="No such route")
        rows = session.execute(text(AUTHORED_ROUTE_STOPS_QUERY), {"route_id": route_id}).fetchall()
    return AuthoredRouteResponse(
        id=route.id,
        title=route.title,
        loop=route.is_loop,
        memories=[row_to_memory(r) for r in rows],
    )


@router.get("/v1/me/memories", response_model=MyMemoriesResponse)
def get_my_memories(
    device: str = Query(..., pattern=DEVICE_PATTERN),
    limit: int = Query(200, ge=1, le=500),
    offset: int = Query(0, ge=0, description="Pagination offset"),
):
    """Everything this account has filed, newest first - including memories
    reported by others (hidden), which is no reason to hide a memory from the
    one screen that manages it.

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
