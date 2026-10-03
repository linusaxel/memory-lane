"""The city board: docs/10, "A city board, by opens"."""

import pytest
from sqlalchemy import text

pytestmark = pytest.mark.db

CPH = (55.6761, 12.5683)
AARHUS = (56.1629, 10.2039)


def _memory(session, lat, lng):
    place = session.execute(
        text(
            "INSERT INTO places (name, place_query, coordinates, precision_meters) "
            "VALUES ('p', gen_random_uuid()::text, ST_MakePoint(:lng, :lat)::geography, 50) "
            "RETURNING id"
        ),
        {"lat": lat, "lng": lng},
    ).scalar()
    return session.execute(
        text(
            "INSERT INTO memories (place_id, summary, extraction_confidence) "
            "VALUES (:p, 's', 'high') RETURNING id"
        ),
        {"p": place},
    ).scalar()


def _person(session, name, *devices, on_board=True):
    user = session.execute(
        text(
            "INSERT INTO users (id, display_name, on_board) "
            "VALUES (gen_random_uuid(), :n, :b) RETURNING id"
        ),
        {"n": name, "b": on_board},
    ).scalar()
    for d in devices:
        session.execute(
            text("INSERT INTO devices (id, user_id) VALUES (CAST(:d AS uuid), :u)"),
            {"d": d, "u": user},
        )


def _open(session, device, memory, when="CURRENT_TIMESTAMP"):
    session.execute(
        text(
            f"INSERT INTO unlocks (device_id, memory_id, unlocked_at) "
            f"VALUES (CAST(:d AS uuid), :m, {when})"
        ),
        {"d": device, "m": memory},
    )


def _device(n):
    return f"00000000-0000-0000-0000-{n:012}"


def test_the_board_counts_an_account_in_the_city_this_month(api_client, db_session):
    a, b = (_memory(db_session, *CPH) for _ in range(2))
    far = _memory(db_session, *AARHUS)
    _person(db_session, "Two phones", _device(1), _device(2))
    _person(db_session, None, _device(3))
    _person(db_session, "Hidden", _device(4), on_board=False)

    _open(db_session, _device(1), a)
    _open(db_session, _device(2), a)  # the same memory on a second phone
    _open(db_session, _device(2), b)
    _open(db_session, _device(1), far)  # not Copenhagen
    _open(db_session, _device(3), a)
    _open(db_session, _device(3), b, "CURRENT_TIMESTAMP - INTERVAL '40 days'")  # last month
    for m in (a, b, far):
        _open(db_session, _device(4), m)
    db_session.commit()

    rows = api_client.get(f"/v1/board?device={_device(2)}").json()["rows"]
    assert [(r["rank"], r["display_name"], r["opens"], r["mine"]) for r in rows] == [
        (1, "Two phones", 2, True),
        (2, "Anonymous", 1, False),
    ]


def test_leaving_the_board(api_client, db_session):
    m = _memory(db_session, *CPH)
    _person(db_session, "Me", _device(1))
    _open(db_session, _device(1), m)
    db_session.commit()
    profile = api_client.put("/v1/me/board", json={"device": _device(1), "on_board": False})
    assert profile.json()["on_board"] is False
    assert api_client.get(f"/v1/board?device={_device(1)}").json()["rows"] == []
