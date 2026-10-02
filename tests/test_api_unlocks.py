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

from api.gate import today
from tests.conftest import give_keys, spend_welcome

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
    spend_welcome(db_session, DEVICE)
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


def _balance(client, device=DEVICE):
    me = client.get(f"/v1/me?device={device}").json()
    return me["welcome_unlocks"], me["keys"]


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


def _on_todays_walk(db_session, memory_id, device=DEVICE):
    db_session.execute(
        text(
            "INSERT INTO daily_routes (device_id, route_date, memory_ids) "
            "VALUES (CAST(:d AS uuid), :today, ARRAY[CAST(:m AS integer)])"
        ),
        {"d": device, "today": today(), "m": memory_id},
    )
    db_session.commit()


def test_one_to_start_opens_from_anywhere(client, memory_id, db_session):
    """docs/10, "Pick one to start, then where you stand"."""
    first, second = [memory_id, *_memories(db_session, 1)]
    opened = _unlock(client, first, lat=None, lng=None)
    assert opened["locked"] is False
    assert opened["summary"]
    assert _balance(client) == (0, 0)

    far = _unlock(client, second, lat=FAR_LAT)
    assert far["locked"] is True, "the welcome one is spent, and not standing there"
    assert db_session.execute(text("SELECT count(*) FROM unlocks")).scalar() == 1


def test_after_the_welcome_one_a_key_standing_there(client, memory_id, db_session):
    """docs/10, "Keys open a lock, and today's walk is free"."""
    spend_welcome(db_session, DEVICE)
    refused = _press(client, memory_id)
    assert refused.status_code == 403
    assert refused.json()["detail"] == {"reason": "no_keys", "keys": 0}
    assert db_session.execute(text("SELECT count(*) FROM unlocks")).scalar() == 0

    give_keys(db_session, DEVICE, 2)
    assert _press(client, memory_id).status_code == 200
    assert _balance(client) == (0, 1)


def test_a_key_never_opens_one_from_afar(client, memory_id, db_session):
    spend_welcome(db_session, DEVICE)
    give_keys(db_session, DEVICE, 3)
    assert _unlock(client, memory_id, lat=FAR_LAT)["locked"] is True
    assert _balance(client) == (0, 3)


def test_standing_there_spends_a_key_before_the_welcome_one(client, memory_id, db_session):
    give_keys(db_session, DEVICE, 5)
    _press(client, memory_id)
    assert _balance(client) == (1, 4)


def test_standing_there_with_no_keys_uses_the_welcome_one(client, memory_id, db_session):
    assert _press(client, memory_id).status_code == 200
    assert _balance(client) == (0, 0)


def test_a_stop_of_todays_walk_opens_for_nothing(client, memory_id, db_session):
    give_keys(db_session, DEVICE, 1)
    _on_todays_walk(db_session, memory_id)
    assert _press(client, memory_id).status_code == 200
    assert _balance(client) == (1, 2), "nothing spent, and a key for finishing the walk"


def test_an_ended_walks_stop_costs_a_key_again(client, memory_id, db_session):
    give_keys(db_session, DEVICE, 1)
    _on_todays_walk(db_session, memory_id)
    db_session.execute(text("UPDATE daily_routes SET ended_at = CURRENT_TIMESTAMP"))
    db_session.commit()
    _press(client, memory_id)
    assert _balance(client) == (1, 0)


def test_opening_an_earned_memory_again_costs_nothing(client, memory_id):
    _unlock(client, memory_id)
    _unlock(client, memory_id, lat=FAR_LAT)
    assert _balance(client) == (0, 0)


def test_a_subscriber_standing_there_spends_nothing(client, memory_id, db_session):
    give_keys(db_session, DEVICE, 0)
    _subscribe(db_session)
    assert _press(client, memory_id).status_code == 200
    assert _balance(client) == (1, 0)


def test_steps_are_counted_once_from_the_watermark_and_buy_nothing(client, db_session):
    give_keys(db_session, DEVICE, 0)
    db_session.execute(
        text(
            "UPDATE users SET steps_counted_until = CURRENT_TIMESTAMP - INTERVAL '1 hour' "
            "WHERE id = (SELECT user_id FROM devices WHERE id = CAST(:d AS uuid))"
        ),
        {"d": DEVICE},
    )
    db_session.commit()
    since = client.get(f"/v1/me?device={DEVICE}").json()["steps_counted_until"]

    def credit(steps):
        return client.post(
            "/v1/me/steps", json={"device": DEVICE, "since": since, "steps": steps}
        ).json()

    after = credit(2400)
    assert after["steps"] == 2400
    assert after["keys"] == 0
    assert after["steps_counted_until"] > since
    assert credit(2400)["steps"] == 2400, "a retry from the old watermark counts nothing"


def test_steps_faster_than_anyone_walks_are_capped(client, db_session):
    give_keys(db_session, DEVICE, 0)
    db_session.execute(
        text(
            "UPDATE users SET steps_counted_until = CURRENT_TIMESTAMP - INTERVAL '10 seconds' "
            "WHERE id = (SELECT user_id FROM devices WHERE id = CAST(:d AS uuid))"
        ),
        {"d": DEVICE},
    )
    db_session.commit()
    since = client.get(f"/v1/me?device={DEVICE}").json()["steps_counted_until"]
    after = client.post(
        "/v1/me/steps", json={"device": DEVICE, "since": since, "steps": 100_000}
    ).json()
    assert 30 <= after["steps"] < 40


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


def test_the_dev_long_press_gives_a_key(client, db_session):
    give_keys(db_session, DEVICE, 1)
    assert client.post(f"/v1/dev/keys?device={DEVICE}").json()["keys"] == 2
