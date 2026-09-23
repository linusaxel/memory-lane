"""Reading the corpus. Nothing here unlocks.

The list endpoints never pass a position to `row_to_memory`: walking into range
must *offer* the unlock, not perform it, or there is no moment to press.

One exception to the "nothing here writes" this file used to be able to claim:
GET /v1/routes/today stores a route the first time a device asks for one each
day, so the same relaunch sees the same route rather than a fresh roll. It
still never records an unlock - that stays write.py's alone.
"""

import itertools
import os
import random
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
    Coordinates,
    Hotspot,
    Memory,
    MyMemoriesMeta,
    MyMemoriesResponse,
    NearbyMeta,
    NearbyResponse,
    PlacesResponse,
    PlaceWithCount,
    RouteMeta,
    RouteResponse,
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
    ROUTE_CANDIDATES_QUERY,
    ROUTE_QUERY,
    SEARCH_COUNT_QUERY,
    SEARCH_COUNT_WITH_LOCATION_QUERY,
    SEARCH_MEMORIES_QUERY,
    SEARCH_MEMORIES_WITH_LOCATION_QUERY,
    SINGLE_MEMORY_QUERY,
)
from pipeline.db import get_session

router = APIRouter()

# 5 stops. 4000m is about a 45-50 minute round trip on foot - wide enough to
# find that many outside a dense corpus without turning a walk into a commute.
ROUTE_SIZE = int(os.getenv("ROUTE_SIZE", "5"))
ROUTE_RADIUS_METERS = int(os.getenv("ROUTE_RADIUS_METERS", "4000"))


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


def _one_per_place(candidates: list) -> list:
    """The map groups pins by coordinate, not by memory - `stack` in
    pipeline/seed_dev.py is three memories on one place. Two of them picked as
    separate route stops would be one pin asked to show two different numbers,
    which is not renderable. Keeping the first (nearest, since the query is
    already distance-ordered) per `place_id` makes a route stop a place, the
    same unit the pin already is."""
    seen: set[int] = set()
    out = []
    for row in candidates:
        if row.place_id in seen:
            continue
        seen.add(row.place_id)
        out.append(row)
    return out


# Rounds of drop-and-reinsert after the first greedy walk. Twenty candidates,
# so this is a few milliseconds.
ROUTE_SHAKES = 50


def _choose_stops(candidates: list, size: int, anchor: Coordinates, seed: str) -> list:
    """The `size` stops that make the shortest walk from the anchor, not the
    `size` nearest: a stop 300m behind you no longer beats a tight cluster 500m
    ahead. Cheapest insertion builds a walk, then ROUTE_SHAKES rounds drop one
    or two stops at random and reinsert the cheapest, keeping whichever walk is
    shorter (iterated local search). Seeded, so one device on one day always
    gets the same answer.

    Each of stranger/other is guaranteed min(available, size // 2) stops, which
    is what the strict alternation before this gave, and still never comes up
    short when one layer runs dry.
    ponytail: every stop is worth the same, so this only minimises metres
    (TODO.md, "Give stops a prize")."""
    points = [anchor] + [Coordinates(lat=r.lat, lng=r.lng) for r in candidates]
    d = [[meters_between(a, b) for b in points] for a in points]
    nodes = range(1, len(points))
    size = min(size, len(candidates))
    stranger = {i: candidates[i - 1].layer == "stranger" for i in nodes}
    quota = {k: min(sum(v == k for v in stranger.values()), size // 2) for k in (True, False)}

    def fits(walk, c):
        after = [stranger[i] for i in walk] + [stranger[c]]
        missing = sum(max(0, q - after.count(k)) for k, q in quota.items())
        return missing <= size - len(after)

    def cost(walk, c, at):
        prev = walk[at - 1] if at else 0
        if at == len(walk):
            return d[prev][c]
        return d[prev][c] + d[c][walk[at]] - d[prev][walk[at]]

    def fill(walk):
        while len(walk) < size:
            _, c, at = min(
                (cost(walk, c, at), c, at)
                for c in nodes
                if c not in walk and fits(walk, c)
                for at in range(len(walk) + 1)
            )
            walk.insert(at, c)
        return walk

    def length(walk):
        return sum(d[a][b] for a, b in itertools.pairwise([0, *walk]))

    rng = random.Random(seed)
    best = fill([])
    for _ in range(ROUTE_SHAKES if size else 0):
        drop = set(rng.sample(best, rng.randint(1, min(2, size))))
        trial = fill([i for i in best if i not in drop])
        if length(trial) < length(best):
            best = trial
    return [candidates[i - 1] for i in best]


# 8! is 40,320 orderings - still cheaper than the SQL round trip before it.
EXACT_ORDER_MAX = 8


def _path_meters(anchor: Coordinates, stops) -> float:
    total, here = 0.0, anchor
    for r in stops:
        there = Coordinates(lat=r.lat, lng=r.lng)
        total += meters_between(here, there)
        here = there
    return total


def _walking_order(picks: list, anchor: Coordinates) -> list:
    """The shortest open walk from the anchor through every pick, by trying
    every ordering. Five stops is 120 of them, and nearest-neighbour - what this
    was - doubles back whenever the closest stop is behind you.
    ponytail: exact up to EXACT_ORDER_MAX, greedy above it; Held-Karp if
    ROUTE_SIZE ever grows that far (TODO.md, "Order the stops exactly")."""
    if len(picks) <= EXACT_ORDER_MAX:
        return list(min(itertools.permutations(picks), key=lambda p: _path_meters(anchor, p)))
    remaining = list(picks)
    ordered = []
    here = anchor
    while remaining:
        nxt = min(remaining, key=lambda r: meters_between(here, Coordinates(lat=r.lat, lng=r.lng)))
        ordered.append(nxt)
        remaining.remove(nxt)
        here = Coordinates(lat=nxt.lat, lng=nxt.lng)
    return ordered


ROUTE_LOOKUP = """
    SELECT memory_ids, radius_meters FROM daily_routes
    WHERE device_id = CAST(:device AS uuid) AND route_date = :route_date
"""

ROUTE_INSERT = """
    INSERT INTO daily_routes (device_id, route_date, memory_ids, radius_meters)
    VALUES (CAST(:device AS uuid), :route_date, CAST(:ids AS integer[]), :radius_meters)
    ON CONFLICT (device_id, route_date) DO NOTHING
"""

# 500m is about the shortest walk that can still separate distinct stops;
# 20km is already a long day's outing, well past what "a route" implies.
ROUTE_RADIUS_MIN_METERS = 500
ROUTE_RADIUS_MAX_METERS = 20_000


@router.get("/v1/routes/today", response_model=RouteResponse)
def get_todays_route(
    device: str = Query(..., pattern=DEVICE_PATTERN),
    lat: float | None = Query(
        None, ge=-90, le=90, description="Required only to start today's route"
    ),
    lng: float | None = Query(
        None, ge=-180, le=180, description="Required only to start today's route"
    ),
    radius_meters: int | None = Query(
        None,
        ge=ROUTE_RADIUS_MIN_METERS,
        le=ROUTE_RADIUS_MAX_METERS,
        description="Required only to start today's route; defaults to ROUTE_RADIUS_METERS",
    ),
):
    """A fixed set of nearby, not-yet-earned stops for today, mixing layers.

    Computed once per device per calendar day and stored, so a relaunch sees
    the same route rather than a fresh roll of the dice - there is no stored
    home location anywhere in this schema, so lat/lng/radius_meters only
    matter on the day's first call, which is the only one with anywhere to
    anchor a route on.
    """
    route_date = gate.today()

    with get_session() as session:
        row = session.execute(
            text(ROUTE_LOOKUP), {"device": device, "route_date": route_date}
        ).fetchone()

        if row is None:
            if lat is None or lng is None:
                raise HTTPException(
                    status_code=400, detail="lat/lng are required to start today's route"
                )
            search_radius = radius_meters if radius_meters is not None else ROUTE_RADIUS_METERS

            candidates = session.execute(
                text(ROUTE_CANDIDATES_QUERY),
                {
                    "lat": lat,
                    "lng": lng,
                    "radius_meters": search_radius,
                    "today": route_date,
                    "device_id": device,
                    "limit": 4 * ROUTE_SIZE,
                },
            ).fetchall()

            anchor = Coordinates(lat=lat, lng=lng)
            picked = _walking_order(
                _choose_stops(
                    _one_per_place(candidates), ROUTE_SIZE, anchor, f"{device}:{route_date}"
                ),
                anchor,
            )
            memory_ids = [r.id for r in picked]
            # An empty route is not stored: stored, it would pin the whole day
            # to "nothing here" even after the device reaches somewhere stocked.
            if not memory_ids:
                return RouteResponse(
                    memories=[],
                    meta=RouteMeta(route_date=route_date, size=0, radius_meters=search_radius),
                )

            touch_device(session, device)
            session.execute(
                text(ROUTE_INSERT),
                {
                    "device": device,
                    "route_date": route_date,
                    "ids": memory_ids,
                    "radius_meters": search_radius,
                },
            )
            # Somebody else's first call this second may have won the race -
            # read back whichever array actually landed.
            row = session.execute(
                text(ROUTE_LOOKUP), {"device": device, "route_date": route_date}
            ).fetchone()

        memory_ids = list(row.memory_ids)
        rows = (
            session.execute(text(ROUTE_QUERY), {"ids": memory_ids}).fetchall() if memory_ids else []
        )

    # No position: these are freshly discovered, unwalked stops, and rendering
    # them locked is the point - the same rule every other list endpoint here
    # follows for exactly this reason.
    by_id = {r.id: row_to_memory(r) for r in rows}
    memories = [by_id[i] for i in memory_ids if i in by_id]

    return RouteResponse(
        memories=memories,
        meta=RouteMeta(
            route_date=route_date, size=len(memory_ids), radius_meters=row.radius_meters
        ),
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
