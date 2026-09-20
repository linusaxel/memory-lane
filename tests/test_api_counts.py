"""meta.total must equal what the result query would return without paging.

Three endpoints disagreed with their own result sets: /v1/memories/nearby
counted by radius alone and ignored tags and min_confidence, the search count
ignored the location filter, and /v1/places/nearby reported len(page) so every
page looked like the last one. Pagination was wrong whenever a filter was on.

These assert the invariant directly against PostGIS rather than through
TestClient, because the bug was in the SQL, not the plumbing.
"""

import pytest
from sqlalchemy import text

import api.main as m

pytestmark = pytest.mark.db

# layer is bound by every nearby query since W4-06; None means "all layers", so
# these assertions are unchanged by it.
CENTER = {"lat": 40.7484, "lng": -73.9857, "radius_meters": 50000.0, "layer": None}


def _seed(session):
    content_id = session.execute(
        text(
            "INSERT INTO content (url, platform, platform_id) "
            "VALUES ('https://youtu.be/aaaaaaaaaaa','youtube','aaaaaaaaaaa') RETURNING id"
        )
    ).scalar()
    rows = [
        ("Katz's", "katz", 40.7223, -73.9874, ["food"], "high"),
        ("Gotham", "gotham", 40.7440, -73.9950, ["comedy"], "medium"),
        ("Oslo", "oslo", 40.7500, -73.9800, ["food", "comedy"], "low"),
        ("Far away", "far", 41.9000, -73.9000, ["food"], "high"),
    ]
    for name, q, lat, lng, tags, conf in rows:
        pid = session.execute(
            text(
                "INSERT INTO places (name, place_query, precision_meters, coordinates, geocode_status) "
                "VALUES (:n,:q,50, ST_SetSRID(ST_MakePoint(:lng,:lat),4326)::geography,'llm') "
                "RETURNING id"
            ),
            {"n": name, "q": q, "lat": lat, "lng": lng},
        ).scalar()
        session.execute(
            text(
                "INSERT INTO memories (content_id, place_id, summary, timestamp_start, tags, "
                "extraction_confidence) VALUES (:c,:p,:s,1.0,CAST(:t AS varchar[]),:conf)"
            ),
            {"c": content_id, "p": pid, "s": f"a memory at {name}", "t": tags, "conf": conf},
        )
    return content_id


def _rows(session, sql, params):
    """Run a paginated query with paging neutralised."""
    return len(session.execute(text(sql), {**params, "limit": 1000, "offset": 0}).fetchall())


@pytest.mark.parametrize("min_confidence", ["low", "medium", "high"])
def test_nearby_total_matches_rows_at_every_confidence(db_session, min_confidence):
    _seed(db_session)
    params = {**CENTER, "min_confidence": min_confidence}
    rows = _rows(db_session, m.NEARBY_MEMORIES_QUERY, params)
    total = db_session.execute(text(m.COUNT_QUERY), params).scalar()
    assert total == rows


def test_nearby_total_respects_tags(db_session):
    _seed(db_session)
    params = {**CENTER, "min_confidence": "low", "tags": ["comedy"]}
    rows = _rows(db_session, m.NEARBY_MEMORIES_WITH_TAGS_QUERY, params)
    total = db_session.execute(text(m.COUNT_WITH_TAGS_QUERY), params).scalar()
    assert total == rows
    # and the tag filter must actually exclude something, or this proves nothing
    unfiltered = db_session.execute(text(m.COUNT_QUERY), {**CENTER, "min_confidence": "low"})
    assert total < unfiltered.scalar()


def test_search_total_respects_location(db_session):
    _seed(db_session)
    near = {"query": "memory", **CENTER}
    rows = _rows(db_session, m.SEARCH_MEMORIES_WITH_LOCATION_QUERY, near)
    total = db_session.execute(text(m.SEARCH_COUNT_WITH_LOCATION_QUERY), near).scalar()
    assert total == rows

    everywhere = db_session.execute(text(m.SEARCH_COUNT_QUERY), {"query": "memory"}).scalar()
    assert everywhere > total, "the far-away memory should be outside the radius"


def test_places_total_counts_places_not_page_rows(db_session):
    _seed(db_session)
    rows = _rows(db_session, m.NEARBY_PLACES_QUERY, CENTER)
    total = db_session.execute(text(m.PLACES_COUNT_QUERY), CENTER).scalar()
    assert total == rows

    # one page of one must still report the full total
    page = db_session.execute(
        text(m.NEARBY_PLACES_QUERY), {**CENTER, "limit": 1, "offset": 0}
    ).fetchall()
    assert len(page) == 1
    assert total > 1
