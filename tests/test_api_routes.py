"""GET /v1/routes/today: today's fixed set of nearby, not-yet-earned stops.

Mirrors tests/test_api_unlock.py's fixture style - a real ephemeral database,
a TestClient, and assertions on the JSON rather than on internals, because the
thing that matters is what a device actually receives.
"""

import datetime

import pytest
from sqlalchemy import text

pytestmark = pytest.mark.db

LAT, LNG = 55.6759, 12.5655
DEVICE = "11111111-1111-1111-1111-111111111111"


@pytest.fixture
def client(api_client):
    return api_client


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
    share a grid cell, close enough to stay inside ROUTE_RADIUS_METERS."""
    place = _place(session, f"Stop {n}", LAT + n * 0.001, LNG)
    if layer == "stranger":
        return _stranger(session, place, f"stranger memory {n}", **kw)
    return _historical(session, place, f"historical memory {n}", f"https://e.invalid/{n:0>11}")


def _route(client, **params):
    return client.get(f"/v1/routes/today?device={DEVICE}&{_qs(params)}")


def _qs(params):
    return "&".join(f"{k}={v}" for k, v in params.items())


def test_a_route_is_stable_within_the_day(client, db_session):
    for n in range(1, 7):
        _offset(db_session, n)
    db_session.commit()

    first = _route(client, lat=LAT, lng=LNG).json()
    assert first["meta"]["size"] == 5
    assert len(first["memories"]) == 5

    # A different position the same day must not reroll the route.
    second = _route(client, lat=LAT + 0.02, lng=LNG + 0.02).json()
    assert [m["id"] for m in second["memories"]] == [m["id"] for m in first["memories"]]
    assert second["meta"]["route_date"] == first["meta"]["route_date"]


def test_radius_meters_defaults_to_the_server_default(client, db_session):
    _offset(db_session, 1)
    db_session.commit()

    route = _route(client, lat=LAT, lng=LNG).json()
    assert route["meta"]["radius_meters"] == 4000


def test_an_explicit_radius_is_honoured_and_then_stable(client, db_session):
    _offset(db_session, 1)
    db_session.commit()

    first = _route(client, lat=LAT, lng=LNG, radius_meters=1000).json()
    assert first["meta"]["radius_meters"] == 1000

    # A later call with a different radius must not reroute or restate it -
    # the route, and the radius that produced it, are fixed for the day.
    second = _route(client, lat=LAT, lng=LNG, radius_meters=9000).json()
    assert second["meta"]["radius_meters"] == 1000


def test_lat_lng_are_required_to_start_a_route(client, db_session):
    _offset(db_session, 1)
    db_session.commit()

    resp = client.get(f"/v1/routes/today?device={DEVICE}")
    assert resp.status_code == 400


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

    route = _route(client, lat=LAT, lng=LNG).json()
    ids = [m["id"] for m in route["memories"]]
    assert earned not in ids, "already earning it once should not spend a route slot on it again"
    assert keep in ids


def test_a_route_mixes_layers_when_both_are_available(client, db_session):
    for n in range(1, 4):
        _offset(db_session, n, layer="historical")
    for n in range(4, 6):
        _offset(db_session, n, layer="stranger")
    db_session.commit()

    route = _route(client, lat=LAT, lng=LNG).json()
    layers = {m["layer"] for m in route["memories"]}
    assert layers == {"historical", "stranger"}, "a route of one kind defeats the point of mixing"


def test_a_sparse_area_returns_fewer_than_five_without_erroring(client, db_session):
    _offset(db_session, 1)
    _offset(db_session, 2)
    db_session.commit()

    route = _route(client, lat=LAT, lng=LNG).json()
    assert route["meta"]["size"] == 2
    assert len(route["memories"]) == 2


def test_an_ambiguous_centroid_is_never_a_route_stop(client, db_session):
    """Two places on one point is the model saying 'somewhere in this city' -
    a route sending someone there would open on arrival, which is not a stop,
    it is scenery."""
    shared_place = _place(db_session, "Somewhere", LAT + 0.001, LNG)
    _place(db_session, "Somewhere else", LAT + 0.001, LNG)
    ambiguous = _historical(db_session, shared_place, "a guess", "https://e.invalid/ambiguous1")
    real = _offset(db_session, 2)
    db_session.commit()

    route = _route(client, lat=LAT, lng=LNG).json()
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

    route = _route(client, lat=LAT, lng=LNG).json()
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

    route = _route(client, lat=LAT, lng=LNG).json()
    ids = [m["id"] for m in route["memories"]]
    assert len(stacked_ids & set(ids)) <= 1, "at most one memory from the same place per route"


def test_route_stops_render_locked(client, db_session):
    """Freshly discovered, unwalked stops - rendering them locked is the whole
    point of a route."""
    _offset(db_session, 1)
    db_session.commit()

    route = _route(client, lat=LAT, lng=LNG).json()
    assert route["memories"][0]["locked"] is True
    assert route["memories"][0]["summary"] == ""
