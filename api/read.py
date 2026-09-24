"""Reading the corpus. Nothing here unlocks.

The list endpoints never pass a position to `row_to_memory`: walking into range
must *offer* the unlock, not perform it, or there is no moment to press.

One exception to "nothing here writes": POST /v1/routes/today stores the walk
a device accepts, next to the solver and the preview that share it. It never
records an unlock - that stays write.py's alone.
"""

import itertools
import json
import math
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
    ROUTE_BUDGET_MAX_METERS,
    ROUTE_BUDGET_MIN_METERS,
    AuthoredRouteResponse,
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
    RouteRequest,
    RouteResponse,
    SearchMeta,
    SearchResponse,
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
    WALKED_QUERY,
    WALKED_STOPS_QUERY,
)
from api.streets import retraced_meters, street_legs, street_table
from pipeline.db import get_session

router = APIRouter()

ROUTE_SIZE = int(os.getenv("ROUTE_SIZE", "5"))
# A loop ends back where the day's walk started, so its last leg is the walk
# home, and it is counted when choosing and ordering stops. ROUTE_LOOP=0 makes
# it one-way. The server never stores that start; the app remembers it.
ROUTE_LOOP = os.getenv("ROUTE_LOOP", "1") != "0"


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


# Rounds of drop-and-reinsert after the first walks. Forty candidates, so
# this is a few milliseconds.
ROUTE_SHAKES = 50
# A walk of at least this share of the slider counts as the walk asked for;
# below it, the shortfall is what ranks it. Seeded walks aim halfway between.
ROUTE_FILL = 0.8
# Headings tried for the seeded walks, each a different circle through the start.
ROUTE_HEADINGS = 8
# A turn sharper than this, on the map itself, is heading back the way it came.
SHARP_TURN_DEGREES = 45
# Walks as good on count and layer mix as the best one, handed to
# _plan_route to be routed on the streets and judged on what they retrace.
ROUTE_SHORTLIST = ROUTE_HEADINGS + 2


def _choose_stops(*args) -> list[int]:
    """_choose_walks' best walk, for callers without streets to judge by."""
    return _choose_walks(*args)[0]


def _choose_walks(
    candidates: list,
    size: int,
    d: list,
    seed: str,
    budget_meters: float,
    loop: bool,
    at: Coordinates,
) -> list[list[int]]:
    """Up to ROUTE_SHORTLIST walks of up to `size` stops from the anchor `at`
    within `budget_meters`, best first, ranked by: as many stops as fit, the
    layer mix, the fewest turns back on itself, the walk reaching ROUTE_FILL of
    the budget, the most prize, then the shortest walk. A long slider gets a long walk, not the five nearest
    stops in a knot. A stop's prize is 1 + contrast_score, so an unscored one
    is worth 1. Every walk on the list has the best one's count and mix.

    A turn back is a turn under SHARP_TURN_DEGREES on the map, at a stop or,
    for a loop, at the anchor. That is all a straight-line map can say; a
    street spur takes the street shapes, which is why there is a list and not
    one walk. Estimating it from the matrix was tried (docs/10-decisions.md)
    and gave long walks up for short ones.

    The first walks are shaped like the ask: for ROUTE_HEADINGS headings,
    targets on a circle through the anchor (a line, one-way) whose walk is the
    budget, and the candidate nearest each target. Insertion by prize per metre
    tops them up, and builds one more walk from nothing, which is what a sparse
    map falls back on. Then ROUTE_SHAKES rounds drop one or two stops at random
    and refill without them, keeping whichever walk scores better (iterated
    local search). Seeded, so one device on one day always gets the same answer.

    `d` is walking metres between nodes, node 0 the anchor and node i
    candidates[i - 1] (api.streets.walking_matrix). Returns nodes, unordered;
    [[]] when there is nothing to walk to.

    Each of stranger/other is guaranteed min(available, size // 2) stops, which
    is what the strict alternation before this gave, and still never comes up
    short when one layer runs dry or is out of budget.
    ponytail: layer is the only diversity term; MMR on tag overlap once prizes
    actually differ (TODO.md, "Give stops a prize")."""
    nodes = range(1, len(candidates) + 1)
    size = min(size, len(candidates))
    prize = {i: 1 + (getattr(candidates[i - 1], "contrast_score", None) or 0) for i in nodes}
    stranger = {i: candidates[i - 1].layer == "stranger" for i in nodes}
    quota = {k: min(sum(v == k for v in stranger.values()), size // 2) for k in (True, False)}

    def missing(walk):
        kinds = [stranger[i] for i in walk]
        return sum(max(0, q - kinds.count(k)) for k, q in quota.items())

    def fits(walk, c):
        return missing([*walk, c]) <= size - len(walk) - 1

    def cost(walk, c, at):
        prev = walk[at - 1] if at else 0
        nxt = walk[at] if at < len(walk) else 0 if loop else None
        if nxt is None:
            return d[prev][c]
        return d[prev][c] + d[c][nxt] - d[prev][nxt]

    def fill(walk, banned=frozenset()):
        while len(walk) < size:
            room = budget_meters - _path_meters(walk, d, loop)
            options = [
                (cost(walk, c, at), c, at)
                for c in nodes
                if c not in walk and c not in banned
                for at in range(len(walk) + 1)
            ]
            options = [o for o in options if o[0] <= room]
            if not options:
                break
            _, c, at = min(
                [o for o in options if fits(walk, o[1])] or options,
                key=lambda o: (-prize[o[1]] / max(o[0], 1), o),
            )
            walk.insert(at, c)
        return walk

    y = {0: 0.0} | {i: (candidates[i - 1].lat - at.lat) * 111_320 for i in nodes}
    x = {0: 0.0} | {
        i: (candidates[i - 1].lng - at.lng) * 111_320 * math.cos(math.radians(at.lat))
        for i in nodes
    }

    def sharp(order):
        ends = [0, *order, 0] if loop else [0, *order]
        turns = list(zip(ends, ends[1:], ends[2:], strict=False))
        if loop and len(order) > 1:
            turns.append((order[-1], 0, order[0]))
        count = 0
        for a, b, c in turns:
            u = (x[a] - x[b], y[a] - y[b])
            v = (x[c] - x[b], y[c] - y[b])
            norms = math.hypot(*u) * math.hypot(*v)
            if norms and (u[0] * v[0] + u[1] * v[1]) / norms > math.cos(
                math.radians(SHARP_TURN_DEGREES)
            ):
                count += 1
        return count

    def score(walk):
        order = _walking_order(walk, d, loop)
        walked = _path_meters(order, d, loop)
        return (
            -len(walk),
            missing(walk),
            sharp(order),
            max(0.0, ROUTE_FILL * budget_meters - walked),
            -sum(prize[i] for i in walk),
            walked,
        )

    def shaped(heading):
        """The candidates nearest `size` targets on a walk of about the budget
        heading off from the anchor, shrunk until they fit; [] if none do."""
        aim = (1 + ROUTE_FILL) / 2 * budget_meters
        for scale in (1, 0.8, 0.6, 0.4):
            if loop:
                # size + 1 corners, the anchor one of them, on a circle through it.
                n = size + 1
                radius = scale * aim / (d_per_crow * 2 * n * math.sin(math.pi / n))
                cx, cy = radius * math.cos(heading), radius * math.sin(heading)
                targets = [
                    (
                        cx + radius * math.cos(heading + math.pi + 2 * math.pi * j / n),
                        cy + radius * math.sin(heading + math.pi + 2 * math.pi * j / n),
                    )
                    for j in range(1, size + 1)
                ]
            else:
                step = scale * aim / (d_per_crow * size)
                targets = [
                    (j * step * math.cos(heading), j * step * math.sin(heading))
                    for j in range(1, size + 1)
                ]
            walk: list[int] = []
            for tx, ty in targets:
                free = [i for i in nodes if i not in walk]
                free = [i for i in free if fits(walk, i)] or free
                walk.append(min(free, key=lambda i: (x[i] - tx) ** 2 + (y[i] - ty) ** 2))
            if _path_meters(_walking_order(walk, d, loop), d, loop) <= budget_meters:
                return walk
        return []

    rng = random.Random(seed)
    # How much longer a walk is than the straight line, from this very matrix:
    # 1.3 without streets, whatever the streets say with them.
    crow = [meters_between(at, Coordinates(lat=c.lat, lng=c.lng)) for c in candidates]
    d_per_crow = sum(d[0][i] for i in nodes) / max(sum(crow), 1) if size else 1
    offset = rng.uniform(0, 2 * math.pi)
    # Nearest-neighbour as a start too: prize per metre can spend the budget on
    # a few far stops where the plain nearest ones would have fit more.
    near: list[int] = []
    while len(near) < size:
        c = min((c for c in nodes if c not in near), key=lambda c: d[near[-1] if near else 0][c])
        if _path_meters([*near, c], d, loop) > budget_meters:
            break
        near.append(c)
    walks = [fill([]), fill(_walking_order(near, d, loop))]
    # And from every candidate as the first stop. Two clusters either side of
    # the anchor: every greedy start opens with the nearer one, and a shake
    # drops one or two stops, never the whole cluster it would take to cross.
    walks += [fill([c]) for c in nodes if _path_meters([c], d, loop) <= budget_meters]
    if size:
        for k in range(ROUTE_HEADINGS):
            walk = shaped(offset + 2 * math.pi * k / ROUTE_HEADINGS)
            if walk:
                walks.append(fill(_walking_order(walk, d, loop)))
    best = min(walks, key=score)
    for _ in range(ROUTE_SHAKES if best else 0):
        # Refilled with the dropped stops allowed back, a greedy fill puts the
        # same cheap stop straight back and never reaches a better one further out.
        drop = set(rng.sample(best, rng.randint(1, min(2, len(best)))))
        trial = fill([i for i in best if i not in drop], drop)
        if score(trial) < score(best):
            best = trial
    # The best walk, then the first walks: one per heading, so the list holds
    # different loops rather than one loop with a stop swapped.
    ranked = {frozenset(w): score(w) for w in [best, *walks]}
    top = score(best)
    alike = sorted((v, sorted(w)) for w, v in ranked.items() if v[:2] == top[:2])
    return [_walking_order(w, d, loop) for _, w in alike[:ROUTE_SHORTLIST]]


# 8! is 40,320 orderings - still cheaper than the SQL round trip before it.
EXACT_ORDER_MAX = 8


def _path_meters(walk, d: list, loop: bool = False) -> float:
    """Metres from the anchor (node 0) through `walk`, and back when `loop`."""
    ends = [0, *walk, 0] if loop and walk else [0, *walk]
    return sum(d[a][b] for a, b in itertools.pairwise(ends))


def _walking_order(picks: list[int], d: list, loop: bool = False) -> list[int]:
    """The shortest walk from the anchor through every pick, and back to it
    when `loop`, by trying
    every ordering. Five stops is 120 of them, and nearest-neighbour - what this
    was - doubles back whenever the closest stop is behind you.
    ponytail: exact up to EXACT_ORDER_MAX, greedy above it; Held-Karp if
    ROUTE_SIZE ever grows that far (TODO.md, "Order the stops exactly")."""
    if len(picks) <= EXACT_ORDER_MAX:
        # A crow-flies loop and its reverse are the same length, so which one
        # min() keeps depends on input order - here, the solver's seeded
        # search. Sorted, it is the same way round for every device.
        return list(
            min(itertools.permutations(sorted(picks)), key=lambda p: _path_meters(p, d, loop))
        )
    remaining = list(picks)
    ordered = []
    here = 0
    while remaining:
        here = min(remaining, key=lambda c: d[here][c])
        ordered.append(here)
        remaining.remove(here)
    return ordered


ROUTE_LOOKUP = """
    SELECT memory_ids, budget_meters, legs FROM daily_routes
    WHERE device_id = CAST(:device AS uuid) AND route_date = :route_date
"""

ROUTE_INSERT = """
    INSERT INTO daily_routes (device_id, route_date, memory_ids, budget_meters, legs)
    VALUES (
        CAST(:device AS uuid), :route_date, CAST(:ids AS integer[]), :budget_meters,
        CAST(:legs AS jsonb)
    )
    ON CONFLICT (device_id, route_date) DO NOTHING
"""


# Rows read to spread from, and candidates kept: one street table costs ~19ms
# a point on the MLD sidecar, so the second number is the latency knob.
ROUTE_POOL = 400
ROUTE_CANDIDATES = 8 * ROUTE_SIZE


def _spread(candidates: list, budget_meters: float) -> list:
    """ROUTE_CANDIDATES of them: the first (nearest) per grid cell of
    budget/15, then the rest nearest first. On a full map the forty nearest all
    sit within a few hundred metres, and no long walk can be built from them;
    on a sparse one this keeps everything.
    ponytail: nearest per cell, not most prize per cell."""
    side = budget_meters / 15
    seen: set = set()
    first, rest = [], []
    for r in candidates:
        cell = (
            round(r.lat * 111_320 / side),
            round(r.lng * 111_320 * math.cos(math.radians(r.lat)) / side),
        )
        (rest if cell in seen else first).append(r)
        seen.add(cell)
    return (first + rest)[:ROUTE_CANDIDATES]


# Rounds of "drop one stop and see whether the loop gets cleaner". Each round
# routes one walk per stop, milliseconds apiece against a local sidecar.
ROUTE_CLEANUPS = 3
# Street walked twice is compared in steps of this, so a few metres from a
# mid-block start to its corner never outrank the solver's own ranking.
SPUR_STEP_METERS = 25


def _plan_route(session, device: str, at: Coordinates, budget_meters: int, route_date):
    """The walk this device would get from `at` today: (stops in order,
    stop-to-stop street legs, {out, home} street legs touching `at`). Seeded
    on device and day, so the preview and the accept that follows it pick the
    same stops without the client ever naming them.

    A loop cannot reach further out than half its length, so that is where
    candidates come from. With streets, two more rules:

    - A stop further from any walkable way than the gate can never be stood
      on, so it is not a stop.
    - The walk should be a clean loop, not a line with spurs: a stop off the
      loop is walked to and back the same way. Each walk on the solver's
      shortlist is routed, and the one retracing the fewest SPUR_STEP_METERS
      of street wins, the solver's order breaking ties. Then each stop is
      dropped in turn and the rest re-picked; a walk with as many stops that
      retraces less wins. Up to ROUTE_CLEANUPS rounds."""
    candidates = session.execute(
        text(ROUTE_CANDIDATES_QUERY),
        {
            "lat": at.lat,
            "lng": at.lng,
            "radius_meters": budget_meters / 2,
            "today": route_date,
            "device_id": device,
            "limit": ROUTE_POOL,
        },
    ).fetchall()
    candidates = _spread(_one_per_place(candidates), budget_meters)
    d, snaps = street_table([at] + [Coordinates(lat=r.lat, lng=r.lng) for r in candidates])
    if snaps:
        keep = [i for i, r in enumerate(candidates) if snaps[i + 1] <= UNLOCK_RADIUS_METERS]
        candidates = [candidates[i] for i in keep]
        rows = [0] + [i + 1 for i in keep]
        d = [[d[a][b] for b in rows] for a in rows]
    seed = f"{device}:{route_date}"

    def walks(banned: set[int]) -> list[list[int]]:
        """The solver's shortlist as nodes into `d`, each in walking order,
        never any stop in `banned`."""
        nodes = [i for i in range(1, len(candidates) + 1) if i not in banned]
        rows = [0, *nodes]
        dd = [[d[a][b] for b in rows] for a in rows]
        shortlist = _choose_walks(
            [candidates[i - 1] for i in nodes], ROUTE_SIZE, dd, seed, budget_meters, ROUTE_LOOP, at
        )
        return [[nodes[i - 1] for i in _walking_order(p, dd, ROUTE_LOOP)] for p in shortlist]

    def walk(banned: set[int]) -> list[int]:
        return walks(banned)[0]

    def streets(order: list[int]):
        stops = [Coordinates(lat=candidates[i - 1].lat, lng=candidates[i - 1].lng) for i in order]
        return street_legs([at, *stops, *([at] if ROUTE_LOOP else [])])

    shortlist = walks(set())
    order = shortlist[0]
    legs = streets(order) if order else None
    if legs is None:
        return [candidates[i - 1] for i in order], None, None

    def spur(order, legs):
        pins = [Coordinates(lat=candidates[i - 1].lat, lng=candidates[i - 1].lng) for i in order]
        return retraced_meters([p for leg in legs for p in leg], pins)

    def judge(order, legs):
        """Short of ROUTE_FILL of the slider first, then street retraced. A
        short walk retraces least, so on spurs alone a 10km ask got 755m."""
        short = max(0.0, ROUTE_FILL * budget_meters - _path_meters(order, d, ROUTE_LOOP))
        return short // SPUR_STEP_METERS, spur(order, legs)

    routed = [(order, legs)] + [(o, streets(o)) for o in shortlist[1:]]
    judged = [(judge(o, lg), n, o, lg) for n, (o, lg) in enumerate(routed) if lg]
    _, _, order, legs = min(judged, key=lambda j: (j[0][0], j[0][1] // SPUR_STEP_METERS, j[1]))
    retraced = spur(order, legs)
    judged_now = judge(order, legs)
    banned: set[int] = set()
    for _ in range(ROUTE_CLEANUPS):
        if retraced < 1:
            break
        trials = []
        for stop in order:
            trial = walk(banned | {stop})
            if len(trial) < len(order):
                continue
            trial_legs = streets(trial)
            if trial_legs is not None:
                trials.append((judge(trial, trial_legs), stop, trial, trial_legs))
        if not trials:
            break
        verdict, stop, trial, trial_legs = min(trials, key=lambda t: t[0])
        if verdict >= judged_now:
            break
        judged_now, order, legs = verdict, trial, trial_legs
        retraced = spur(order, legs)
        banned.add(stop)

    # One street route through the whole walk, start and home included, split
    # into the stop-to-stop legs (stored) and the two that touch the start
    # (handed to the preview, which stores nothing).
    ends = {"out": legs[0], "home": legs[-1] if ROUTE_LOOP else None}
    return [candidates[i - 1] for i in order], legs[1 : len(order)], ends


def _route_response(
    route_date, rows, memory_ids, budget_meters, legs, ends=None, earned=frozenset()
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
            loop=ROUTE_LOOP,
            # A stop hidden since would shift every leg after it onto the wrong
            # pair; straight lines are the honest fallback.
            legs=legs if len(memories) == len(memory_ids) else None,
            out_leg=ends and ends["out"],
            home_leg=ends and ends["home"],
        ),
    )


def _legs_json(legs):
    return [[c.model_dump() for c in leg] for leg in legs] if legs else None


@router.get("/v1/routes/preview", response_model=RouteResponse)
def preview_route(
    device: str = Query(..., pattern=DEVICE_PATTERN),
    lat: float = Query(..., ge=-90, le=90),
    lng: float = Query(..., ge=-180, le=180),
    budget_meters: int = Query(..., ge=ROUTE_BUDGET_MIN_METERS, le=ROUTE_BUDGET_MAX_METERS),
):
    """The walk POST /v1/routes/today would store, stored nowhere. A device that
    already accepted today's walk still gets a preview; accepting returns the
    walk it already has."""
    route_date = gate.today()
    with get_session() as session:
        picked, legs, ends = _plan_route(
            session, device, Coordinates(lat=lat, lng=lng), budget_meters, route_date
        )
    return _route_response(
        route_date, picked, [r.id for r in picked], budget_meters, _legs_json(legs), ends
    )


@router.post("/v1/routes/today", response_model=RouteResponse)
def accept_route(body: RouteRequest):
    """Accept today's walk. One per device per day: the first accept is stored
    and every later one gets it back, whatever it asked for.

    An empty walk is not stored: stored, it would pin the whole day to
    "nothing here" even after the device reaches somewhere stocked."""
    route_date = gate.today()
    with get_session() as session:
        row = session.execute(
            text(ROUTE_LOOKUP), {"device": body.device, "route_date": route_date}
        ).fetchone()
        if row is None:
            picked, legs, _ = _plan_route(
                session,
                body.device,
                Coordinates(lat=body.lat, lng=body.lng),
                body.budget_meters,
                route_date,
            )
            if not picked:
                return _route_response(route_date, [], [], body.budget_meters, None)
            touch_device(session, body.device)
            session.execute(
                text(ROUTE_INSERT),
                {
                    "device": body.device,
                    "route_date": route_date,
                    "ids": [r.id for r in picked],
                    "budget_meters": body.budget_meters,
                    "legs": json.dumps(_legs_json(legs)) if legs else None,
                },
            )
            # Somebody else's accept this second may have won the race - read
            # back whichever array actually landed.
            row = session.execute(
                text(ROUTE_LOOKUP), {"device": body.device, "route_date": route_date}
            ).fetchone()
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
    return _route_response(route_date, rows, memory_ids, row.budget_meters, row.legs)


@router.get("/v1/routes/walked", response_model=WalkedResponse)
def get_walked_routes(
    device: str = Query(..., pattern=DEVICE_PATTERN),
    limit: int = Query(100, ge=1, le=500),
):
    """Every walk this account accepted, newest first, finished or not. Earned
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
        route = _route_response(w.route_date, rows, ids, w.budget_meters, w.legs, earned=earned)
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
