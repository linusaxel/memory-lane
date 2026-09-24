"""Notes: only from someone who unlocked the memory, one each, taken down by
the author. See docs/10-decisions.md#notes-are-gated-like-a-purchase."""

import pytest
from sqlalchemy import text

pytestmark = pytest.mark.db

AUTHOR = "aaaaaaaa-2222-3333-4444-555555555555"
VISITOR = "11111111-2222-3333-4444-555555555555"
STRANGER = "99999999-8888-7777-6666-555555555555"


@pytest.fixture
def client(api_client):
    return api_client


@pytest.fixture
def memory_id(db_session):
    user = db_session.execute(
        text("INSERT INTO users (id, display_name) VALUES (gen_random_uuid(), 'Ada') RETURNING id")
    ).scalar()
    db_session.execute(
        text("INSERT INTO devices (id, user_id) VALUES (CAST(:d AS uuid), :u)"),
        {"d": AUTHOR, "u": user},
    )
    db_session.execute(text("INSERT INTO devices (id) VALUES (CAST(:d AS uuid))"), {"d": VISITOR})
    place = db_session.execute(
        text(
            "INSERT INTO places (name, place_query, coordinates, precision_meters) "
            "VALUES ('Vega', 'user:x', ST_MakePoint(12.5655, 55.6759)::geography, 10) "
            "RETURNING id"
        )
    ).scalar()
    memory = db_session.execute(
        text(
            "INSERT INTO memories (place_id, user_id, summary, extraction_confidence, layer) "
            "VALUES (:p, :u, 'the night the amp caught fire', 'high', 'stranger') RETURNING id"
        ),
        {"p": place, "u": user},
    ).scalar()
    for device in (AUTHOR, VISITOR):
        db_session.execute(
            text("INSERT INTO unlocks (device_id, memory_id) VALUES (CAST(:d AS uuid), :m)"),
            {"d": device, "m": memory},
        )
    db_session.commit()
    return memory


def _note(client, memory_id, body="I was there too", device=VISITOR):
    return client.post(f"/v1/memories/{memory_id}/note", json={"device": device, "body": body})


def _notes(client, memory_id, device=VISITOR):
    return client.get(f"/v1/memories/{memory_id}/notes?device={device}")


def test_a_note_needs_an_unlock(client, memory_id):
    assert _note(client, memory_id, device=STRANGER).status_code == 403
    assert _notes(client, memory_id, device=STRANGER).status_code == 403


def test_a_second_note_rewrites_the_first(client, memory_id):
    assert _note(client, memory_id).status_code == 200
    _note(client, memory_id, body="  second thoughts  ")
    notes = _notes(client, memory_id).json()["notes"]
    assert [(n["body"], n["author"], n["mine"]) for n in notes] == [
        ("second thoughts", "Anonymous", True)
    ]


def test_the_author_reads_notes_and_the_count_travels_locked(client, memory_id):
    _note(client, memory_id)
    notes = _notes(client, memory_id, device=AUTHOR).json()["notes"]
    assert notes[0]["mine"] is False
    assert client.get(f"/v1/memories/{memory_id}").json()["note_count"] == 1


def test_the_author_takes_a_note_down_and_a_stranger_cannot(client, memory_id):
    _note(client, memory_id)
    note_id = _notes(client, memory_id).json()["notes"][0]["id"]
    url = f"/v1/memories/{memory_id}/notes/{note_id}"
    assert client.delete(f"{url}?device={STRANGER}").status_code == 404
    assert client.delete(f"{url}?device={AUTHOR}").status_code == 204
    assert _notes(client, memory_id).json()["notes"] == []
    assert client.get(f"/v1/memories/{memory_id}").json()["note_count"] == 0


def test_a_blank_or_long_note_is_refused(client, memory_id):
    assert _note(client, memory_id, body="   ").status_code == 422
    assert _note(client, memory_id, body="x" * 281).status_code == 422
