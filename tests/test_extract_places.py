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


def test_a_pin_outside_the_launch_area_is_not_saved(db_session, monkeypatch):
    from pipeline import extract

    monkeypatch.setattr(extract, "LAUNCH_BBOX", (55.60, 12.45, 55.74, 12.66))
    content_id = _content(db_session)
    save_memories(
        db_session,
        content_id,
        [
            _memory("Stockholm", place_query="Gamla stan, Stockholm", lat=59.325, lng=18.071),
            _memory("Nørrebro", place_query="Assistens Kirkegård", lat=55.691, lng=12.550),
            _memory("unpinned", place_query="somewhere", lat=None, lng=None),
        ],
    )
    saved = db_session.execute(text("SELECT summary FROM memories ORDER BY id")).scalars().all()
    assert saved == ["Nørrebro", "unpinned"]


def _saved(session):
    return session.execute(text("SELECT summary FROM memories ORDER BY id")).scalars().all()


def test_a_retelling_nearby_is_not_saved_and_another_story_is(db_session):
    from tests.fakes import FakeAnthropic

    content_id = _content(db_session)
    save_memories(db_session, content_id, [_memory("the pastrami argument")])
    same = FakeAnthropic({"reason": "the same argument", "same_as": 0})
    other = FakeAnthropic({"reason": "a different night", "same_as": -1})

    save_memories(db_session, content_id, [_memory("they argued over pastrami")], client=same)
    save_memories(db_session, content_id, [_memory("the night the lights went")], client=other)

    assert _saved(db_session) == ["the pastrami argument", "the night the lights went"]
    assert len(same.messages.calls) == len(other.messages.calls) == 1


def test_an_unreadable_or_failed_check_saves_the_memory(db_session):
    from tests.fakes import FakeAnthropic

    class _Down:
        class messages:
            @staticmethod
            def create(**kwargs):
                raise RuntimeError("overloaded")

    content_id = _content(db_session)
    save_memories(db_session, content_id, [_memory("first")])
    save_memories(db_session, content_id, [_memory("second")], client=FakeAnthropic(["no"]))
    save_memories(db_session, content_id, [_memory("third")], client=_Down())
    assert _saved(db_session) == ["first", "second", "third"]


def test_the_first_telling_in_one_batch_is_kept(db_session):
    from tests.fakes import FakeAnthropic

    fake = FakeAnthropic({"reason": "told twice", "same_as": 0})
    content_id = _content(db_session)
    save_memories(db_session, content_id, [_memory("first"), _memory("again")], client=fake)
    assert _saved(db_session) == ["first"]
    assert len(fake.messages.calls) == 1, "the first memory has no neighbour to ask about"


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


def test_the_bar_sits_between_a_retelling_and_a_second_story():
    """Verbatim, the closest pair of each on the corpus (2026-09-28): Hedebygade
    told twice overlaps 0.20, Flyvergrillen's two stories 0.14."""
    at = {"venue": "Hedebygade", "locality": "Copenhagen"}
    one = "Tove Ditlevsen grew up on Hedebygade, a hard working-class street on Vesterbro at the time. This is the street she immortalized as 'barndommens gade' (the street of childhood) in her book Barndom, writing unsparingly about what it meant to be a child here."
    two = "Tove Ditlevsen grew up on this street, Hedebygade, in a rough working-class quarter near Istedgade where prostitution and poverty shaped daily life. She wrote about it with unusual bluntness in her novel Barndom, later reissued as the first part of what became internationally known as The Copenhagen Trilogy, praised by The New York Times as a landmark of Scandinavian literature."
    assert len(merge_nearby_memories([dict(at, summary=one), dict(at, summary=two)])) == 1

    at = {"venue": "Flyvergrillen", "locality": "Kastrup"}
    bush = "When George Bush landed in Denmark in the mid-2000s, crowds packed Flyvergrillen to watch Air Force One touch down at the airport next door. The grill bar, open since the early 1970s, has long drawn plane enthusiasts who come just to watch takeoffs and landings."
    kiosk = "People used to gather here just to watch planes, and a boy would run around selling ice cream he'd bought from a shop further down the road. Someone decided to open an ice cream kiosk on the spot instead, and by the 1970s it had grown into the grill bar known as Flyvergrillen."
    assert len(merge_nearby_memories([dict(at, summary=bush), dict(at, summary=kiosk)])) == 2


def test_a_better_telling_is_saved_and_hides_the_first(db_session):
    from tests.fakes import FakeAnthropic

    better = FakeAnthropic({"reason": "a scene", "same_as": 0, "new_is_better": True})
    content_id = _content(db_session)
    save_memories(db_session, content_id, [_memory("the palace burned")])
    save_memories(db_session, content_id, [_memory("he watched the roof fall")], client=better)
    visible = db_session.execute(
        text("SELECT summary FROM memories WHERE NOT hidden ORDER BY id")
    ).scalars()
    assert list(visible) == ["he watched the roof fall"]


def test_a_retelling_is_caught_where_it_lands_not_where_the_model_pinned_it(db_session):
    """2026-09-30: the model pinned Kasino's King story 1 km from the Kasino
    already saved. The check looked there, found nothing, and the venue snapped
    the retelling onto the first telling's pin."""
    from tests.fakes import FakeAnthropic

    same = FakeAnthropic({"reason": "the same King", "same_as": 0, "new_is_better": False})
    content_id = _content(db_session)
    save_memories(db_session, content_id, [_structured("the King at the door")])
    far = _structured("I am the King, he whispered", lat=40.7313, lng=-73.9874)
    save_memories(db_session, content_id, [far], client=same)
    assert _saved(db_session) == ["the King at the door"]
    assert len(same.messages.calls) == 1


def test_two_names_on_one_wikidata_point_are_one_place(db_session, monkeypatch):
    """2026-10-03: "Blue Tower" and "Blåtårn" were two places with eight
    Leonora stories between them, because places matched by name only."""
    from pipeline import extract

    monkeypatch.setattr(extract.geocode, "place", lambda *a: (55.6753, 12.5783, 50, "wikidata"))
    content_id = _content(db_session)
    save_memories(
        db_session,
        content_id,
        [
            _memory("the tower", venue="Blue Tower", locality="Copenhagen"),
            _memory("the cell", venue="Blåtårn", locality="Copenhagen"),
        ],
    )
    assert _counts(db_session) == (1, 2)


def test_a_venue_that_is_the_city_is_not_saved(db_session):
    content_id = _content(db_session)
    save_memories(
        db_session,
        content_id,
        [
            _memory("an execution", venue="Copenhagen", locality="Copenhagen"),
            _memory("the tower", venue="Blåtårn", locality="Copenhagen"),
        ],
    )
    assert _saved(db_session) == ["the tower"]
