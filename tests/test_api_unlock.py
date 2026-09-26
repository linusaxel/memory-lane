"""The proximity gate: what leaves the server when you are not standing there.

A client-side gate is not a gate, so the assertions here are about the JSON, not
about the app. If any of these start returning a summary, the mechanic is over -
one curl reads the whole corpus from a sofa and there is no reason to walk
anywhere.

The other half is what is *not* gated. 111 of 186 memories sit on city centroids
the model emitted when it did not know the address, so gating those would mean
demanding somebody stand at a coordinate the memory never happened at. Only a
coordinate no other place shares is treated as real enough to lock.
"""

import pytest
from sqlalchemy import text

import api.gate as gate

pytestmark = pytest.mark.db

# Copenhagen, Rådhuspladsen, and a point ~1.1km north of it.
LAT, LNG = 55.6759, 12.5655
FAR_LAT = LAT + 0.01


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


def _memory(session, place_id, summary, url):
    content = session.execute(
        text(
            "INSERT INTO content (url, platform, platform_id, source_type) "
            "VALUES (:u, 'text', :p, 'archive') RETURNING id"
        ),
        {"u": url, "p": url[-11:]},
    ).scalar()
    return session.execute(
        text(
            "INSERT INTO memories (place_id, content_id, timestamp_start, summary, "
            "extraction_confidence, tags) VALUES (:p, :c, 0, :s, 'high', "
            "ARRAY['music']::varchar[]) RETURNING id"
        ),
        {"p": place_id, "c": content, "s": summary},
    ).scalar()


@pytest.fixture
def one_memory(db_session):
    place = _place(db_session, "Vega", LAT, LNG)
    memory = _memory(
        db_session, place, "the night the amp caught fire", "https://e.invalid/aaaaaaaaaaa"
    )
    db_session.commit()
    return memory


def _nearby(client, **params):
    query = "&".join(f"{k}={v}" for k, v in {"lat": LAT, "lng": LNG, **params}.items())
    return client.get(f"/v1/memories/nearby?{query}").json()["memories"][0]


def test_the_map_never_serves_a_summary(client, one_memory):
    mem = _nearby(client)

    assert mem["locked"] is True
    assert mem["summary"] == ""
    assert mem["content"] is None, "the source video is part of what walking there buys"
    assert mem["media"] == [] and mem["source_url"] is None and mem["attribution"] is None


def test_a_locked_memory_says_what_it_is_not_what_it_says(client, one_memory):
    """The map's peek: its tags and its length, never its words."""
    mem = _nearby(client)

    assert mem["tags"] == ["music"]
    assert mem["summary_words"] == len("the night the amp caught fire".split())


def test_a_locked_memory_still_says_where_to_walk(client, one_memory):
    """A pin you cannot read and cannot find is just a grey dot."""
    mem = _nearby(client)

    assert mem["place"]["name"] == "Vega"
    assert mem["place"]["coordinates"] == {"lat": pytest.approx(LAT), "lng": pytest.approx(LNG)}
    assert mem["distance_meters"] is not None
    assert mem["unlock_radius_meters"] == gate.UNLOCK_RADIUS_METERS


def test_the_map_does_not_unlock_by_being_stood_on(client, one_memory):
    """Walking into range offers the unlock; it must not perform it. Otherwise
    the pin opens itself, there is no moment to press, and the mechanic is a
    proximity query with extra steps."""
    mem = _nearby(client, at_lat=LAT, at_lng=LNG)

    assert mem["locked"] is True
    assert mem["summary"] == ""


def test_a_shared_coordinate_is_never_locked(client, db_session):
    """Two places on one point is the model's way of saying 'somewhere in this
    city'. Locking that would ask somebody to walk to a fiction."""
    first = _place(db_session, "Gotham Comedy Club", LAT, LNG)
    _place(db_session, "Times Square", LAT, LNG)
    _memory(db_session, first, "a heckler got the better of him", "https://e.invalid/bbbbbbbbbbb")
    db_session.commit()

    mem = _nearby(client)

    assert mem["locked"] is False
    assert mem["summary"] == "a heckler got the better of him"


def test_the_single_memory_read_is_the_only_unlock(client, one_memory):
    locked = client.get(f"/v1/memories/{one_memory}").json()
    assert locked["locked"] is True and locked["summary"] == ""

    unlocked = client.get(f"/v1/memories/{one_memory}?at_lat={LAT}&at_lng={LNG}").json()
    assert unlocked["locked"] is False
    assert unlocked["summary"] == "the night the amp caught fire"


def test_a_failed_unlock_says_how_far_off_it_was(client, one_memory):
    """'Too far' with no number is unactionable - the person cannot tell whether
    to take one more step or give up."""
    mem = client.get(f"/v1/memories/{one_memory}?at_lat={FAR_LAT}&at_lng={LNG}").json()

    assert mem["locked"] is True
    assert mem["distance_meters"] == pytest.approx(1112, abs=50)


def test_search_is_not_a_side_door(client, one_memory):
    """Search reaches the same rows with no radius worth the name."""
    mem = client.get("/v1/memories/search?q=amp").json()["memories"][0]

    assert mem["locked"] is True
    assert mem["summary"] == ""


def test_the_place_sample_is_not_a_side_door(client, one_memory):
    """/v1/places/nearby carries a verbatim summary as sample_memory, and there
    is no unlock read for a place - so a gated one never ships it."""
    place = client.get(f"/v1/places/nearby?lat={LAT}&lng={LNG}").json()["places"][0]
    assert place["sample_memory"] is None
    assert place["name"] == "Vega", "the place itself is not a secret"


def test_the_card_is_not_a_side_door(client, one_memory):
    """The widest hole the gate ever had: /card renders a summary as HTML and
    does not go through row_to_memory, so it had to be gated separately - and
    for a while was not. Memory ids are sequential, so one loop read everything.
    """
    locked = client.get(f"/v1/memories/{one_memory}/card").text
    assert "amp caught fire" not in locked
    assert "Stand within" in locked, "a locked card still says what to do about it"
    assert "Vega" in locked, "and still names the place, and still credits it"

    unlocked = client.get(f"/v1/memories/{one_memory}/card?at_lat={LAT}&at_lng={LNG}").text
    assert "amp caught fire" in unlocked


def test_a_centroid_card_is_readable_by_anyone(client, db_session):
    """Same rule as everywhere else: a coordinate several places share is the
    model saying "somewhere in this city", and gating it would ask for a walk to
    a fiction. The embed shows these to strangers on purpose."""
    first = _place(db_session, "Gotham Comedy Club", LAT, LNG)
    _place(db_session, "Times Square", LAT, LNG)
    memory = _memory(
        db_session, first, "a heckler got the better of him", "https://e.invalid/ccccccccccc"
    )
    db_session.commit()

    assert "heckler" in client.get(f"/v1/memories/{memory}/card").text
