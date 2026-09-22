"""Hearting a memory: one-way, idempotent per device, no un-hearting.

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
