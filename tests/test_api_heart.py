"""Hearting a memory: idempotent per device, and the account can take it back.

Mirrors tests/test_api_unlocks.py's shape - same fixture, same device
constants - since heart_memory is built on the same "device, memory, insert
once" pattern as unlock and report.
"""

import pytest
from sqlalchemy import text

pytestmark = pytest.mark.db

LAT, LNG = 55.6759, 12.5655
DEVICE = "11111111-2222-3333-4444-555555555555"
OTHER_DEVICE = "99999999-8888-7777-6666-555555555555"


@pytest.fixture
def client(api_client):
    return api_client


@pytest.fixture
def memory_id(db_session):
    place = db_session.execute(
        text(
            "INSERT INTO places (name, place_query, coordinates, precision_meters) "
            "VALUES ('Vega', 'Vega', ST_MakePoint(:lng, :lat)::geography, 50) RETURNING id"
        ),
        {"lat": LAT, "lng": LNG},
    ).scalar()
    content = db_session.execute(
        text(
            "INSERT INTO content (url, platform, platform_id, source_type) "
            "VALUES ('https://e.invalid/aaaaaaaaaaa', 'text', 'aaaaaaaaaaa', 'archive') "
            "RETURNING id"
        )
    ).scalar()
    memory = db_session.execute(
        text(
            "INSERT INTO memories (place_id, content_id, timestamp_start, summary, "
            "extraction_confidence) VALUES (:p, :c, 0, 'the night the amp caught fire', 'high') "
            "RETURNING id"
        ),
        {"p": place, "c": content},
    ).scalar()
    db_session.commit()
    return memory


def _heart(client, memory_id, device=DEVICE):
    return client.post(f"/v1/memories/{memory_id}/heart", json={"device": device})


def test_hearting_once_returns_a_count_of_one(client, memory_id):
    res = _heart(client, memory_id)
    assert res.status_code == 200
    assert res.json()["heart_count"] == 1


def test_hearting_twice_from_the_same_device_stays_at_one(client, memory_id, db_session):
    _heart(client, memory_id)
    res = _heart(client, memory_id)
    assert res.json()["heart_count"] == 1
    assert db_session.execute(text("SELECT count(*) FROM memory_hearts")).scalar() == 1


def test_two_devices_hearting_the_same_memory_counts_both(client, memory_id):
    _heart(client, memory_id, device=DEVICE)
    res = _heart(client, memory_id, device=OTHER_DEVICE)
    assert res.json()["heart_count"] == 2


def test_the_count_shows_up_on_a_single_read(client, memory_id):
    _heart(client, memory_id)
    memory = client.get(f"/v1/memories/{memory_id}").json()
    assert memory["heart_count"] == 1


def test_the_count_shows_up_on_nearby(client, memory_id):
    _heart(client, memory_id)
    memories = client.get(f"/v1/memories/nearby?lat={LAT}&lng={LNG}&radius_km=1").json()["memories"]
    assert len(memories) == 1
    assert memories[0]["heart_count"] == 1


def test_a_device_appears_the_first_time_it_hearts_something(client, memory_id, db_session):
    """Nothing registers a device; earning or hearting something does."""
    assert db_session.execute(text("SELECT count(*) FROM devices")).scalar() == 0
    _heart(client, memory_id)
    assert db_session.execute(text("SELECT count(*) FROM devices")).scalar() == 1


def test_a_device_id_that_is_not_a_uuid_is_rejected(client, memory_id):
    assert (
        client.post(
            f"/v1/memories/{memory_id}/heart", json={"device": "../../etc/passwd"}
        ).status_code
        == 422
    )


def test_hearting_something_that_does_not_exist_is_a_404(client):
    assert _heart(client, 999999).status_code == 404


def test_you_cannot_heart_your_own_memory(client, memory_id, db_session):
    user = db_session.execute(
        text("INSERT INTO users (id) VALUES (gen_random_uuid()) RETURNING id")
    ).scalar()
    db_session.execute(
        text("INSERT INTO devices (id, user_id) VALUES (CAST(:d AS uuid), :u)"),
        {"d": DEVICE, "u": user},
    )
    db_session.execute(
        text("UPDATE memories SET user_id = :u WHERE id = :m"), {"u": user, "m": memory_id}
    )
    db_session.commit()
    assert _heart(client, memory_id).status_code == 403
    assert db_session.execute(text("SELECT count(*) FROM memory_hearts")).scalar() == 0
    assert _heart(client, memory_id, device=OTHER_DEVICE).status_code == 200


def _unlocks(client):
    return client.get(f"/v1/unlocks?device={DEVICE}").json()["memories"]


def _mine(client):
    return client.get(f"/v1/me/memories?device={DEVICE}")


def test_the_collection_says_which_ones_you_hearted(client, memory_id):
    client.post(f"/v1/memories/{memory_id}/unlock", json={"device": DEVICE, "lat": LAT, "lng": LNG})
    assert _unlocks(client)[0]["hearted"] is False
    _heart(client, memory_id, device=OTHER_DEVICE)
    assert _unlocks(client)[0]["hearted"] is False, "someone else's heart is not yours"
    _heart(client, memory_id)
    assert _unlocks(client)[0]["hearted"] is True


def test_the_author_sees_when_the_last_heart_came_never_from_whom(client, memory_id, db_session):
    user = db_session.execute(
        text("INSERT INTO users (id) VALUES (gen_random_uuid()) RETURNING id")
    ).scalar()
    db_session.execute(
        text("INSERT INTO devices (id, user_id) VALUES (CAST(:d AS uuid), :u)"),
        {"d": DEVICE, "u": user},
    )
    db_session.execute(
        text("UPDATE memories SET user_id = :u WHERE id = :m"), {"u": user, "m": memory_id}
    )
    db_session.commit()
    assert _mine(client).json()["memories"][0]["last_hearted_at"] is None
    _heart(client, memory_id, device=OTHER_DEVICE)
    # With its zone: a phone reads a naive timestamp as local time.
    assert _mine(client).json()["memories"][0]["last_hearted_at"].endswith(("Z", "+00:00"))
    assert OTHER_DEVICE not in _mine(client).text


def _unheart(client, memory_id, device=DEVICE):
    return client.delete(f"/v1/memories/{memory_id}/heart?device={device}")


def test_a_heart_can_be_taken_back(client, memory_id):
    _heart(client, memory_id)
    _heart(client, memory_id, device=OTHER_DEVICE)
    res = _unheart(client, memory_id)
    assert res.status_code == 200
    assert res.json()["heart_count"] == 1, "only this device's heart comes off"
    assert _unheart(client, memory_id).json()["heart_count"] == 1, "twice is a no-op"


def test_taking_back_covers_every_phone_on_the_account(client, memory_id, db_session):
    """/v1/unlocks says hearted for the account, so undo has to clear it there."""
    user = db_session.execute(
        text("INSERT INTO users (id) VALUES (gen_random_uuid()) RETURNING id")
    ).scalar()
    for d in (DEVICE, OTHER_DEVICE):
        db_session.execute(
            text("INSERT INTO devices (id, user_id) VALUES (CAST(:d AS uuid), :u)"),
            {"d": d, "u": user},
        )
    db_session.commit()
    _heart(client, memory_id, device=OTHER_DEVICE)
    assert _unheart(client, memory_id).json()["heart_count"] == 0
