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

from datetime import timedelta

import pytest
from sqlalchemy import text

import api.gate as gate
from api.gate import today

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


def test_a_person_who_was_here_outranks_the_archive(client, db_session):
    """The core rule: friend, then stranger, then historical, and layer wins
    over contrast. One point holding a note somebody left and a well-scored
    podcast anecdote is one feed, and the note must not be page three of it."""
    place = _place(db_session, "Vega", LAT, LNG)
    content = _content(db_session, "https://example.invalid/eeeeeeeeeee")
    _memory(db_session, place, content, "a jazz club, now a bank", contrast_score=0.95)
    _memory(db_session, place, content, "we queued here in the rain", layer="stranger")
    _memory(db_session, place, content, "her flat was upstairs", layer="friend")
    db_session.commit()

    body = client.get(f"/v1/memories/nearby?lat={LAT}&lng={LNG}").json()
    assert [mem["layer"] for mem in body["memories"]] == ["friend", "stranger", "historical"]


def test_within_a_layer_contrast_still_decides(client, db_session):
    """Layer precedence is a tiebreak between kinds, not a replacement for the
    ranking. Drop the contrast term and this still passes on order alone, so it
    is asserted the other way round: the better-scored historical memory beats
    the nearer one, exactly as it did before layers were in the ORDER BY."""
    near = _place(db_session, "Near", LAT, LNG)
    far = _place(db_session, "Far", LAT + 0.01, LNG)
    content = _content(db_session, "https://example.invalid/fffffffffff")
    _memory(db_session, near, content, "dull but close", contrast_score=0.1)
    _memory(db_session, far, content, "extraordinary but far", contrast_score=0.9)
    _memory(db_session, near, content, "somebody stood here", layer="stranger")
    db_session.commit()

    body = client.get(f"/v1/memories/nearby?lat={LAT}&lng={LNG}&radius_km=5").json()
    assert [mem["summary"] for mem in body["memories"]] == [
        "somebody stood here",
        "extraordinary but far",
        "dull but close",
    ]


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


def test_something_that_happened_today_comes_back_up(client, db_session):
    """Phase 5.1. There are no notifications in this product, so the only way a
    date can surface anything is by sorting it to the top of the list somebody
    is already looking at - which means it has to beat contrast."""
    place = _place(db_session, "Vega", LAT, LNG)
    content = _content(db_session, "https://example.invalid/ggggggggggg")
    _memory(db_session, place, content, "a much better story", contrast_score=0.95)
    _memory(
        db_session,
        place,
        content,
        "thirty years ago today",
        contrast_score=0.1,
        happened_at=today().replace(year=today().year - 30),
        happened_precision="day",
    )
    db_session.commit()

    body = client.get(f"/v1/memories/nearby?lat={LAT}&lng={LNG}").json()
    assert [mem["summary"] for mem in body["memories"]] == [
        "thirty years ago today",
        "a much better story",
    ]
    assert body["memories"][0]["anniversary"] is True
    assert body["memories"][1]["anniversary"] is False


def test_the_same_date_in_another_year_is_not_an_anniversary(client, db_session):
    """Day-and-month, not the whole date: a memory of today is today's news."""
    place = _place(db_session, "Vega", LAT, LNG)
    content = _content(db_session, "https://example.invalid/hhhhhhhhhhh")
    _memory(
        db_session,
        place,
        content,
        "yesterday",
        happened_at=today() - timedelta(days=1),
    )
    db_session.commit()

    body = client.get(f"/v1/memories/nearby?lat={LAT}&lng={LNG}").json()
    assert body["memories"][0]["anniversary"] is False


def test_a_year_only_date_is_not_an_anniversary(client, db_session):
    """A year is stored as 1 January; it must not resurface every New Year."""
    place = _place(db_session, "Vega", LAT, LNG)
    content = _content(db_session, "https://example.invalid/iiiiiiiiiii")
    _memory(
        db_session,
        place,
        content,
        "sometime that year",
        happened_at=today().replace(year=today().year - 30),
        happened_precision="year",
    )
    db_session.commit()

    body = client.get(f"/v1/memories/nearby?lat={LAT}&lng={LNG}").json()
    assert body["memories"][0]["anniversary"] is False


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


def test_the_app_falls_back_to_the_radius_the_server_actually_uses():
    """mobile/src/reach.ts carries its own copy of the unlock radius, for the
    case where a memory arrives without the server's. A copy that drifts is
    an app drawing a reach circle the server will not honour - the same class
    of bug the palette and the tag vocabulary are already pinned against."""
    import pathlib
    import re

    reach_ts = (
        pathlib.Path(__file__).resolve().parents[1] / "mobile" / "src" / "reach.ts"
    ).read_text()
    match = re.search(r"FALLBACK_RADIUS_M\s*=\s*(\d+)", reach_ts)
    assert match, "mobile/src/reach.ts no longer declares FALLBACK_RADIUS_M"

    assert int(match.group(1)) == gate.UNLOCK_RADIUS_METERS, (
        f"the app falls back to {match.group(1)}m and the server gates at "
        f"{gate.UNLOCK_RADIUS_METERS}m"
    )
