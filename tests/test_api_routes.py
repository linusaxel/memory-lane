"""Today's walk: GET /v1/routes/preview proposes it, POST /v1/routes/today
accepts it for the day, GET /v1/routes/today reads it back.

Mirrors tests/test_api_unlock.py's fixture style - a real ephemeral database,
a TestClient, and assertions on the JSON rather than on internals, because the
thing that matters is what a device actually receives.
"""

import datetime
import math
from itertools import pairwise
from types import SimpleNamespace

import pytest
from sqlalchemy import text

from api import accounts, read, route_solver, streets
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


def _stranger(session, place_id, summary):
    """Always gated - user_id is the other half of is_gated."""
    user_id = session.execute(
        text("INSERT INTO users (id) VALUES (gen_random_uuid()) RETURNING id")
    ).scalar()
    return session.execute(
        text(
            "INSERT INTO memories (place_id, content_id, timestamp_start, summary, "
            "extraction_confidence, tags, layer, user_id) VALUES "
            "(:p, NULL, NULL, :s, 'high', ARRAY['personal']::varchar[], 'stranger', "
            ":u) RETURNING id"
        ),
        {"p": place_id, "s": summary, "u": user_id},
    ).scalar()


def _offset(session, n, layer="historical"):
    """A gated memory ~n*100m north of LAT,LNG - far enough apart that no two
    share a grid cell, close enough to fit a 4km walk."""
    place = _place(session, f"Stop {n}", LAT + n * 0.001, LNG)
    if layer == "stranger":
        return _stranger(session, place, f"stranger memory {n}")
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
    assert preview["meta"]["size"] == 4
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

    # ~111m apart in a line north: 1km reaches 3, but asks for one stop a km.
    assert _preview(client, budget_meters=1000).json()["meta"]["size"] == 1


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


def test_a_dull_story_is_never_a_stop_but_an_unscored_one_is(client, db_session):
    dull, fine, unscored = (_offset(db_session, n) for n in (1, 2, 3))
    db_session.execute(
        text("UPDATE memories SET walk_score = :s WHERE id = :m"), {"s": 3, "m": dull}
    )
    db_session.execute(
        text("UPDATE memories SET walk_score = :s WHERE id = :m"), {"s": 4, "m": fine}
    )
    db_session.commit()

    ids = [m["id"] for m in _route(client).json()["memories"]]
    assert dull not in ids, "a 3 is no stop, even with nothing better nearby"
    assert fine in ids and unscored in ids


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
    assert len(chosen) == 4
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


def test_a_stop_hidden_after_the_accept_drops_out_of_todays_walk(client, db_session):
    _offset(db_session, 1)
    _offset(db_session, 2)
    db_session.commit()
    stops = [m["id"] for m in _route(client).json()["memories"]]

    db_session.execute(text("UPDATE memories SET hidden = TRUE WHERE id = :m"), {"m": stops[0]})
    db_session.commit()

    walk = client.get(f"/v1/routes/today?device={DEVICE}").json()
    assert [m["id"] for m in walk["memories"]] == stops[1:]


def test_the_mystery_stop_is_off_every_stop_and_on_the_way():
    def at(n, north, east=0.0):
        return SimpleNamespace(
            id=n, lat=LAT + north / 111_320, lng=LNG + east / 63_000, walk_score=6
        )

    first, last = at(1, 300), at(2, 900)
    candidates = [
        first,
        last,
        at(3, 600, 30),  # on the way, 300 m from both stops
        at(4, 350, 10),  # on the way, but at a stop
        at(5, 600, 200),  # between them, but off the way
    ]
    line = [Coordinates(lat=c.lat, lng=c.lng) for c in (first, last)]
    start = Coordinates(lat=LAT, lng=LNG)

    assert route_solver._mystery(candidates, [1, 2], line, [start, None]).id == 3
    assert route_solver._mystery(candidates[:2] + candidates[3:], [1, 2], line, [start]) is None


def _mystery_walk(db_session):
    """Two stops north of LAT,LNG on a 2 km loop, and a third memory beside the
    way between them that the walk passes and never stops at."""
    _offset(db_session, 2.5)
    _offset(db_session, 6.5)
    place = _place(db_session, "Mystery", LAT + 0.0045, LNG + 0.0003)
    mystery = _historical(db_session, place, "the mystery", "https://e.invalid/mystery0000")
    db_session.commit()
    return mystery


def test_a_mystery_stop_is_withheld_until_the_phone_is_near_it(client, db_session):
    mystery = _mystery_walk(db_session)

    def withheld(walk):
        return walk["mystery"]["id"] == 0 and walk["mystery"]["place"]["coordinates"] is None

    preview = _preview(client, budget_meters=2000).json()
    assert mystery not in [m["id"] for m in preview["memories"]]
    assert withheld(preview)
    accepted = _route(client, budget_meters=2000).json()
    assert withheld(accepted) and accepted["meta"]["size"] == 2

    today = f"/v1/routes/today?device={DEVICE}"
    assert withheld(client.get(today).json())
    assert withheld(client.get(f"{today}&lat={LAT}&lng={LNG}").json())
    found = client.get(f"{today}&lat={LAT + 0.004}&lng={LNG}").json()["mystery"]
    assert found["id"] == mystery and found["locked"] and found["summary"] == ""
    assert found["place"]["coordinates"] is not None


def test_a_mystery_stop_opens_like_a_stop_and_is_not_owed(client, db_session):
    mystery = _mystery_walk(db_session)
    stops = [
        (m["id"], m["place"]["coordinates"])
        for m in _route(client, budget_meters=2000).json()["memories"]
    ]

    def unlock(memory_id, lat, lng):
        return client.post(
            f"/v1/memories/{memory_id}/unlock", json={"device": DEVICE, "lat": lat, "lng": lng}
        )

    assert unlock(mystery, LAT + 0.0045, LNG + 0.0003).json()["locked"] is False
    found = client.get(f"/v1/routes/today?device={DEVICE}").json()["mystery"]
    assert found["id"] == mystery and not found["locked"], "found stays found"
    for memory_id, at in stops:
        unlock(memory_id, at["lat"], at["lng"])
    finished = db_session.execute(text("SELECT completed_at FROM daily_routes")).scalar()
    assert finished is not None


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
    stop = accepted.json()["memories"][0]
    at = stop["place"]["coordinates"]
    client.post(f"/v1/memories/{stop['id']}/unlock", json={"device": DEVICE, **at})
    walked = client.get(f"/v1/routes/walked?device={DEVICE}").json()["walks"]
    assert walked[0]["meta"]["loop"] is False


def test_a_one_way_walk_to_an_end_passes_stops_on_the_way_and_finishes_there(
    client, db_session, on_streets
):
    """Stops north and south, the end 2.2km north: a 2.5km walk has no room to
    double back 400m south, and its last leg is the walk to the end."""
    for n in (1, 2, 3, -4, -5, -6):
        _offset(db_session, n)
    db_session.commit()
    on_streets()
    end = {"lat": LAT + 0.02, "lng": LNG}
    query = f"device={DEVICE}&lat={LAT}&lng={LNG}&budget_meters=2500"

    preview = client.get(f"/v1/routes/preview?{query}&end_lat={end['lat']}&end_lng={LNG}")
    body = preview.json()
    assert body["meta"]["loop"] is False
    assert body["memories"] and all(
        m["place"]["coordinates"]["lat"] > LAT for m in body["memories"]
    )
    assert body["meta"]["home_leg"][-1] == end
    accepted = client.post(
        "/v1/routes/today",
        json={"device": DEVICE, "lat": LAT, "lng": LNG, "budget_meters": 2500, "end": end},
    ).json()
    assert [m["id"] for m in accepted["memories"]] == [m["id"] for m in body["memories"]]
    assert accepted["meta"]["loop"] is False


def test_an_end_out_of_reach_says_how_long_a_walk_reaches_it(client, db_session):
    _offset(db_session, 1)
    db_session.commit()
    query = f"device={DEVICE}&lat={LAT}&lng={LNG}&budget_meters=4000"

    # 5.6km north, and 1.3x that without streets.
    refused = client.get(f"/v1/routes/preview?{query}&end_lat={LAT + 0.05}&end_lng={LNG}")
    assert refused.status_code == 422
    assert refused.json()["detail"]["reason"] == "too_far"
    assert 7200 < refused.json()["detail"]["min_budget_meters"] < 7300
    assert client.get(f"/v1/routes/preview?{query}&end_lat={LAT}").status_code == 422


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
            f"/v1/routes/preview?device={DEVICE}&lat={LAT}&lng={LNG}&budget_meters=5000"
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
        json={"device": DEVICE, "lat": LAT, "lng": LNG, "budget_meters": 5000, "again": 1},
    ).json()
    assert [m["id"] for m in accepted["memories"]] == shown


def _end(client):
    return client.post("/v1/routes/today/end", json={"device": DEVICE})


def test_an_ended_walk_frees_the_day_for_another(client, db_session):
    for n in range(1, 9):
        _offset(db_session, n)
    db_session.commit()

    first = _route(client).json()
    assert _end(client).status_code == 204
    assert client.get(f"/v1/routes/today?device={DEVICE}").status_code == 404
    assert _end(client).status_code == 204, "the same tap twice is not an error"

    second = _route(client, budget_meters=1000).json()
    assert second["meta"]["budget_meters"] == 1000 != first["meta"]["budget_meters"]
    assert client.get(f"/v1/routes/today?device={DEVICE}").json() == second
    assert _stored(db_session) == 1, "the first opened nothing, so ending it deleted it"


def _walked(client):
    return client.get(f"/v1/routes/walked?device={DEVICE}").json()["walks"]


def test_a_walk_that_opened_nothing_is_deleted_as_it_ends(client, db_session):
    for n in (1, 2):
        _offset(db_session, n)
    db_session.commit()

    _route(client)
    assert _walked(client) == [], "listed from its first unlock, not before"
    _end(client)
    assert _stored(db_session) == 0

    stop = _route(client).json()["memories"][0]
    at = stop["place"]["coordinates"]
    client.post(f"/v1/memories/{stop['id']}/unlock", json={"device": DEVICE, **at})
    _end(client)
    assert _stored(db_session) == 1
    [walk] = _walked(client)
    assert walk["meta"]["earned"] == 1


def test_accepting_sweeps_a_past_walk_that_opened_nothing(client, db_session):
    memory = _offset(db_session, 1)
    for n in (2, 3):
        _offset(db_session, n)
    db_session.execute(text("INSERT INTO devices (id) VALUES (CAST(:d AS uuid))"), {"d": DEVICE})
    yesterday = read.gate.today() - datetime.timedelta(days=1)
    db_session.execute(
        text(
            "INSERT INTO daily_routes (device_id, route_date, memory_ids) "
            "VALUES (CAST(:d AS uuid), :day, ARRAY[:m])"
        ),
        {"d": DEVICE, "day": yesterday, "m": memory},
    )
    db_session.commit()

    _route(client)
    dates = db_session.execute(text("SELECT route_date FROM daily_routes")).scalars().all()
    assert dates == [read.gate.today()], "never ended, opened nothing: gone"


def test_an_ended_walk_keeps_what_it_earned(client, db_session):
    for n in (1, 2):
        _offset(db_session, n)
    db_session.commit()
    stops = _route(client).json()["memories"]
    earned = (stops[0]["id"], stops[0]["place"]["coordinates"])

    def unlock(memory_id, at):
        return client.post(f"/v1/memories/{memory_id}/unlock", json={"device": DEVICE, **at})

    assert unlock(*earned).status_code == 200
    _end(client)

    [walk] = client.get(f"/v1/routes/walked?device={DEVICE}").json()["walks"]
    assert (walk["meta"]["earned"], walk["meta"]["completed_at"]) == (1, None)


def _subscribe(session, days=30):
    """Bind DEVICE to an account paid up for `days` (negative: lapsed)."""
    session.execute(
        text("INSERT INTO devices (id) VALUES (CAST(:d AS uuid)) ON CONFLICT DO NOTHING"),
        {"d": DEVICE},
    )
    user_id = session.execute(
        text("INSERT INTO users (id) VALUES (gen_random_uuid()) RETURNING id")
    ).scalar()
    session.execute(
        text("UPDATE devices SET user_id = :u WHERE id = CAST(:d AS uuid)"),
        {"u": user_id, "d": DEVICE},
    )
    session.execute(
        text(
            "INSERT INTO subscriptions (user_id, expires_at) "
            "VALUES (:u, CURRENT_TIMESTAMP + make_interval(days => :days))"
        ),
        {"u": user_id, "days": days},
    )
    session.commit()


def _walk_one_stop(client):
    stop = _route(client).json()["memories"][0]
    at = stop["place"]["coordinates"]
    assert client.post(
        f"/v1/memories/{stop['id']}/unlock", json={"device": DEVICE, **at}
    ).is_success
    _end(client)


def _xp(client):
    return client.get(f"/v1/me?device={DEVICE}").json()["xp"]


def _finish(client):
    for stop in _route(client).json()["memories"]:
        at = stop["place"]["coordinates"]
        assert client.post(
            f"/v1/memories/{stop['id']}/unlock", json={"device": DEVICE, **at}
        ).is_success


def test_a_free_walker_walks_once_a_week(client, db_session):
    """docs/10, "A free walk a week": a walk's stops are free, so a second
    walk would open any pin for nothing. The refusal names the next free day."""
    for n in range(1, 9):
        _offset(db_session, n)
    db_session.commit()
    _walk_one_stop(client)
    today = read.gate.today()
    next_free = (today + datetime.timedelta(days=7)).isoformat()

    for refused in (_preview(client), _route(client)):
        assert refused.status_code == 403
        assert refused.json()["detail"] == {"reason": "walked", "next_free": next_free}

    def walked_days_ago(days):
        db_session.execute(
            text("UPDATE daily_routes SET route_date = :d"),
            {"d": today - datetime.timedelta(days=days)},
        )
        db_session.commit()

    walked_days_ago(6)
    assert _preview(client).status_code == 403
    walked_days_ago(7)
    assert _route(client).is_success


def test_a_free_walk_takes_the_best_stories_when_there_are_enough(client, db_session):
    """Good stories near, the best a little further: a free walk goes further."""
    ids = [_offset(db_session, n) for n in range(1, 9)]
    best = ids[4:]
    db_session.execute(text("UPDATE memories SET walk_score = 7"))
    db_session.execute(text("UPDATE memories SET walk_score = 8 WHERE id = ANY(:b)"), {"b": best})
    db_session.commit()

    picked = [m["id"] for m in _route(client).json()["memories"]]
    assert picked and set(picked) <= set(best)


def test_a_walk_that_opened_nothing_gives_the_day_back(client, db_session):
    for n in range(1, 9):
        _offset(db_session, n)
    db_session.commit()
    _route(client)
    _end(client)
    assert _route(client).is_success


def test_a_subscriber_walks_again(client, db_session):
    for n in range(1, 9):
        _offset(db_session, n)
    _subscribe(db_session)
    _walk_one_stop(client)
    assert _route(client).is_success


def test_finishing_a_walk_earns_xp_once_a_day(client, db_session):
    for n in range(1, 9):
        _offset(db_session, n)
    _subscribe(db_session)
    _finish(client)
    first = _xp(client)
    assert first > 0
    _end(client)
    _finish(client)
    assert _xp(client) == first, "a subscriber's second walk earns nothing"


def test_a_walk_left_unfinished_earns_no_key(client, db_session):
    for n in (1, 2):
        _offset(db_session, n)
    db_session.commit()
    _walk_one_stop(client)
    assert _xp(client) == 0


def _shape(session, memory_id, tags, year):
    session.execute(
        text(
            "UPDATE memories SET tags = CAST(:t AS varchar[]), "
            "happened_at = make_date(:y, 6, 1) WHERE id = :id"
        ),
        {"t": tags, "y": year, "id": memory_id},
    )


def _shaped_ids(client, query="", **body):
    preview = client.get(
        f"/v1/routes/preview?device={DEVICE}&lat={LAT}&lng={LNG}&budget_meters=1000{query}"
    )
    accepted = client.post(
        "/v1/routes/today",
        json={"device": DEVICE, "lat": LAT, "lng": LNG, "budget_meters": 1000, **body},
    )
    ids = [m["id"] for m in preview.json()["memories"]]
    assert ids == [m["id"] for m in accepted.json()["memories"]], "accept plans the preview"
    return ids


def _themed_pair(session):
    """Two stops as good as each other, ~100m either side of the start: a 1km
    walk takes one, and only the theme tells them apart."""
    south = _historical(
        session, _place(session, "South", LAT - 0.001, LNG), "south", "https://e.invalid/s"
    )
    north = _historical(
        session, _place(session, "North", LAT + 0.001, LNG), "north", "https://e.invalid/n"
    )
    _shape(session, south, ["music"], 1930)
    _shape(session, north, ["history"], 1990)
    return south, north


def test_a_subscribers_theme_and_era_lean_the_walk(client, db_session):
    south, north = _themed_pair(db_session)
    _subscribe(db_session)
    assert _shaped_ids(client, "&tags=history", tags=["history"]) == [north]
    _end(client)
    assert _shaped_ids(client, "&tags=music", tags=["music"]) == [south]
    _end(client)
    assert _shaped_ids(client, "&year_from=1920&year_to=1940", year_from=1920, year_to=1940) == [
        south
    ]
    _end(client)
    era = "&year_from=1980&year_to=1999"
    assert _shaped_ids(client, era, year_from=1980, year_to=1999) == [north]
    _end(client)
    # Both stops carry a theme; only south also meets the era.
    both = "&tags=music&tags=history&year_from=1920&year_to=1940"
    assert _shaped_ids(client, both, tags=["music", "history"], year_from=1920, year_to=1940) == [
        south
    ], "a theme and an era outweigh a theme alone"
    _end(client)

    undated = _offset(db_session, 2)
    db_session.commit()
    walk = _shaped_ids(client, era, year_from=1980, year_to=1999)
    assert undated in walk, "an era leans, it never leaves the undated out"


def test_a_non_subscribers_theme_and_years_change_nothing(client, db_session):
    _themed_pair(db_session)
    db_session.commit()
    plain = [m["id"] for m in _preview(client, budget_meters=1000).json()["memories"]]
    for query in ("&tags=history", "&tags=music", "&year_from=2000"):
        shaped = client.get(
            f"/v1/routes/preview?device={DEVICE}&lat={LAT}&lng={LNG}&budget_meters=1000{query}"
        )
        assert [m["id"] for m in shaped.json()["memories"]] == plain


def test_a_theme_outside_the_vocabulary_is_refused(client, db_session):
    assert (
        client.get(
            f"/v1/routes/preview?device={DEVICE}&lat={LAT}&lng={LNG}&budget_meters=1000&tags=smørrebrød"
        ).status_code
        == 422
    )


def test_the_local_api_can_make_every_device_a_subscriber(client, db_session, monkeypatch):
    monkeypatch.setattr(read, "DEV_SUBSCRIBED", True)
    monkeypatch.setattr(accounts, "DEV_SUBSCRIBED", True)
    _, north = _themed_pair(db_session)
    db_session.commit()
    assert client.get(f"/v1/me?device={DEVICE}").json()["subscribed"]
    assert _shaped_ids(client, "&tags=history", tags=["history"]) == [north]


def _last_walk(session, days_ago=1):
    """A past walk that opened its one stop, far out of today's way."""
    walked = _offset(session, 40)
    session.execute(
        text("INSERT INTO devices (id) VALUES (CAST(:d AS uuid)) ON CONFLICT DO NOTHING"),
        {"d": DEVICE},
    )
    session.execute(
        text("INSERT INTO unlocks (device_id, memory_id) VALUES (CAST(:d AS uuid), :m)"),
        {"d": DEVICE, "m": walked},
    )
    session.execute(
        text(
            "INSERT INTO daily_routes (device_id, route_date, memory_ids, created_at) VALUES "
            "(CAST(:d AS uuid), CURRENT_DATE - :n, ARRAY[:m], "
            "CURRENT_TIMESTAMP - :n * INTERVAL '1 day')"
        ),
        {"d": DEVICE, "n": days_ago, "m": walked},
    )


def _added(session, memory_id, days_ago):
    session.execute(
        text(
            "UPDATE memories SET created_at = CURRENT_TIMESTAMP - :n * INTERVAL '1 day' WHERE id = :id"
        ),
        {"n": days_ago, "id": memory_id},
    )


def test_new_nearby_counts_what_arrived_within_2km_since_the_last_walk(
    client, db_session, monkeypatch
):
    monkeypatch.setattr(read, "FREE_WALK_EVERY_DAYS", 1)
    old, new, far = _offset(db_session, 1), _offset(db_session, 2), _offset(db_session, 30)
    assert _preview(client).json()["meta"]["new_nearby"] == 0, "no walk yet, nothing is new"

    _added(db_session, old, 5)
    _last_walk(db_session, 2)
    _added(db_session, new, 1)
    _added(db_session, far, 1)
    db_session.commit()
    assert _preview(client).json()["meta"]["new_nearby"] == 1


def test_a_memory_new_since_the_last_walk_leans_the_walk(client, db_session, monkeypatch):
    monkeypatch.setattr(read, "FREE_WALK_EVERY_DAYS", 1)
    south, north = _themed_pair(db_session)
    _last_walk(db_session, 2)
    _added(db_session, south, 5)
    _added(db_session, north, 1)
    db_session.commit()
    assert _shaped_ids(client) == [north]
    _end(client)

    _added(db_session, south, 0)
    _added(db_session, north, 5)
    db_session.commit()
    assert _shaped_ids(client) == [south]
