"""Unlocks, server-side, without accounts.

Until this existed the only record that somebody had earned a memory lived in
that phone's AsyncStorage: clear the app's data and the walking was undone. A
device claims an opaque UUID it generated itself, which is enough to make a
collection durable and to give a future sign-in something to attach to, and not
enough to identify anybody.

The properties worth holding: an unlock is only recorded when the gate actually
opened, unlocking twice does not move the date, and the collection comes back
readable from anywhere - re-locking something somebody stood in the rain for is
a punishment for leaving.
"""

import pytest
from sqlalchemy import text

from tests.conftest import give_user, on_walk

pytestmark = pytest.mark.db

LAT, LNG = 55.6759, 12.5655
FAR_LAT = LAT + 0.01
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
    give_user(db_session, DEVICE)
    on_walk(db_session, DEVICE, memory)
    return memory


def _unlock(client, memory_id, lat=LAT, lng=LNG, device=DEVICE):
    return client.post(
        f"/v1/memories/{memory_id}/unlock", json={"device": device, "lat": lat, "lng": lng}
    ).json()


def test_standing_there_returns_the_memory_and_records_it(client, memory_id, db_session):
    opened = _unlock(client, memory_id)
    assert opened["locked"] is False
    assert opened["summary"] == "the night the amp caught fire"

    rows = db_session.execute(text("SELECT device_id, memory_id FROM unlocks")).fetchall()
    assert len(rows) == 1
    assert str(rows[0].device_id) == DEVICE


def test_a_refused_unlock_records_nothing(client, memory_id, db_session):
    """The write is downstream of the gate, not beside it."""
    refused = _unlock(client, memory_id, lat=FAR_LAT)
    assert refused["locked"] is True
    assert refused["summary"] == ""
    assert refused["distance_meters"] == pytest.approx(1112, abs=50)

    assert db_session.execute(text("SELECT count(*) FROM unlocks")).scalar() == 0


def test_unlocking_twice_does_not_move_the_date(client, memory_id, db_session):
    """The first time is the one that was earned."""
    _unlock(client, memory_id)
    first = db_session.execute(text("SELECT unlocked_at FROM unlocks")).scalar()

    _unlock(client, memory_id)
    rows = db_session.execute(text("SELECT unlocked_at FROM unlocks")).fetchall()
    assert len(rows) == 1
    assert rows[0].unlocked_at == first


def test_the_collection_comes_back_readable_from_anywhere(client, memory_id):
    """No position is sent. Walking away must not take a memory back."""
    _unlock(client, memory_id)

    memories = client.get(f"/v1/unlocks?device={DEVICE}").json()["memories"]
    assert len(memories) == 1
    assert memories[0]["locked"] is False
    assert memories[0]["summary"] == "the night the amp caught fire"


def test_one_device_cannot_read_anothers_collection(client, memory_id):
    _unlock(client, memory_id)
    assert client.get(f"/v1/unlocks?device={OTHER_DEVICE}").json()["memories"] == []


def _memories(session, n):
    """n more memories, each its own place ~100 m apart, so each is gated."""
    ids = []
    for i in range(n):
        place = session.execute(
            text(
                "INSERT INTO places (name, place_query, coordinates, precision_meters) "
                "VALUES (:n, :n, ST_MakePoint(:lng, :lat)::geography, 50) RETURNING id"
            ),
            {"n": f"Spot {i}", "lat": LAT + 0.001 * (i + 1), "lng": LNG},
        ).scalar()
        ids.append(
            session.execute(
                text(
                    "INSERT INTO memories (place_id, summary, extraction_confidence) "
                    "VALUES (:p, :s, 'high') RETURNING id"
                ),
                {"p": place, "s": f"memory {i}"},
            ).scalar()
        )
    session.commit()
    return ids


def _press(client, memory_id):
    return client.post(
        f"/v1/memories/{memory_id}/unlock", json={"device": DEVICE, "lat": LAT, "lng": LNG}
    )


def _finished(client, device=DEVICE):
    walks = client.get(f"/v1/routes/walked?device={device}").json()["walks"]
    return [w for w in walks if w["meta"]["completed_at"]]


def _subscribe(db_session, device=DEVICE):
    db_session.execute(
        text(
            "INSERT INTO subscriptions (user_id, expires_at) "
            "SELECT user_id, CURRENT_TIMESTAMP + INTERVAL '1 day' FROM devices "
            "WHERE id = CAST(:d AS uuid)"
        ),
        {"d": device},
    )
    db_session.commit()


def test_only_a_stop_of_todays_walk_opens(client, memory_id, db_session):
    """docs/10, "A walk planner, nothing else": standing on a memory that is
    not a stop of the walk in progress opens nothing."""
    (off_walk,) = _memories(db_session, 1)
    give_user(db_session, DEVICE)
    refused = client.post(
        f"/v1/memories/{off_walk}/unlock",
        json={"device": DEVICE, "lat": LAT + 0.001, "lng": LNG},
    )
    assert refused.status_code == 403
    assert refused.json()["detail"] == {"reason": "not_on_walk"}
    assert db_session.execute(text("SELECT count(*) FROM unlocks")).scalar() == 0


def test_nothing_opens_from_afar(client, memory_id, db_session):
    assert _unlock(client, memory_id, lat=None, lng=None)["locked"] is True
    assert db_session.execute(text("SELECT count(*) FROM unlocks")).scalar() == 0


def test_a_stop_of_todays_walk_opens_and_finishes_it(client, memory_id):
    assert _finished(client) == []
    assert _press(client, memory_id).status_code == 200
    assert len(_finished(client)) == 1


def test_an_ended_walks_stop_does_not_open(client, memory_id, db_session):
    db_session.execute(text("UPDATE daily_routes SET ended_at = CURRENT_TIMESTAMP"))
    db_session.commit()
    assert _press(client, memory_id).json()["detail"] == {"reason": "not_on_walk"}


def test_a_subscriber_off_the_walk_is_refused_too(client, memory_id, db_session):
    (off_walk,) = _memories(db_session, 1)
    give_user(db_session, DEVICE)
    _subscribe(db_session)
    refused = client.post(
        f"/v1/memories/{off_walk}/unlock",
        json={"device": DEVICE, "lat": LAT + 0.001, "lng": LNG},
    )
    assert refused.status_code == 403


def test_opening_an_earned_memory_again_costs_nothing(client, memory_id):
    _unlock(client, memory_id)
    assert _unlock(client, memory_id, lat=FAR_LAT)["locked"] is False


def test_a_device_id_that_is_not_a_uuid_is_rejected(client, memory_id):
    """It is a cast to uuid downstream; reject at the edge rather than 500."""
    assert (
        client.post(
            f"/v1/memories/{memory_id}/unlock",
            json={"device": "../../etc/passwd", "lat": LAT, "lng": LNG},
        ).status_code
        == 422
    )
    assert client.get("/v1/unlocks?device=not-a-uuid").status_code == 422


def test_unlocking_something_that_does_not_exist_is_a_404(client):
    assert (
        client.post(
            "/v1/memories/999999/unlock", json={"device": DEVICE, "lat": LAT, "lng": LNG}
        ).status_code
        == 404
    )
