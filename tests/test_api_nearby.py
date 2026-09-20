"""What /v1/memories/nearby actually returns.

The single endpoint the app calls, and until now nothing asserted its
behaviour. tests/test_api_sql.py proves every query constant is valid SQL,
which does not mean the radius excludes anything or that the order is right.

Ordering is the part worth guarding. Contrast is the product: the gap between
the memory and what you are standing in front of, not which pin is nearest.
Postgres sorts NULL FIRST under DESC and every memory extracted before contrast
scoring has none, so a missing NULLS LAST inverts the feature completely and
still returns plausible-looking results.
"""

import pytest
from sqlalchemy import text

import api.gate as gate

pytestmark = pytest.mark.db

# Copenhagen, Rådhuspladsen.
LAT, LNG = 55.6759, 12.5655


@pytest.fixture(autouse=True)
def _nothing_is_gated(monkeypatch):
    """These tests assert the radius, the ordering and the fields. The proximity
    gate is asserted in test_api_unlock.py; here nothing is gated, so a redacted
    summary cannot masquerade as a wrong-order bug."""
    monkeypatch.setattr(gate, "is_gated", lambda row: False)


@pytest.fixture
def client(api_client):
    return api_client


def _place(session, name, lat, lng):
    return session.execute(
        text(
            "INSERT INTO places (name, place_query, coordinates, precision_meters) "
            "VALUES (:n, :q, ST_MakePoint(:lng, :lat)::geography, 50) RETURNING id"
        ),
        {"n": name, "q": f"{name} query", "lat": lat, "lng": lng},
    ).scalar()


def _content(session, url):
    return session.execute(
        text(
            "INSERT INTO content (url, platform, platform_id, source_type) "
            "VALUES (:u, 'text', :p, 'archive') RETURNING id"
        ),
        {"u": url, "p": url[-11:]},
    ).scalar()


def _memory(session, place_id, content_id, summary, **kw):
    cols = {
        "place_id": place_id,
        "content_id": content_id,
        "timestamp_start": 0.0,
        "summary": summary,
        "extraction_confidence": "high",
        **kw,
    }
    names = ", ".join(cols)
    binds = ", ".join(f":{k}" for k in cols)
    return session.execute(
        text(f"INSERT INTO memories ({names}) VALUES ({binds}) RETURNING id"), cols
    ).scalar()


def test_a_place_outside_the_radius_is_not_returned(client, db_session):
    near = _place(db_session, "Near", LAT, LNG)
    far = _place(db_session, "Far", LAT + 0.5, LNG)  # ~55km north
    content = _content(db_session, "https://example.invalid/aaaaaaaaaaa")
    _memory(db_session, near, content, "close by")
    _memory(db_session, far, content, "far away")
    db_session.commit()

    body = client.get(f"/v1/memories/nearby?lat={LAT}&lng={LNG}&radius_km=5").json()
    assert [mem["summary"] for mem in body["memories"]] == ["close by"]
    assert body["meta"]["total"] == 1


def test_the_highest_contrast_memory_comes_first_even_if_further(client, db_session):
    """The whole point. A bank lobby that was a jazz club beats a nearer pin."""
    near = _place(db_session, "Near dull", LAT, LNG)
    far = _place(db_session, "Far vivid", LAT + 0.01, LNG)  # ~1.1km
    content = _content(db_session, "https://example.invalid/bbbbbbbbbbb")
    _memory(db_session, near, content, "still a cathedral", contrast_score=0.1)
    _memory(db_session, far, content, "now a bank lobby", contrast_score=0.95)
    db_session.commit()

    body = client.get(f"/v1/memories/nearby?lat={LAT}&lng={LNG}&radius_km=5").json()
    assert [mem["summary"] for mem in body["memories"]] == [
        "now a bank lobby",
        "still a cathedral",
    ]


def test_unscored_memories_sort_below_scored_ones(client, db_session):
    """Without NULLS LAST, Postgres puts every unscored memory on top - and the
    live corpus is 224 unscored memories."""
    a = _place(db_session, "Scored", LAT, LNG)
    b = _place(db_session, "Unscored", LAT + 0.001, LNG)
    content = _content(db_session, "https://example.invalid/ccccccccccc")
    _memory(db_session, a, content, "scored low", contrast_score=0.2)
    _memory(db_session, b, content, "never scored")
    db_session.commit()

    body = client.get(f"/v1/memories/nearby?lat={LAT}&lng={LNG}&radius_km=5").json()
    assert [mem["summary"] for mem in body["memories"]] == ["scored low", "never scored"]


def test_a_layer_filter_returns_only_that_layer(client, db_session):
    place = _place(db_session, "Vega", LAT, LNG)
    content = _content(db_session, "https://example.invalid/ddddddddddd")
    _memory(db_session, place, content, "public and permanent", layer="historical")
    _memory(db_session, place, content, "intimate and ephemeral", layer="friend")
    db_session.commit()

    only = client.get(f"/v1/memories/nearby?lat={LAT}&lng={LNG}&layer=friend").json()
    assert [mem["summary"] for mem in only["memories"]] == ["intimate and ephemeral"]
    assert only["meta"]["total"] == 1, "total must respect the layer filter too"

    everything = client.get(f"/v1/memories/nearby?lat={LAT}&lng={LNG}").json()
    assert everything["meta"]["total"] == 2, "omitting layer means every layer"


def test_an_unknown_layer_is_rejected_not_silently_ignored(client):
    """A typo must not quietly return friend memories to everyone."""
    assert client.get(f"/v1/memories/nearby?lat={LAT}&lng={LNG}&layer=public").status_code == 422


def test_the_card_fields_are_served(client, db_session):
    """attribution and source_url exist so a shared card can carry its credit."""
    place = _place(db_session, "Vega", LAT, LNG)
    content = _content(db_session, "https://example.invalid/eeeeeeeeeee")
    _memory(
        db_session,
        place,
        content,
        "a band played here",
        happened_at="1978-06-17",
        attribution="SYNTHETIC FIXTURE",
        source_url="https://example.invalid/synthetic/1",
        contrast_score=0.9,
        contrast_note="a music room; a bank branch since 1994",
    )
    db_session.commit()

    mem = client.get(f"/v1/memories/nearby?lat={LAT}&lng={LNG}").json()["memories"][0]
    assert mem["happened_at"] == "1978-06-17"
    assert mem["attribution"] == "SYNTHETIC FIXTURE"
    assert mem["source_url"] == "https://example.invalid/synthetic/1"
    assert mem["contrast_score"] == pytest.approx(0.9)
    assert "bank branch" in mem["contrast_note"]
    assert mem["layer"] == "historical"


def test_every_memory_carries_the_unlock_radius(client, db_session):
    """The app draws the reach circle from this, and it used to be set only on
    locked memories - so a viewport with nothing locked in it silently fell back
    to the app's own hardcoded 150, under a comment promising the opposite."""
    place = _place(db_session, "Vega", LAT, LNG)
    content = _content(db_session, "https://e.invalid/rrrrrrrrrrr")
    _memory(db_session, place, content, "the night the amp caught fire")
    db_session.commit()

    memories = client.get(f"/v1/memories/nearby?lat={LAT}&lng={LNG}&radius_km=5").json()["memories"]
    assert memories
    assert all(m["unlock_radius_meters"] == gate.UNLOCK_RADIUS_METERS for m in memories)


def test_stats_says_the_radius_too(client):
    """The only source when there is nothing on the map at all, which is exactly
    when the circle is still drawn around the person."""
    assert client.get("/v1/stats").json()["unlock_radius_meters"] == gate.UNLOCK_RADIUS_METERS
