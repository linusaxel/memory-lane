"""Managing a memory after it was filed: list your own, edit one, delete one.

Two things are being protected here, the same shape of risk as
test_api_submit.py's on the other end of a submission's life:

**Ownership.** The only credential is still a device id in the request body,
so "is this yours" has to mean "does your account's user_id match the row's",
checked server-side - never trust the client to only ask about its own.

**The cleanup.** A submission mints its own place and can carry its own
media. Deleting one must not leave either behind, and must not touch a place
another memory still uses.
"""

import pytest
from sqlalchemy import text

from tests.test_api_submit import LAT, LNG, device, submit, upload

pytestmark = pytest.mark.db


@pytest.fixture
def client(api_client):
    """conftest's, under the shorter name every test here already uses."""
    return api_client


# -- listing --------------------------------------------------------------


def test_the_list_is_only_your_own(client):
    mine = device()
    theirs = device()
    submit(client, device=mine)
    submit(client, device=theirs)

    listed = client.get(f"/v1/me/memories?device={mine}").json()["memories"]
    assert len(listed) == 1


def test_an_unrelated_device_sees_nothing(client):
    assert client.get(f"/v1/me/memories?device={device()}").json()["memories"] == []


def test_offset_pages_past_the_limit_instead_of_dropping_the_rest(client):
    """The mobile My memories subtab pages through this rather than being
    capped at whatever `limit` the server answers with in one call. Ordering
    across submissions this close together is not itself under test here -
    MY_MEMORIES_QUERY only sorts by created_at, no tiebreaker - so this checks
    the two pages together cover everything exactly once, not their order."""
    dev = device()
    ids = {submit(client, device=dev)["id"] for _ in range(3)}

    page = client.get(f"/v1/me/memories?device={dev}&limit=2").json()
    assert len(page["memories"]) == 2
    assert page["meta"] == {"total": 3, "limit": 2, "offset": 0}

    rest = client.get(f"/v1/me/memories?device={dev}&limit=2&offset=2").json()
    assert len(rest["memories"]) == 1
    assert rest["meta"]["total"] == 3

    seen = {m["id"] for m in page["memories"]} | {m["id"] for m in rest["memories"]}
    assert seen == ids


def test_the_list_keeps_a_hidden_memory_and_says_so(client):
    """Every other endpoint drops a hidden memory silently. This one is the
    author's own management screen, so it has to say what happened instead."""
    dev = device()
    memory = submit(client, device=dev)
    for _ in range(3):
        client.post(f"/v1/memories/{memory['id']}/report", json={"device": device()})

    listed = client.get(f"/v1/me/memories?device={dev}").json()["memories"]
    assert listed[0]["hidden"] is True
    assert listed[0]["summary"] != ""  # still readable to its own author


# -- editing ----------------------------------------------------------------


def test_editing_changes_the_visible_fields(client):
    dev = device()
    memory = submit(client, device=dev)

    edited = client.put(
        f"/v1/memories/{memory['id']}",
        json={
            "device": dev,
            "place_name": "The other bench",
            "summary": "We came back and it was gone. #nature",
            "media_ids": [],
        },
    ).json()

    assert edited["place"]["name"] == "The other bench"
    assert edited["summary"] == "We came back and it was gone. #nature"
    # Re-read from the new words: the old ones' tags go with them.
    assert edited["tags"] == ["nature"]


def test_a_renamed_place_still_matches_search(client):
    """search_vector is trigger-maintained on both the summary and the place
    name (db/migrations/010) - a rename must reach it without any extra code
    in the edit handler."""
    dev = device()
    memory = submit(client, device=dev)
    client.put(
        f"/v1/memories/{memory['id']}",
        json={
            "device": dev,
            "place_name": "Nyhavn kiosk",
            "summary": memory["summary"],
            "media_ids": [],
        },
    )

    found = client.get(f"/v1/memories/search?q=Nyhavn+kiosk&lat={LAT}&lng={LNG}").json()
    assert memory["id"] in [m["id"] for m in found["memories"]]


def test_an_unrelated_device_cannot_edit(client):
    memory = submit(client)
    resp = client.put(
        f"/v1/memories/{memory['id']}",
        json={
            "device": device(),
            "place_name": "Stolen",
            "summary": "Not mine to change.",
            "media_ids": [],
        },
    )
    assert resp.status_code == 404


def test_a_second_device_on_the_same_account_may_edit(client, db_session):
    """Ownership is the account (memories.user_id), not the device - the same
    relationship test_two_submissions_from_one_device_are_one_person exercises
    from the filing side."""
    dev_a = device()
    dev_b = device()
    memory = submit(client, device=dev_a)

    db_session.execute(
        text("INSERT INTO devices (id) VALUES (CAST(:b AS uuid)) ON CONFLICT (id) DO NOTHING"),
        {"b": dev_b},
    )
    db_session.execute(
        text(
            "UPDATE devices SET user_id = (SELECT user_id FROM devices WHERE id = CAST(:a AS uuid)) "
            "WHERE id = CAST(:b AS uuid)"
        ),
        {"a": dev_a, "b": dev_b},
    )
    db_session.commit()

    resp = client.put(
        f"/v1/memories/{memory['id']}",
        json={
            "device": dev_b,
            "place_name": "Edited from the other phone",
            "summary": memory["summary"],
            "media_ids": [],
        },
    )
    assert resp.status_code == 200


def test_editing_can_add_and_remove_photos(client, tmp_path):
    dev = device()
    first = upload(client, dev).json()
    memory = submit(client, device=dev, media_ids=[first["id"]])

    second = upload(client, dev).json()
    edited = client.put(
        f"/v1/memories/{memory['id']}",
        json={
            "device": dev,
            "place_name": memory["place"]["name"],
            "summary": memory["summary"],
            "media_ids": [second["id"]],
        },
    ).json()

    assert [item["id"] for item in edited["media"]] == [second["id"]]
    # The dropped photo's file is actually gone, not just unlinked from the row.
    removed_path = tmp_path / first["url"].removeprefix("/media/")
    assert not removed_path.exists()


def test_editing_cannot_adopt_somebody_elses_upload(client):
    dev = device()
    memory = submit(client, device=dev)
    somebody_elses = upload(client, device()).json()

    resp = client.put(
        f"/v1/memories/{memory['id']}",
        json={
            "device": dev,
            "place_name": memory["place"]["name"],
            "summary": memory["summary"],
            "media_ids": [somebody_elses["id"]],
        },
    )
    assert resp.status_code == 400


# -- deleting -----------------------------------------------------------------


def test_deleting_removes_it_from_the_corpus(client):
    dev = device()
    memory = submit(client, device=dev)

    resp = client.delete(f"/v1/memories/{memory['id']}?device={dev}")
    assert resp.status_code == 204
    assert client.get(f"/v1/memories/{memory['id']}").status_code == 404


def test_deleting_removes_it_from_the_authors_own_collection(client):
    dev = device()
    memory = submit(client, device=dev)
    client.delete(f"/v1/memories/{memory['id']}?device={dev}")

    assert client.get(f"/v1/unlocks?device={dev}").json()["memories"] == []
    assert client.get(f"/v1/me/memories?device={dev}").json()["memories"] == []


def test_deleting_cleans_up_its_own_place_but_not_a_shared_one(client, db_session):
    dev = device()
    memory = submit(client, device=dev)
    place_id = memory["place"]["id"]

    client.delete(f"/v1/memories/{memory['id']}?device={dev}")

    assert (
        db_session.execute(text("SELECT 1 FROM places WHERE id = :id"), {"id": place_id}).scalar()
        is None
    )


def test_deleting_leaves_a_shared_place_alone(client, db_session):
    """Guard against ever deleting a place another row still needs. A
    submission's place is never shared in practice, but the query's own guard
    - NOT EXISTS (memories at this place) - is what makes that safe rather
    than assumed."""
    dev = device()
    memory = submit(client, device=dev)
    place_id = memory["place"]["id"]

    db_session.execute(
        text(
            "INSERT INTO memories (place_id, summary, extraction_confidence) "
            "VALUES (:p, 'a second memory at the same place', 'high')"
        ),
        {"p": place_id},
    )
    db_session.commit()

    client.delete(f"/v1/memories/{memory['id']}?device={dev}")

    assert (
        db_session.execute(text("SELECT 1 FROM places WHERE id = :id"), {"id": place_id}).scalar()
        == 1
    )


def test_deleting_unlinks_its_media_files(client, tmp_path):
    dev = device()
    uploaded = upload(client, dev).json()
    memory = submit(client, device=dev, media_ids=[uploaded["id"]])

    client.delete(f"/v1/memories/{memory['id']}?device={dev}")

    path = tmp_path / uploaded["url"].removeprefix("/media/")
    assert not path.exists()


def test_an_unrelated_device_cannot_delete(client):
    memory = submit(client)
    resp = client.delete(f"/v1/memories/{memory['id']}?device={device()}")
    assert resp.status_code == 404
