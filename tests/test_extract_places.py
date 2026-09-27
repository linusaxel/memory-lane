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

from pipeline.extract import merge_nearby_memories, save_memories

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


def _structured(summary, venue="Katz's Delicatessen", locality="New York", **kw):
    mem = _memory(summary, **kw)
    mem.pop("place_name", None)
    mem.pop("place_query", None)
    mem["venue"] = venue
    mem["locality"] = locality
    return mem


def test_same_venue_different_incidental_text_is_one_row(db_session):
    """The under-merge case pipeline/dedup.py's string heuristic used to exist
    for: the same real venue, described with different free text, now collides
    at insert time instead of needing a human-reviewed batch job afterwards."""
    content_id = _content(db_session)
    save_memories(db_session, content_id, [_structured("first visit")])
    save_memories(
        db_session,
        content_id,
        [_structured("second visit", venue="katz's delicatessen", locality="new york")],
    )

    places, memories = _counts(db_session)
    assert (places, memories) == (1, 2)


def test_two_venues_sharing_a_locality_stay_separate(db_session):
    """The documented failure pipeline/dedup.py's heuristic cannot fix: two
    real venues on the same street. Andaz/Comedy Store, Sunset Boulevard -
    docs/10-decisions.md#place-dedup-matches-on-names-not-coordinates."""
    content_id = _content(db_session)
    save_memories(
        db_session,
        content_id,
        [
            _structured("hotel", venue="Andaz West Hollywood", locality="West Hollywood"),
            _structured("comedy set", venue="Comedy Store", locality="West Hollywood"),
        ],
    )
    places, memories = _counts(db_session)
    assert (places, memories) == (2, 2)


def test_merge_nearby_keys_on_venue_and_locality():
    a = {
        "venue": "Vega",
        "locality": "Copenhagen",
        "timestamp_start": 10.0,
        "summary": "s1",
        "tags": ["music"],
    }
    b = {
        "venue": "vega",
        "locality": "copenhagen",
        "timestamp_start": 40.0,
        "summary": "s2",
        "tags": ["history"],
    }
    merged = merge_nearby_memories([a, b])
    assert len(merged) == 1
    assert set(merged[0]["tags"]) == {"music", "history"}
    assert merged[0]["summary"] == "s1", "two stories glued together are over the word limit"


def test_merge_nearby_does_not_merge_different_venues_same_locality():
    a = {
        "venue": "Andaz West Hollywood",
        "locality": "West Hollywood",
        "timestamp_start": 10.0,
        "summary": "s1",
    }
    b = {
        "venue": "Comedy Store",
        "locality": "West Hollywood",
        "timestamp_start": 15.0,
        "summary": "s2",
    }
    assert len(merge_nearby_memories([a, b])) == 2


def test_merge_keeps_two_stories_at_one_bar_apart():
    """Verbatim from the Copenhagen video: the crawl's opening and Tit Ind are
    both pinned to Maskot seconds apart, and are two memories. The Ringkaféen
    pair is one story told by two overlapping chunks, and is one."""
    at = {"venue": "Maskot", "locality": "Copenhagen", "timestamp_start": 10.0}
    opening = "The 30th anniversary of Trip Nørrebro was declared underway outside Maskot with cake, shots, and a round of hugs and toasts."
    tit_ind = "Maskot's owners, Helle and Kim, took it over after their previous bar, Tit Ind near Nørrebro station, was torn down to make way for metro construction."
    assert len(merge_nearby_memories([dict(at, summary=opening), dict(at, summary=tit_ind)])) == 2

    at = dict(at, venue="Ringkaféen")
    one = "Ringkaféen, a bar from the 1930s at Folmer Bendtsens Plads, sank into the ground when metro construction broke through to the old Lygteå stream running beneath the asphalt."
    two = "Ringkafeen, a bar dating from the 1930s on Folmer Bensens Plads, sank into the ground when metro construction broke through to the old Lygteå stream running under the asphalt."
    assert len(merge_nearby_memories([dict(at, summary=one), dict(at, summary=two)])) == 1


def test_a_story_told_again_minutes_later_is_one_memory():
    """Verbatim from Café Woodstock: the raid told at 3:07 and again at 4:14."""
    at = {"venue": "Woodstock", "locality": "Copenhagen"}
    one = "During the 'værtshuskrigen,' when the state tried stripping Christiania's bars of alcohol licenses and equipment, Woodstock was completely gutted, with truckloads of bar stools, bottles and beer crates hauled away. But the bar counter itself stayed standing, since a customer had mortared it in with a technique so solid even police with the right tools couldn't remove it."
    two = "During værtshuskrigen, when the state tried to strip Christiania's bars of alcohol licenses and equipment, police arrived at Woodstock in trucks and hauled away the tables, benches, beer and tap equipment. The bar counter itself, built with an unusual masonry technique, could not be removed and still stands today, with only its tabletop lost."
    memories = [
        dict(at, summary=one, timestamp_start=187.0),
        dict(at, summary=two, timestamp_start=254.6),
    ]
    assert [m["summary"] for m in merge_nearby_memories(memories)] == [one]
