"""A memory that cannot be read until a date, not even by the person who wrote it.

Phase 5.2. The proximity gate asks *are you here*; this asks *is it time*, and
the two are independent. Everything worth asserting is about that independence,
because every existing way of opening a memory is a way this could leak:

- standing on the spot, which is the whole of the other gate;
- the collection, which forces a memory open by passing it its own coordinates;
- the unlock endpoint, which records having walked there;
- the card, which renders HTML and gates itself with a second copy of the query.

Four doors, one check. It lives at the top of `is_locked`, before position is
considered at all, so a fifth door inherits it for free.
"""

from datetime import timedelta

import pytest
from sqlalchemy import text

from api.gate import today
from tests.conftest import on_todays_route

pytestmark = pytest.mark.db

# Rådhuspladsen.
LAT, LNG = 55.6759, 12.5655

SOON = today() + timedelta(days=1)
PASSED = today() - timedelta(days=1)


@pytest.fixture
def client(api_client):
    return api_client


def submission(**overrides) -> dict:
    body = {
        "device": "11111111-1111-4111-8111-111111111111",
        "lat": LAT,
        "lng": LNG,
        "place_name": "The bench by the harbour",
        "summary": "For whoever is standing here in ten years: it was worth it.",
        "tags": ["strange"],
    }
    body.update(overrides)
    return body


def file_one(client, **overrides):
    response = client.post("/v1/memories", json=submission(**overrides))
    assert response.status_code == 201, response.text
    return response.json()


def test_a_sealed_memory_does_not_open_to_the_person_who_filed_it(client):
    """The strongest form of the rule, and the one that is easy to get wrong:
    the submit path deliberately opens a memory for its author, because filing
    something is standing there. A time lock has to survive that."""
    memory = file_one(client, opens_at=SOON.isoformat())

    assert memory["locked"] is True
    assert memory["summary"] == ""
    assert memory["opens_at"] == SOON.isoformat()


def test_standing_on_the_spot_does_not_open_it(client, db_session):
    memory = file_one(client, opens_at=SOON.isoformat())
    on_todays_route(db_session, submission()["device"], memory["id"])
    read = client.get(f"/v1/memories/{memory['id']}?at_lat={LAT}&at_lng={LNG}").json()
    assert read["locked"] is True

    unlocked = client.post(
        f"/v1/memories/{memory['id']}/unlock",
        json={"device": submission()["device"], "lat": LAT, "lng": LNG},
    ).json()
    assert unlocked["locked"] is True, "walking there must not open a time capsule"


def test_it_stays_shut_in_the_collection_too(client):
    """/v1/unlocks forces every memory open by handing it its own coordinates.
    That is the one place the position gate is deliberately bypassed, so it is
    the one place a time lock has to be checked ahead of it."""
    device = submission()["device"]
    memory = file_one(client, opens_at=SOON.isoformat())

    collection = client.get(f"/v1/unlocks?device={device}").json()["memories"]
    mine = [m for m in collection if m["id"] == memory["id"]]
    assert mine, "it is still theirs - it is only shut"
    assert mine[0]["locked"] is True
    assert mine[0]["summary"] == ""


def test_the_card_will_not_hand_it_over_either(client):
    """api/card.py keeps its own copy of the query. A column it forgot would
    read as "no lock" and render a sealed memory to anyone holding the link."""
    memory = file_one(client, opens_at=SOON.isoformat())
    html = client.get(f"/v1/memories/{memory['id']}/card?at_lat={LAT}&at_lng={LNG}").text

    assert "worth it" not in html
    assert "sealed" in html
    # And it says when, rather than telling somebody to walk across a city for
    # a memory that will not open to anybody today.
    assert SOON.strftime("%-d %B %Y") in html
    assert "Stand within" not in html


def test_a_date_that_has_passed_is_not_a_lock(client):
    """No special case for it: an expired seal is the same thing as no seal."""
    memory = file_one(client, opens_at=PASSED.isoformat())
    assert memory["locked"] is False
    assert memory["summary"].startswith("For whoever")
    assert memory["opens_at"] is None, "a date that no longer means anything is not sent"


def test_without_a_date_nothing_changes(client):
    memory = file_one(client)
    assert memory["locked"] is False
    assert memory["opens_at"] is None


def test_the_map_shows_it_without_showing_it(client, db_session):
    """It is still a pin. Somebody has to be able to see that there is
    something here and come back."""
    memory = file_one(client, opens_at=SOON.isoformat())
    nearby = client.get(f"/v1/memories/nearby?lat={LAT}&lng={LNG}&radius_km=1").json()

    only = [m for m in nearby["memories"] if m["id"] == memory["id"]]
    assert len(only) == 1
    assert only[0]["locked"] is True
    assert only[0]["summary"] == ""
    assert only[0]["opens_at"] == SOON.isoformat()


def test_search_cannot_reach_inside_it(client):
    file_one(client, opens_at=SOON.isoformat())
    found = client.get("/v1/memories/search?q=worth").json()["memories"]
    assert all(m["summary"] == "" for m in found)


def test_the_column_exists_in_both_places(db_session):
    """Fresh databases get it from db/schema.sql and existing ones from the
    migration. Drift between the two is invisible until a deploy behaves
    differently from a laptop."""
    import pathlib

    root = pathlib.Path(__file__).resolve().parents[1]
    migration = (root / "db" / "migrations" / "009_time_locked.sql").read_text()
    assert "opens_at DATE" in migration

    live = db_session.execute(
        text(
            "SELECT data_type FROM information_schema.columns "
            "WHERE table_name = 'memories' AND column_name = 'opens_at'"
        )
    ).scalar()
    assert live == "date"
