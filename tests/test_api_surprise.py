"""A surprise: one memory opened off a walk, for half an hour, once a week.

The phone only says where it was; the server decides. If any of these start
granting freely, a loop of requests opens the map from a sofa.
docs/10-decisions.md#a-surprise-once-a-week.
"""

import pytest
from sqlalchemy import text

pytestmark = pytest.mark.db

LAT, LNG = 55.6759, 12.5655
NEAR = LAT + 0.001  # ~110 m north
FAR = LAT + 0.01  # ~1.1 km north
DEVICE = "11111111-2222-3333-4444-555555555555"
OTHER_DEVICE = "99999999-8888-7777-6666-555555555555"


@pytest.fixture
def client(api_client):
    return api_client


def _memory(session, name, lat):
    place = session.execute(
        text(
            "INSERT INTO places (name, place_query, coordinates, precision_meters) "
            "VALUES (:n, :n, ST_MakePoint(:lng, :lat)::geography, 50) RETURNING id"
        ),
        {"n": name, "lat": lat, "lng": LNG},
    ).scalar()
    content = session.execute(
        text(
            "INSERT INTO content (url, platform, platform_id, source_type) "
            "VALUES (:u, 'text', :u, 'archive') RETURNING id"
        ),
        {"u": f"https://e.invalid/{name}"},
    ).scalar()
    return session.execute(
        text(
            "INSERT INTO memories (place_id, content_id, timestamp_start, summary, "
            "extraction_confidence) VALUES (:p, :c, 0, 'the night the amp caught fire', "
            "'high') RETURNING id"
        ),
        {"p": place, "c": content},
    ).scalar()


@pytest.fixture
def vega(db_session):
    memory = _memory(db_session, "Vega", LAT)
    db_session.commit()
    return memory


def _surprise(client, memory_id, lat=NEAR, device=DEVICE):
    return client.post(
        "/v1/surprise", json={"device": device, "memory_id": memory_id, "lat": lat, "lng": LNG}
    )


def _open(client, memory_id, device=DEVICE):
    return client.post(
        f"/v1/memories/{memory_id}/unlock", json={"device": device, "lat": LAT, "lng": LNG}
    )


def test_a_surprise_names_the_place_and_never_the_story(client, vega):
    granted = _surprise(client, vega)
    assert granted.status_code == 201
    assert granted.json()["place"] == "Vega"
    assert granted.json()["expires_at"].endswith(("Z", "+00:00"))
    assert "amp" not in granted.text


def test_a_surprise_opens_its_memory_standing_on_it(client, vega):
    assert _open(client, vega).status_code == 403
    _surprise(client, vega)
    opened = _open(client, vega)
    assert opened.status_code == 200
    assert opened.json()["summary"] == "the night the amp caught fire"


def test_an_expired_surprise_opens_nothing(client, db_session, vega):
    _surprise(client, vega)
    db_session.execute(
        text("UPDATE surprises SET expires_at = LOCALTIMESTAMP - INTERVAL '1 minute'")
    )
    db_session.commit()
    assert _open(client, vega).json()["detail"] == {"reason": "not_on_walk"}


def test_one_a_week(client, db_session, vega):
    second = _memory(db_session, "Pumpehuset", LAT + 0.0005)
    db_session.commit()
    assert _surprise(client, vega).status_code == 201
    assert _surprise(client, second).status_code == 409
    db_session.execute(text("UPDATE surprises SET granted_at = LOCALTIMESTAMP - INTERVAL '8 days'"))
    db_session.commit()
    assert _surprise(client, second).status_code == 201


def test_too_far_is_refused(client, vega):
    assert _surprise(client, vega, lat=FAR).json()["detail"] == {"reason": "not_now"}


def test_one_already_opened_is_refused(client, vega):
    _surprise(client, vega)
    _open(client, vega)
    # A week later it would still be no surprise.
    assert _surprise(client, vega, device=DEVICE).status_code == 409


def test_another_accounts_surprise_opens_nothing(client, vega):
    _surprise(client, vega, device=OTHER_DEVICE)
    assert _open(client, vega).status_code == 403
