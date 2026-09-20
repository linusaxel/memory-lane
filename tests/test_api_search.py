"""What /v1/memories/search actually matches.

Written while trying to make search indexable, which turned out not to be worth
doing (see the ponytail note on SEARCH_VECTOR). The tests outlived the attempt:
nothing asserted this endpoint's behaviour before, and the last one pins the
cross-field matching that any future index work would have to give up.
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

import api.main as m

pytestmark = pytest.mark.db


@pytest.fixture
def client(db_session, monkeypatch):
    from contextlib import contextmanager

    @contextmanager
    def _session():
        yield db_session

    monkeypatch.setattr(m, "get_session", _session)
    # Search reaches the same rows as the map, so it is gated too. These tests
    # are about matching, not about the gate - test_api_unlock.py owns that.
    monkeypatch.setattr(m, "is_gated", lambda row: False)
    return TestClient(m.app)


@pytest.fixture
def corpus(db_session):
    content = db_session.execute(
        text(
            "INSERT INTO content (url, platform, platform_id, source_type) "
            "VALUES ('https://e.invalid/aaaaaaaaaaa', 'text', 'aaaaaaaaaaa', 'archive') "
            "RETURNING id"
        )
    ).scalar()

    def place(name, lat):
        return db_session.execute(
            text(
                "INSERT INTO places (name, place_query, coordinates, precision_meters) "
                "VALUES (:n, :n, ST_MakePoint(12.5655, :lat)::geography, 50) RETURNING id"
            ),
            {"n": name, "lat": lat},
        ).scalar()

    def memory(place_id, summary):
        db_session.execute(
            text(
                "INSERT INTO memories (place_id, content_id, timestamp_start, summary, "
                "extraction_confidence) VALUES (:p, :c, 0, :s, 'high')"
            ),
            {"p": place_id, "c": content, "s": summary},
        )

    memory(place("Vega", 55.6759), "the night the amp caught fire")
    memory(place("Comedy Cellar", 55.6760), "a heckler ruined the night")
    db_session.commit()


def _search(client, q):
    body = client.get(f"/v1/memories/search?q={q}").json()
    return sorted(mem["place"]["name"] for mem in body["memories"])


def test_a_word_in_the_summary_matches(client, corpus):
    assert _search(client, "amp") == ["Vega"]


def test_a_word_in_the_place_name_matches(client, corpus):
    """The place vector is half the point - searching a venue has to find it."""
    assert _search(client, "cellar") == ["Comedy Cellar"]


def test_stemming_still_applies(client, corpus):
    """'english' rather than 'simple', on both vectors."""
    assert _search(client, "hecklers") == ["Comedy Cellar"]


def test_a_miss_is_empty_rather_than_everything(client, corpus):
    body = client.get("/v1/memories/search?q=parliament").json()
    assert body["memories"] == []
    assert body["meta"]["total"] == 0


def test_the_total_counts_matches_not_the_page(client, corpus):
    """Both summaries say "night". One row is asked for; two exist."""
    body = client.get("/v1/memories/search?q=night&limit=1").json()
    assert len(body["memories"]) == 1
    assert body["meta"]["total"] == 2


def test_words_split_across_the_two_fields_still_match(client, corpus):
    """'cellar' is in the place name and 'heckler' in the summary, and the
    vector is built from both concatenated, so this finds the row.

    This is the assertion any future indexing work has to break: a predicate
    that an index can serve has to be per-table, and per-table cannot match a
    query whose words are split across the two."""
    assert _search(client, "cellar heckler") == ["Comedy Cellar"]
