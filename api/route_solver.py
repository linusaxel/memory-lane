"""The daily walk: which stops, in what order. api/read.py serves it.

How a walk is ranked, in two stages, the second only with streets:

1. From the matrix (`_choose_walks`, its `score`): the most stops that fit,
   then the layer mix, then the fewest sharp turns back on itself, then the
   shortfall under ROUTE_FILL of the slider, then the fewest bunched stops
   (`_bunched`), then the most prize, then the shortest walk. Every walk tied with the best one on count and mix makes a
   shortlist of up to ROUTE_SHORTLIST. Without streets, the best one is the walk.
2. From the streets (`_plan_route`, its `judge`): each shortlisted walk is
   routed and scored on metres off the slider plus metres retraced plus
   CROSSING_METERS a place it crosses itself, in steps of SPUR_STEP_METERS,
   then on retraced metres alone. Every walk within ROUTE_VARIETY of the
   slider of the best one, retracing and crossing no more, is as good;
   the day plus `again` picks among them. Then up to ROUTE_CLEANUPS rounds drop
   one stop and re-pick, keeping a walk with as many stops that judges better.
"""

import functools
import itertools
import math
import os
import random

from fastapi import HTTPException
from sqlalchemy import text

from api.gate import UNLOCK_RADIUS_METERS, meters_between
from api.models import Coordinates
from api.queries import ROUTE_CANDIDATES_QUERY
from api.streets import crossings, retraced_meters, street_legs, street_table

ROUTE_SIZE = int(os.getenv("ROUTE_SIZE", "5"))


def _route_size(budget_meters: float) -> int:
    """At least ROUTE_SIZE stops, then about one a km: five stops on the
    shortest street legs between them cannot fill a long slider."""
    return max(ROUTE_SIZE, round(budget_meters / 1000))


# A loop ends back where the day's walk started, so its last leg is the walk
# home, and it is counted when choosing and ordering stops. ROUTE_LOOP=0 makes
# it one-way, and a request's `loop` overrides it. The server never stores that
# start; the app remembers it.
ROUTE_LOOP = os.getenv("ROUTE_LOOP", "1") != "0"


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
# Up to this many candidates, every set of stops is tried: 120 of them at 7.
# ponytail: a sparse map is exact, a full one heuristic; nothing tells how far
# off the heuristic is on 40 candidates but the solver's own property tests.
EXACT_CHOICE_MAX = 7
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
    include: int | None = None,
    end: Coordinates | None = None,
) -> list[list[int]]:
    """Up to ROUTE_SHORTLIST walks of up to `size` stops from the anchor `at`
    within `budget_meters`, best first, ranked by stage 1 of the module
    docstring. ROUTE_FILL is why a long slider gets a long walk, not the five
    nearest stops in a knot. A stop's prize is 1 + contrast_score, so an
    unscored one is worth 1.

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
    `include`, a memory id, is on every walk returned ("Walk here"). Every
    walk starts from it; _plan_route has already vetted that it fits alone.
    `end` is where a one-way walk finishes. `d` already walks to it where a
    loop walks home (column 0, `_plan_route`), so `loop` is true; only the
    map's turns need to know where it is.

    ponytail: layer is the only diversity term; MMR on tag overlap once prizes
    actually differ."""
    nodes = range(1, len(candidates) + 1)
    size = min(size, len(candidates))
    must = {i for i in nodes if include is not None and candidates[i - 1].id == include}
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
        for c in must - set(walk):
            if len(walk) < size:
                walk.insert(min(range(len(walk) + 1), key=lambda at: cost(walk, c, at)), c)
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
            # Whether a stop fits is its layer's, so ask once a layer.
            one_of = {stranger[o[1]]: o[1] for o in options}
            ok = {k for k, c in one_of.items() if fits(walk, c)}
            options = [o for o in options if stranger[o[1]] in ok] or options
            _, c, at = min(
                options,
                key=lambda o: (-prize[o[1]] / max(o[0], 1), o),
            )
            walk.insert(at, c)
        return walk

    points = {0: at, -1: end or at} | {i: candidates[i - 1] for i in nodes}
    y = {i: (p.lat - at.lat) * 111_320 for i, p in points.items()}
    x = {i: (p.lng - at.lng) * 111_320 * math.cos(math.radians(at.lat)) for i, p in points.items()}

    def sharp(order):
        ends = [0, *order, -1] if loop else [0, *order]
        turns = list(zip(ends, ends[1:], ends[2:], strict=False))
        if loop and not end and len(order) > 1:
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
        return scored(frozenset(walk))

    # _walking_order sorts first, so a score is the set's, and the search
    # meets the same sets again and again.
    @functools.cache
    def scored(walk):
        order = _walking_order(list(walk), d, loop)
        walked = _path_meters(order, d, loop)
        return (
            -len(walk),
            missing(walk),
            sharp(order),
            _bunched(order, d, loop),
            max(0.0, ROUTE_FILL * budget_meters - walked),
            -sum(prize[i] for i in walk),
            walked,
        )

    def shaped(heading, around=False):
        """The candidates nearest `size` targets on a walk of about the budget
        heading off from the anchor, shrunk until they fit; [] if none do.
        `around` puts a loop's targets on a circle round the anchor instead of
        through it: out, round and back, for stops on every side of the start
        (a lake round a flat), which the circle through it leaves on one side."""
        aim = (1 + ROUTE_FILL) / 2 * budget_meters
        for scale in (1, 0.8, 0.6, 0.4):
            if loop and around:
                # Out, size - 1 chords of 2 pi / size, and back.
                radius = (
                    scale * aim / (d_per_crow * (2 + 2 * (size - 1) * math.sin(math.pi / size)))
                )
                targets = [
                    (
                        radius * math.cos(heading + 2 * math.pi * j / size),
                        radius * math.sin(heading + 2 * math.pi * j / size),
                    )
                    for j in range(size)
                ]
            elif loop:
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
            for c in must:
                # It stands in for the target nearest it.
                del targets[
                    min(
                        range(len(targets)),
                        key=lambda j: (x[c] - targets[j][0]) ** 2 + (y[c] - targets[j][1]) ** 2,
                    )
                ]
                walk.append(c)
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
    if len(candidates) <= EXACT_CHOICE_MAX:
        walks += [
            list(s)
            for k in range(1, size + 1)
            for s in itertools.combinations(nodes, k)
            if must <= set(s)
            and _path_meters(_walking_order(list(s), d, loop), d, loop) <= budget_meters
        ]
    # ponytail: no shaped walks to an end; the fills and shakes find them.
    # A line bowed towards the end, if a long walk to one comes out short.
    if size and not end:
        for k in range(ROUTE_HEADINGS):
            for around in (False, True) if loop else (False,):
                walk = shaped(offset + 2 * math.pi * k / ROUTE_HEADINGS, around)
                if walk:
                    walks.append(fill(_walking_order(walk, d, loop)))
    walks = [w for w in walks if must <= set(w)]
    best = min(walks, key=score)
    for _ in range(ROUTE_SHAKES if len(best) > len(must) else 0):
        # Refilled with the dropped stops allowed back, a greedy fill puts the
        # same cheap stop straight back and never reaches a better one further out.
        # Then again with them allowed, for one that fits on the end after all.
        free = [i for i in best if i not in must]
        drop = set(rng.sample(free, rng.randint(1, min(2, len(free)))))
        trial = fill(fill([i for i in best if i not in drop], drop))
        if score(trial) < score(best):
            best = trial
    # The best walk, then the first walks: one per heading, so the list holds
    # different loops rather than one loop with a stop swapped.
    ranked = {frozenset(w): score(w) for w in [best, *walks]}
    top = score(best)
    alike = sorted((v, sorted(w)) for w, v in ranked.items() if v[:2] == top[:2])
    return [_walking_order(w, d, loop) for _, w in alike[:ROUTE_SHORTLIST]]


# A leg shorter than this share of an even one is two stops bunched together.
BUNCHED_SHARE = 0.5


def _bunched(order: list[int], d: list, loop: bool) -> int:
    """Legs of the walk, out and home included, shorter than BUNCHED_SHARE of
    the walk split evenly between them."""
    ends = [0, *order, 0] if loop and order else [0, *order]
    legs = [d[a][b] for a, b in itertools.pairwise(ends)]
    even = sum(legs) / max(len(legs), 1)
    return sum(leg < BUNCHED_SHARE * even for leg in legs)


# 6! is 720 orderings. `score` orders every walk it looks at, so 8! (40,320)
# on a 10 km walk of ten stops took seconds.
EXACT_ORDER_MAX = 6


def _path_meters(walk, d: list, loop: bool = False) -> float:
    """Metres from the anchor (node 0) through `walk`, and back when `loop`."""
    ends = [0, *walk, 0] if loop and walk else [0, *walk]
    return sum(d[a][b] for a, b in itertools.pairwise(ends))


def _walking_order(picks: list[int], d: list, loop: bool = False) -> list[int]:
    """The shortest walk from the anchor through every pick, and back to it
    when `loop`, by trying
    every ordering. Five stops is 120 of them, and nearest-neighbour alone
    doubles back whenever the closest stop is behind you.
    ponytail: exact up to EXACT_ORDER_MAX, nearest-neighbour then 2-opt above
    it; Held-Karp if a long walk's order is ever measurably off."""
    if len(picks) <= EXACT_ORDER_MAX:
        # A crow-flies loop and its reverse are the same length, so which one
        # min() keeps depends on input order - here, the solver's seeded
        # search. Sorted, it is the same way round for every device.
        return list(
            min(itertools.permutations(sorted(picks)), key=lambda p: _path_meters(p, d, loop))
        )
    remaining = sorted(picks)
    ordered = []
    here = 0
    while remaining:
        here = min(remaining, key=lambda c: d[here][c])
        ordered.append(here)
        remaining.remove(here)
    walked = _path_meters(ordered, d, loop)
    better = True
    while better:
        better = False
        for i, j in itertools.combinations(range(len(ordered)), 2):
            trial = ordered[:i] + ordered[i : j + 1][::-1] + ordered[j + 1 :]
            if (meters := _path_meters(trial, d, loop)) < walked - 1e-9:
                ordered, walked, better = trial, meters, True
    return ordered


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
# What a walk crossing its own path costs in the judge, as if it were this
# many metres retraced: a figure of eight reads as lost on the map.
CROSSING_METERS = 300
# A walk judged within this share of the slider of the best one, retracing no
# more, is as good a walk. Day and `again` take turns through them.
ROUTE_VARIETY = 0.1


def _plan_route(
    session,
    device: str,
    at: Coordinates,
    budget_meters: int,
    route_date,
    loop: bool = ROUTE_LOOP,
    again: int = 0,
    include: int | None = None,
    end: Coordinates | None = None,
):
    """The walk this device would get from `at` today: (stops in order,
    stop-to-stop street legs, {out, home} street legs touching `at`). Seeded
    on device and day, so the preview and the accept that follows it pick the
    same stops without the client ever naming them.

    A loop cannot reach further out than half its length, so that is where
    candidates come from. With streets, two more rules:

    - A stop further from any walkable way than the gate can never be stood
      on, so it is not a stop.
    - The walk should be a clean loop, not a line with spurs: a stop off the
      loop is walked to and back the same way. That is stage 2 of the module
      docstring. The app rolls `again` afresh for every plan and steps it for
      "Show me another", so a plan differs whenever there is another as good.

    `include` is a memory the walk must pass ("Walk here"). The candidates
    query puts it first if it may be a stop at all; 422 if it may not, or no
    walk of this length reaches it.

    `end` is where a one-way walk finishes, sent with each request and stored
    nowhere. A stop on a walk that long is within half of it of the midway
    point, so candidates come from there. 422 too_far if the end is out of reach."""
    if end:
        loop = False
    centre = Coordinates(lat=(at.lat + end.lat) / 2, lng=(at.lng + end.lng) / 2) if end else at
    candidates = session.execute(
        text(ROUTE_CANDIDATES_QUERY),
        {
            "lat": centre.lat,
            "lng": centre.lng,
            "radius_meters": budget_meters / 2,
            "device_id": device,
            "limit": ROUTE_POOL,
            "include": include,
        },
    ).fetchall()
    candidates = _spread(_one_per_place(candidates), budget_meters)
    stops_at = [Coordinates(lat=r.lat, lng=r.lng) for r in candidates]
    d, snaps = street_table([at, *stops_at, *([end] if end else [])])
    keep = range(len(candidates))
    if snaps:
        keep = [i for i in keep if snaps[i + 1] <= UNLOCK_RADIUS_METERS]
        candidates = [candidates[i] for i in keep]
    if end:
        # The walk to the end stands in for the walk home: column 0 is metres
        # to it, so everything below that closes a loop walks to the end instead.
        if (reach := d[0][-1]) > budget_meters:
            raise HTTPException(
                status_code=422,
                detail={"reason": "too_far", "min_budget_meters": math.ceil(reach)},
            )
        rows = [0] + [i + 1 for i in keep]
        d = [[d[a][-1], *(d[a][b] for b in rows[1:])] for a in rows]
    elif snaps:
        rows = [0] + [i + 1 for i in keep]
        d = [[d[a][b] for b in rows] for a in rows]
    closed = loop or end is not None
    if include is not None:
        # Beyond half the length is not_a_stop too: the app floors the slider
        # at twice the crow's distance, so that is a position that moved.
        if not candidates or candidates[0].id != include:
            raise HTTPException(status_code=422, detail={"reason": "not_a_stop"})
        if (reach := _path_meters([1], d, closed)) > budget_meters:
            raise HTTPException(
                status_code=422,
                detail={"reason": "too_far", "min_budget_meters": math.ceil(reach)},
            )
    seed = f"{device}:{route_date}"

    solve_for = budget_meters

    def walks(banned: set[int]) -> list[list[int]]:
        """The solver's shortlist as nodes into `d`, each in walking order,
        never any stop in `banned`."""
        nodes = [i for i in range(1, len(candidates) + 1) if i not in banned]
        rows = [0, *nodes]
        dd = [[d[a][b] for b in rows] for a in rows]
        shortlist = _choose_walks(
            [candidates[i - 1] for i in nodes],
            _route_size(budget_meters),
            dd,
            seed,
            solve_for,
            closed,
            at,
            include,
            end,
        )
        return [[nodes[i - 1] for i in _walking_order(p, dd, closed)] for p in shortlist]

    def walk(banned: set[int]) -> list[int]:
        return walks(banned)[0]

    def streets(order: list[int]):
        stops = [Coordinates(lat=candidates[i - 1].lat, lng=candidates[i - 1].lng) for i in order]
        if end:
            return street_legs([at, *stops, end])
        if not loop:
            return street_legs([at, *stops])
        # Once more past home to the first stop, and that leg is the way out:
        # with the start a waypoint mid-route, out and home cannot share the
        # stretch to its corner. An end of a route may turn round; a middle not.
        legs = street_legs([at, *stops, at, stops[0]])
        return legs and [legs[-1], *legs[1:-1]]

    shortlist = walks(set())
    order = shortlist[0]
    legs = streets(order) if order else None
    if legs is None:
        return [candidates[i - 1] for i in order], None, None

    def routed_meters(legs):
        return sum(meters_between(a, b) for leg in legs for a, b in itertools.pairwise(leg))

    def spur(order, legs):
        pins = [Coordinates(lat=candidates[i - 1].lat, lng=candidates[i - 1].lng) for i in order]
        return retraced_meters([p for leg in legs for p in leg], pins)

    def crossed(order, legs):
        pins = [at] + [
            Coordinates(lat=candidates[i - 1].lat, lng=candidates[i - 1].lng) for i in order
        ]
        return crossings([p for leg in legs for p in leg], pins)

    def judge(order, legs):
        """Stage 2's ranking, in the module docstring. A short walk retraces
        least, so on spurs alone a 10km ask got 755m. Short of ROUTE_FILL is
        read from `d`, where a stub walked in and out cannot
        pay for itself; over the slider from the routed legs, because no U-turn
        at a stop means round the block, which the table does not know about."""
        short = ROUTE_FILL * budget_meters - _path_meters(order, d, closed)
        off = max(0.0, short, routed_meters(legs) - budget_meters)
        retraced = spur(order, legs)
        tangled = CROSSING_METERS * crossed(order, legs)
        return (off + retraced + tangled) // SPUR_STEP_METERS, retraced

    routed = [(order, legs)] + [(o, streets(o)) for o in shortlist[1:]]
    # Round the block is longer than `d` says. When that takes the walk over
    # the slider, solve again for as much less as it went over, and judge both.
    over = routed_meters(legs) / max(_path_meters(order, d, closed), 1)
    if routed_meters(legs) > budget_meters and over > 1:
        solve_for = budget_meters / over
        routed += [(o, streets(o)) for o in walks(set()) if o]
    judged = [(judge(o, lg), crossed(o, lg), n, o, lg) for n, (o, lg) in enumerate(routed) if lg]
    (top, top_retraced), top_crossed, *_ = min(judged, key=lambda j: j[:3])
    slack = ROUTE_VARIETY * budget_meters / SPUR_STEP_METERS
    alike = sorted(
        (
            j
            for j in judged
            if j[0][0] <= top + slack
            and j[0][1] <= top_retraced + SPUR_STEP_METERS
            and j[1] <= top_crossed
        ),
        key=lambda j: j[:3],
    )
    *_, order, legs = alike[(random.Random(seed).randrange(len(alike)) + again) % len(alike)]
    retraced = spur(order, legs)
    judged_now = judge(order, legs)
    banned: set[int] = set()
    for _ in range(ROUTE_CLEANUPS):
        if retraced < 1 and not crossed(order, legs):
            break
        trials = []
        for stop in order:
            if candidates[stop - 1].id == include:
                continue
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
    ends = {"out": legs[0], "home": legs[-1] if closed else None}
    return [candidates[i - 1] for i in order], legs[1 : len(order)], ends
