"""Today's walk: GET /v1/routes/preview proposes it, POST /v1/routes/today
accepts it for the day, GET /v1/routes/today reads it back.

Mirrors tests/test_api_unlock.py's fixture style - a real ephemeral database,
a TestClient, and assertions on the JSON rather than on internals, because the
thing that matters is what a device actually receives.
"""

import datetime
import math
from itertools import pairwise

import pytest
from sqlalchemy import text

from api import read, route_solver, streets
from api.models import Coordinates

pytestmark = pytest.mark.db

LAT, LNG = 55.6759, 12.5655
DEVICE = "11111111-1111-1111-1111-111111111111"


@pytest.fixture
def client(api_client):
    return api_client


@pytest.fixture
def on_streets(monkeypatch):
    """Streets where the table and the legs agree: straight lines, measured
    straight. Pass other legs to add a detour; the table does not see it, as
    OSRM's does not see the stub to a pin it snapped to the street."""

    def table(points):
        return [[read.meters_between(a, b) for b in points] for a in points], [0.0] * len(points)

    def use(legs=lambda stops: [[a, b] for a, b in pairwise(stops)]):
        monkeypatch.setattr(route_solver, "street_table", table)
        monkeypatch.setattr(route_solver, "street_legs", legs)

    return use


def _place(session, name, lat, lng, precision=50):
    return session.execute(
        text(
            "INSERT INTO places (name, place_query, coordinates, precision_meters) "
            "VALUES (:n, :q, ST_MakePoint(:lng, :lat)::geography, :prec) RETURNING id"
        ),
        {"n": name, "q": f"{name} query", "lat": lat, "lng": lng, "prec": precision},
    ).scalar()


def _historical(session, place_id, summary, url, tags=None):
    """Walk-to-unlock: a coordinate no other place shares, like the real
    corpus's non-centroid rows."""
    content = session.execute(
        text(
            "INSERT INTO content (url, platform, platform_id, source_type) "
            "VALUES (:u, 'text', :p, 'archive') RETURNING id"
        ),
        {"u": url, "p": url[-11:]},
    ).scalar()
    return session.execute(
        text(
            "INSERT INTO memories (place_id, content_id, timestamp_start, summary, "
            "extraction_confidence, tags, layer) VALUES (:p, :c, 0, :s, 'high', "
            "CAST(:t AS varchar[]), 'historical') RETURNING id"
        ),
        {"p": place_id, "c": content, "s": summary, "t": tags or ["music"]},
    ).scalar()


def _stranger(session, place_id, summary, opens_at=None):
    """Always gated - user_id is the other half of is_gated."""
    user_id = session.execute(
        text("INSERT INTO users (id) VALUES (gen_random_uuid()) RETURNING id")
    ).scalar()
    return session.execute(
        text(
            "INSERT INTO memories (place_id, content_id, timestamp_start, summary, "
            "extraction_confidence, tags, layer, user_id, opens_at) VALUES "
            "(:p, NULL, NULL, :s, 'high', ARRAY['personal']::varchar[], 'stranger', "
            ":u, :o) RETURNING id"
        ),
        {"p": place_id, "s": summary, "u": user_id, "o": opens_at},
    ).scalar()


def _offset(session, n, layer="historical", **kw):
    """A gated memory ~n*100m north of LAT,LNG - far enough apart that no two
    share a grid cell, close enough to fit a 4km walk."""
    place = _place(session, f"Stop {n}", LAT + n * 0.001, LNG)
    if layer == "stranger":
        return _stranger(session, place, f"stranger memory {n}", **kw)
    return _historical(session, place, f"historical memory {n}", f"https://e.invalid/{n:0>11}")


def _route(client, lat=LAT, lng=LNG, budget_meters=4000):
    """Accept today's walk."""
    return client.post(
        "/v1/routes/today",
        json={"device": DEVICE, "lat": lat, "lng": lng, "budget_meters": budget_meters},
    )


def _preview(client, lat=LAT, lng=LNG, budget_meters=4000):
    return client.get(
        f"/v1/routes/preview?device={DEVICE}&lat={lat}&lng={lng}&budget_meters={budget_meters}"
    )


def _stored(db_session):
    return db_session.execute(text("SELECT COUNT(*) FROM daily_routes")).scalar()


def test_a_preview_stores_nothing_and_accepting_it_stores_the_same_walk(client, db_session):
    for n in range(1, 7):
        _offset(db_session, n)
    db_session.commit()

    preview = _preview(client).json()
    assert preview["meta"]["size"] == 5
    assert _stored(db_session) == 0
    assert client.get(f"/v1/routes/today?device={DEVICE}").status_code == 404

    accepted = _route(client).json()
    assert [m["id"] for m in accepted["memories"]] == [m["id"] for m in preview["memories"]]
    assert accepted["meta"]["budget_meters"] == 4000
    assert _stored(db_session) == 1

    read_back = client.get(f"/v1/routes/today?device={DEVICE}").json()
    assert read_back == accepted


def test_the_accepted_walk_is_locked_for_the_day(client, db_session):
    for n in range(1, 7):
        _offset(db_session, n)
    db_session.commit()

    first = _route(client).json()
    # Another length from another position the same day gets the first walk.
    second = _route(client, lat=LAT + 0.02, lng=LNG + 0.02, budget_meters=1000).json()
    assert second == first


def test_a_shorter_walk_has_fewer_stops(client, db_session):
    for n in range(1, 7):
        _offset(db_session, n)
    db_session.commit()

    # ~111m apart in a line north: 1km as a loop, crow-flies x 1.3, reaches 3.
    assert _preview(client, budget_meters=1000).json()["meta"]["size"] == 3


@pytest.mark.parametrize("budget", [999, 10_001])
def test_a_walk_length_outside_1_to_10km_is_refused(client, db_session, budget):
    assert _preview(client, budget_meters=budget).status_code == 422
    assert _route(client, budget_meters=budget).status_code == 422


def test_a_route_excludes_already_unlocked_memories(client, db_session):
    keep = _offset(db_session, 1)
    earned = _offset(db_session, 2)
    db_session.execute(
        text("INSERT INTO devices (id) VALUES (CAST(:d AS uuid)) ON CONFLICT (id) DO NOTHING"),
        {"d": DEVICE},
    )
    db_session.execute(
        text("INSERT INTO unlocks (device_id, memory_id) VALUES (CAST(:d AS uuid), :m)"),
        {"d": DEVICE, "m": earned},
    )
    db_session.commit()

    route = _route(client).json()
    ids = [m["id"] for m in route["memories"]]
    assert earned not in ids, "already earning it once should not spend a route slot on it again"
    assert keep in ids


def test_a_route_mixes_layers_when_both_are_available(client, db_session):
    for n in range(1, 4):
        _offset(db_session, n, layer="historical")
    for n in range(4, 6):
        _offset(db_session, n, layer="stranger")
    db_session.commit()

    route = _route(client).json()
    layers = {m["layer"] for m in route["memories"]}
    assert layers == {"historical", "stranger"}, "a route of one kind defeats the point of mixing"


def test_a_sparse_area_returns_fewer_than_five_without_erroring(client, db_session):
    _offset(db_session, 1)
    _offset(db_session, 2)
    db_session.commit()

    route = _route(client).json()
    assert route["meta"]["size"] == 2
    assert len(route["memories"]) == 2


def test_an_empty_route_is_not_stored_for_the_day(client, db_session):
    """Accepting somewhere empty must not cost the rest of the day's walk."""
    _offset(db_session, 1)
    db_session.commit()

    empty = _route(client, lat=LAT + 1).json()
    assert empty["meta"]["size"] == 0
    assert empty["memories"] == []

    stocked = _route(client).json()
    assert stocked["meta"]["size"] == 1


def test_an_ambiguous_centroid_is_never_a_route_stop(client, db_session):
    """Two places on one point is the model saying 'somewhere in this city' -
    a route sending someone there would open on arrival, which is not a stop,
    it is scenery."""
    shared_place = _place(db_session, "Somewhere", LAT + 0.001, LNG)
    _place(db_session, "Somewhere else", LAT + 0.001, LNG)
    ambiguous = _historical(db_session, shared_place, "a guess", "https://e.invalid/ambiguous1")
    real = _offset(db_session, 2)
    db_session.commit()

    route = _route(client).json()
    ids = [m["id"] for m in route["memories"]]
    assert ambiguous not in ids
    assert real in ids


def test_a_sealed_memory_is_never_a_route_stop(client, db_session):
    """A time capsule cannot be unlocked by walking there, whatever the
    distance - a route slot spent on one would ask for a walk that can't pay
    off."""
    future = datetime.date.today() + datetime.timedelta(days=365)
    sealed = _offset(db_session, 1, layer="stranger", opens_at=future)
    open_one = _offset(db_session, 2)
    db_session.commit()

    route = _route(client).json()
    ids = [m["id"] for m in route["memories"]]
    assert sealed not in ids
    assert open_one in ids


def test_a_stack_never_contributes_two_route_stops(client, db_session):
    """The map groups pins by coordinate, not by memory - `stack` in
    pipeline/seed_dev.py is three memories on one place. Two of them picked as
    separate stops would be one pin asked to show two different numbers."""
    stacked_place = _place(db_session, "The corner", LAT + 0.001, LNG)
    stacked_ids = {
        _historical(
            db_session, stacked_place, f"stack memory {n}", f"https://e.invalid/stack{n:04}"
        )
        for n in range(3)
    }
    for n in range(2, 6):
        _offset(db_session, n)
    db_session.commit()

    route = _route(client).json()
    ids = [m["id"] for m in route["memories"]]
    assert len(stacked_ids & set(ids)) <= 1, "at most one memory from the same place per route"


def test_route_stops_render_locked(client, db_session):
    """Freshly discovered, unwalked stops - rendering them locked is the whole
    point of a route."""
    _offset(db_session, 1)
    db_session.commit()

    route = _route(client).json()
    assert route["memories"][0]["locked"] is True
    assert route["memories"][0]["summary"] == ""


def test_street_legs_are_stored_stop_to_stop(client, db_session, monkeypatch, on_streets):
    for n in range(1, 4):
        _offset(db_session, n)
    db_session.commit()
    monkeypatch.setattr(streets, "ROUTING_URL", None)
    assert _route(client).json()["meta"]["legs"] is None

    db_session.execute(text("DELETE FROM daily_routes"))
    db_session.commit()
    on_streets()
    first = _route(client).json()
    stops = [m["place"]["coordinates"] for m in first["memories"]]
    assert first["meta"]["legs"] == [[a, b] for a, b in pairwise(stops)]

    # The preview also draws the legs touching the start; accepting stores
    # none of them.
    preview = _preview(client).json()["meta"]
    start = {"lat": LAT, "lng": LNG}
    assert preview["out_leg"] == [start, stops[0]]
    assert preview["home_leg"] == [stops[-1], start]
    assert first["meta"]["out_leg"] is None

    # Read back from the row, not recomputed: the start is in none of them.
    monkeypatch.setattr(route_solver, "street_legs", lambda stops: None)
    legs = client.get(f"/v1/routes/today?device={DEVICE}").json()["meta"]["legs"]
    assert legs == first["meta"]["legs"]


def test_retraced_meters_counts_a_stretch_walked_twice_either_way():
    a, b, c = (Coordinates(lat=LAT + n * 0.001, lng=LNG) for n in range(3))
    assert streets.retraced_meters([a, b, c]) == 0
    # Out to c and back to b: b-c is walked twice.
    assert round(streets.retraced_meters([a, b, c, b])) == 111
    # With a stop at c, the 20m of it inside the gate is never walked twice.
    assert round(streets.retraced_meters([a, b, c, b], [c])) == 91


def test_a_stop_that_forces_an_out_and_back_is_swapped_for_a_clean_loop(
    client, db_session, monkeypatch, on_streets
):
    """Stop 2 hangs off the street: reaching it means walking a stub in and the
    same stub out. With a sixth stop to spare, the walk drops it."""
    ids = {n: _offset(db_session, n) for n in range(1, 7)}
    db_session.commit()
    spur = Coordinates(lat=LAT + 0.002, lng=LNG)
    stub = Coordinates(lat=LAT + 0.002, lng=LNG + 0.0004)

    def legs(points):
        out = []
        for a, b in pairwise(points):
            if a == spur:
                out.append([a, stub, b])
            elif b == spur:
                out.append([a, stub, b])
            else:
                out.append([a, b])
        return out

    on_streets(legs)
    chosen = [m["id"] for m in _preview(client).json()["memories"]]
    assert len(chosen) == 5
    assert ids[2] not in chosen


def test_a_stop_too_far_from_any_street_is_never_a_stop(client, db_session, monkeypatch):
    """The gate is 20m. A pin 40m inside a block can never be stood on from a
    street, so a street-routed walk does not offer it."""
    ids = {n: _offset(db_session, n) for n in range(1, 4)}
    db_session.commit()

    def table(points):
        d = [[read.meters_between(a, b) * streets.ROUTE_CIRCUITY for b in points] for a in points]
        # Node 0 is the anchor; the second-nearest candidate is 40m off the street.
        return d, [0.0] + [40.0 if i == 1 else 5.0 for i in range(len(points) - 1)]

    monkeypatch.setattr(route_solver, "street_table", table)
    chosen = [m["id"] for m in _preview(client).json()["memories"]]
    assert ids[2] not in chosen
    assert {ids[1], ids[3]} <= set(chosen)


def test_a_long_ask_is_not_traded_for_a_short_walk_that_retraces_less(
    client, db_session, monkeypatch, on_streets
):
    """A knot of stops round the corner is a clean loop; a ring of stops a
    kilometre and more out is the walk asked for, but each one is reached by a
    stub walked in and out. Judged on retracing alone, a 10km ask got the knot."""

    for k in range(5):
        _historical(
            db_session,
            _place(db_session, f"Near {k}", LAT + 0.0003 * math.cos(k), LNG + 0.0005 * math.sin(k)),
            f"near {k}",
            f"https://e.invalid/near{k:0>7}",
        )
    far = []
    for k in range(10):
        angle = 2 * math.pi * k / 10
        lat, lng = LAT + 0.012 * math.cos(angle), LNG + 0.02 * math.sin(angle)
        _historical(
            db_session,
            _place(db_session, f"Far {k}", lat, lng),
            f"far {k}",
            f"https://e.invalid/far{k:0>8}",
        )
        far.append(Coordinates(lat=lat, lng=lng))
    db_session.commit()

    def stub(at):
        return Coordinates(lat=at.lat, lng=at.lng + 0.0015)

    def legs(points):
        out = []
        for a, b in pairwise(points):
            shape = [a] + ([stub(a)] if a in far else []) + ([stub(b)] if b in far else []) + [b]
            out.append(shape)
        return out

    on_streets(legs)
    meta = _preview(client, budget_meters=10000).json()["meta"]
    path = [meta["out_leg"], *meta["legs"], meta["home_leg"]]
    walked = sum(
        read.meters_between(Coordinates(**a), Coordinates(**b))
        for leg in path
        for a, b in pairwise(leg)
    )
    assert walked >= route_solver.ROUTE_FILL * 10000, f"a 10km ask walked {walked:.0f}m"


def _authored(session, memory_ids, status="published"):
    route_id = session.execute(
        text("INSERT INTO routes (title, status) VALUES ('A walk', :s) RETURNING id"),
        {"s": status},
    ).scalar()
    for position, memory_id in enumerate(memory_ids):
        session.execute(
            text("INSERT INTO route_stops (route_id, position, memory_id) VALUES (:r, :p, :m)"),
            {"r": route_id, "p": position, "m": memory_id},
        )
    return route_id


def test_an_authored_route_serves_its_stops_in_order_locked_and_without_hidden_ones(
    client, db_session
):
    first, hidden, last = _offset(db_session, 3), _offset(db_session, 2), _offset(db_session, 1)
    db_session.execute(text("UPDATE memories SET hidden = TRUE WHERE id = :m"), {"m": hidden})
    route_id = _authored(db_session, [first, hidden, last])
    db_session.commit()

    route = client.get(f"/v1/routes/{route_id}").json()
    assert [m["id"] for m in route["memories"]] == [first, last]
    assert all(m["locked"] and m["summary"] == "" for m in route["memories"])


def test_a_draft_route_is_not_served(client, db_session):
    route_id = _authored(db_session, [_offset(db_session, 1)], status="draft")
    db_session.commit()

    assert client.get(f"/v1/routes/{route_id}").status_code == 404
    assert client.get(f"/v1/routes/{route_id + 1}").status_code == 404


def test_a_stop_hidden_after_the_accept_drops_out_of_todays_walk(client, db_session):
    _offset(db_session, 1)
    _offset(db_session, 2)
    db_session.commit()
    stops = [m["id"] for m in _route(client).json()["memories"]]

    db_session.execute(text("UPDATE memories SET hidden = TRUE WHERE id = :m"), {"m": stops[0]})
    db_session.commit()

    walk = client.get(f"/v1/routes/today?device={DEVICE}").json()
    assert [m["id"] for m in walk["memories"]] == stops[1:]


def test_the_unlock_that_earns_the_last_stop_finishes_the_walk_once(client, db_session):
    for n in (1, 2):
        _offset(db_session, n)
    db_session.commit()
    stops = [(m["id"], m["place"]["coordinates"]) for m in _route(client).json()["memories"]]

    def unlock(memory_id, at):
        client.post(
            f"/v1/memories/{memory_id}/unlock",
            json={"device": DEVICE, "lat": at["lat"], "lng": at["lng"]},
        )
        return db_session.execute(text("SELECT completed_at FROM daily_routes")).scalar()

    assert unlock(*stops[0]) is None
    finished = unlock(*stops[1])
    assert finished is not None
    assert unlock(*stops[1]) == finished, "set once, never moved"


def test_walked_lists_the_accounts_walks_with_earned_stops_open(client, db_session):
    for n in (1, 2):
        _offset(db_session, n)
    db_session.commit()
    stops = _route(client).json()["memories"]
    at = stops[0]["place"]["coordinates"]
    client.post(f"/v1/memories/{stops[0]['id']}/unlock", json={"device": DEVICE, **at})

    def walks(device=DEVICE):
        response = client.get(f"/v1/routes/walked?device={device}")
        assert response.status_code == 200
        return response.json()["walks"]

    [walk] = walks()
    assert walk["meta"]["route_date"] == read.gate.today().isoformat()
    assert (walk["meta"]["earned"], walk["meta"]["size"]) == (1, 2)
    assert walk["meta"]["completed_at"] is None
    assert [m["locked"] for m in walk["memories"]] == [False, True]
    assert walk["memories"][0]["summary"] and not walk["memories"][1]["summary"]

    at = stops[1]["place"]["coordinates"]
    client.post(f"/v1/memories/{stops[1]['id']}/unlock", json={"device": DEVICE, **at})
    assert walks()[0]["meta"]["completed_at"] is not None

    sibling, stranger = (
        "22222222-2222-2222-2222-222222222222",
        "33333333-3333-3333-3333-333333333333",
    )
    user = db_session.execute(
        text("INSERT INTO users (id) VALUES (gen_random_uuid()) RETURNING id")
    ).scalar()
    db_session.execute(
        text("UPDATE devices SET user_id = :u WHERE id = CAST(:d AS uuid)"),
        {"u": user, "d": DEVICE},
    )
    db_session.execute(
        text("INSERT INTO devices (id, user_id) VALUES (CAST(:d AS uuid), :u)"),
        {"d": sibling, "u": user},
    )
    db_session.commit()
    assert [w["meta"]["earned"] for w in walks(sibling)] == [2], "a new phone gets its history"
    assert walks(stranger) == []


def test_a_theme_keeps_only_stops_carrying_its_tag(client, db_session):
    food = set()
    for n in range(1, 7):
        place = _place(db_session, f"Stop {n}", LAT + n * 0.001, LNG)
        tags = ["food"] if n % 2 else ["music"]
        memory = _historical(db_session, place, f"memory {n}", f"https://e.invalid/{n:0>11}", tags)
        if n % 2:
            food.add(memory)
    db_session.commit()

    chosen = {
        m["id"]
        for m in client.get(
            f"/v1/routes/preview?device={DEVICE}&lat={LAT}&lng={LNG}&budget_meters=4000&tag=food"
        ).json()["memories"]
    }
    assert chosen == food
    accepted = client.post(
        "/v1/routes/today",
        json={"device": DEVICE, "lat": LAT, "lng": LNG, "budget_meters": 4000, "tag": "food"},
    ).json()
    assert {m["id"] for m in accepted["memories"]} == food


def test_a_theme_outside_the_vocabulary_is_refused(client):
    query = f"device={DEVICE}&lat={LAT}&lng={LNG}&budget_meters=4000&tag=gossip"
    assert client.get(f"/v1/routes/preview?{query}").status_code == 422


def test_one_way_is_asked_for_per_walk_and_stored_with_it(client, db_session):
    for n in range(1, 4):
        _offset(db_session, n)
    db_session.commit()

    query = f"device={DEVICE}&lat={LAT}&lng={LNG}&budget_meters=4000&loop=false"
    assert client.get(f"/v1/routes/preview?{query}").json()["meta"]["loop"] is False
    accepted = client.post(
        "/v1/routes/today",
        json={"device": DEVICE, "lat": LAT, "lng": LNG, "budget_meters": 4000, "loop": False},
    )
    assert accepted.json()["meta"]["loop"] is False
    # Read back tomorrow's way: from the row, not from the server's default.
    assert client.get(f"/v1/routes/today?device={DEVICE}").json()["meta"]["loop"] is False
    walked = client.get(f"/v1/routes/walked?device={DEVICE}").json()["walks"]
    assert walked[0]["meta"]["loop"] is False


def test_a_loop_is_routed_through_its_start_so_out_and_home_cannot_share_a_street(
    client, db_session, monkeypatch, on_streets
):
    """The start is a route's end, and an end may turn round: out and home took
    the same stretch to the corner. Routed once more past home, the start is a
    waypoint mid-route, and the leg after it is the way out."""
    for n in range(1, 4):
        _offset(db_session, n)
    db_session.commit()
    asked = []

    def legs(points):
        asked.append(points)
        return [
            [a, Coordinates(lat=a.lat, lng=a.lng + 0.0001 * i), b]
            for i, (a, b) in enumerate(pairwise(points))
        ]

    on_streets(legs)
    meta = _preview(client).json()["meta"]
    start = Coordinates(lat=LAT, lng=LNG)
    points = asked[-1]
    assert points[0] == start and points[-2] == start and points[-1] == points[1]
    # The out leg is the last one routed, the one leaving the start mid-route.
    assert meta["out_leg"][1]["lng"] == pytest.approx(LNG + 0.0001 * (len(points) - 2))


def test_another_day_or_show_me_another_is_a_different_walk_as_good(
    client, db_session, monkeypatch, on_streets
):
    """Stops on a ring round the start: many loops are as good as the best, so
    the day and "Show me another" take turns through them, and the accept
    stores the one previewed."""
    for n in range(12):
        a = 2 * math.pi * n / 12
        place = _place(
            db_session, f"Ring {n}", LAT + 0.005 * math.cos(a), LNG + 0.008 * math.sin(a)
        )
        _historical(db_session, place, f"ring memory {n}", f"https://e.invalid/{n:0>11}")
    db_session.commit()
    on_streets()

    def ids(again=0):
        preview = client.get(
            f"/v1/routes/preview?device={DEVICE}&lat={LAT}&lng={LNG}&budget_meters=4000"
            f"&again={again}"
        ).json()
        return [m["id"] for m in preview["memories"]]

    assert ids(1) != ids(0)
    assert ids(0) == ids(0)
    days = set()
    for k in range(7):
        monkeypatch.setattr(read.gate, "today", lambda k=k: datetime.date(2026, 9, 24 + k))
        days.add(frozenset(ids()))
    assert len(days) > 1

    shown = ids(1)
    accepted = client.post(
        "/v1/routes/today",
        json={"device": DEVICE, "lat": LAT, "lng": LNG, "budget_meters": 4000, "again": 1},
    ).json()
    assert [m["id"] for m in accepted["memories"]] == shown


def _include(client, memory_id, **extra):
    params = f"device={DEVICE}&lat={LAT}&lng={LNG}&budget_meters=4000&include={memory_id}"
    return client.get(
        f"/v1/routes/preview?{params}" + "".join(f"&{k}={v}" for k, v in extra.items())
    )


def test_walk_here_puts_that_memory_on_the_walk_and_the_accept_agrees(client, db_session):
    ids = [_offset(db_session, n) for n in range(1, 9)]
    db_session.commit()
    plain = {m["id"] for m in _preview(client).json()["memories"]}
    pin = next(i for i in ids if i not in plain)

    preview = [m["id"] for m in _include(client, pin).json()["memories"]]
    assert pin in preview and len(preview) == 5
    accepted = client.post(
        "/v1/routes/today",
        json={"device": DEVICE, "lat": LAT, "lng": LNG, "budget_meters": 4000, "include": pin},
    ).json()
    assert [m["id"] for m in accepted["memories"]] == preview


def test_walk_here_refuses_what_could_never_be_a_stop(client, db_session):
    _offset(db_session, 1)
    earned, hidden, far = _offset(db_session, 2), _offset(db_session, 3), _offset(db_session, 30)
    db_session.execute(text("UPDATE memories SET hidden = TRUE WHERE id = :m"), {"m": hidden})
    db_session.execute(
        text("INSERT INTO devices (id) VALUES (CAST(:d AS uuid)) ON CONFLICT (id) DO NOTHING"),
        {"d": DEVICE},
    )
    db_session.execute(
        text("INSERT INTO unlocks (device_id, memory_id) VALUES (CAST(:d AS uuid), :m)"),
        {"d": DEVICE, "m": earned},
    )
    db_session.commit()

    for pin in (earned, hidden, far, far + 1000):
        refused = _include(client, pin)
        assert refused.status_code == 422, pin
        assert refused.json()["detail"] == {"reason": "not_a_stop"}
        accepted = client.post(
            "/v1/routes/today",
            json={"device": DEVICE, "lat": LAT, "lng": LNG, "budget_meters": 4000, "include": pin},
        )
        assert accepted.status_code == 422
    assert _stored(db_session) == 0


def test_walk_here_is_not_filtered_out_by_a_theme(client, db_session):
    for n in range(1, 5):
        place = _place(db_session, f"Stop {n}", LAT + n * 0.001, LNG)
        _historical(db_session, place, f"memory {n}", f"https://e.invalid/{n:0>11}", ["food"])
    music = _offset(db_session, 5)
    db_session.commit()

    assert music in {m["id"] for m in _include(client, music, tag="food").json()["memories"]}


def test_walk_here_is_never_the_stop_the_cleanup_drops(client, db_session, on_streets):
    """The layout of the out-and-back test above, but stop 2 was asked for."""
    ids = {n: _offset(db_session, n) for n in range(1, 7)}
    db_session.commit()
    spur = Coordinates(lat=LAT + 0.002, lng=LNG)
    stub = Coordinates(lat=LAT + 0.002, lng=LNG + 0.0004)
    on_streets(
        lambda points: [[a, stub, b] if spur in (a, b) else [a, b] for a, b in pairwise(points)]
    )

    assert ids[2] in [m["id"] for m in _include(client, ids[2]).json()["memories"]]


def test_walk_here_too_far_by_street_says_how_long_a_walk_reaches_it(
    client, db_session, monkeypatch
):
    pin = _offset(db_session, 4)
    db_session.commit()

    def table(points):
        # The crow says 445m, so it is within half of 1km; the streets say half as far again.
        return [[read.meters_between(a, b) * 1.5 for b in points] for a in points], [0.0] * len(
            points
        )

    monkeypatch.setattr(route_solver, "street_table", table)
    params = f"device={DEVICE}&lat={LAT}&lng={LNG}&budget_meters=1000&include={pin}"
    refused = client.get(f"/v1/routes/preview?{params}")
    assert refused.status_code == 422
    detail = refused.json()["detail"]
    assert detail["reason"] == "too_far"
    assert 1300 < detail["min_budget_meters"] < 1400
