"""Saving the same place twice must reuse the row, not mint a new one.

places had no unique constraint, so `ON CONFLICT DO NOTHING` in save_memories
could never fire: every memory created a fresh place. The live database reached
224 places for 224 memories, and one venue existed six times - six stacked pins
on the map for one comedy club.

These run against the real ephemeral PostGIS DB because the behaviour under test
IS the constraint; a mock would prove nothing about it.
"""

import pytest
from sqlalchemy import text

from pipeline.extract import save_memories

pytestmark = pytest.mark.db


def _memory(summary, place_query="Katz's Delicatessen, New York", **kw):
    mem = {
        "place_name": "Katz's Delicatessen",
        "place_query": place_query,
        "lat": 40.7223,
        "lng": -73.9874,
        "summary": summary,
        "tags": ["food"],
        "confidence": "high",
        "location_precision": "exact",
        "timestamp_start": 10.0,
    }
    mem.update(kw)
    return mem


def _content(session, url="https://www.youtube.com/watch?v=aaaaaaaaaaa"):
    return session.execute(
        text(
            "INSERT INTO content (url, platform, platform_id) "
            "VALUES (:u, 'youtube', 'aaaaaaaaaaa') RETURNING id"
        ),
        {"u": url},
    ).scalar()


def _counts(session):
    return (
        session.execute(text("SELECT count(*) FROM places")).scalar(),
        session.execute(text("SELECT count(*) FROM memories")).scalar(),
    )


def test_the_same_place_twice_is_one_row(db_session):
    content_id = _content(db_session)
    save_memories(db_session, content_id, [_memory("first visit")])
    save_memories(db_session, content_id, [_memory("second visit")])

    places, memories = _counts(db_session)
    assert (places, memories) == (1, 2), "the ON CONFLICT fallback did not reuse the place"


def test_both_memories_point_at_the_same_place(db_session):
    content_id = _content(db_session)
    save_memories(db_session, content_id, [_memory("first"), _memory("second")])

    place_ids = db_session.execute(text("SELECT DISTINCT place_id FROM memories")).fetchall()
    assert len(place_ids) == 1
    assert place_ids[0][0] is not None, "place_id came back NULL - the memory was dropped"


def test_different_places_stay_separate(db_session):
    content_id = _content(db_session)
    save_memories(
        db_session,
        content_id,
        [
            _memory("deli", place_query="Katz's, New York"),
            _memory("bar", place_query="Oslo Norway"),
        ],
    )
    places, memories = _counts(db_session)
    assert (places, memories) == (2, 2)


def test_a_place_without_coordinates_also_dedups(db_session):
    """The no-coords INSERT branch has its own ON CONFLICT and its own bug surface."""
    content_id = _content(db_session)
    save_memories(db_session, content_id, [_memory("a", lat=None, lng=None)])
    save_memories(db_session, content_id, [_memory("b", lat=None, lng=None)])

    places, memories = _counts(db_session)
    assert (places, memories) == (1, 2)
