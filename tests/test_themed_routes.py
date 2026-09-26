"""The check before the themed-routes job: stops are places, and only the
ones a walk would take."""

import pytest
from sqlalchemy import text

from pipeline.themed_routes import themes

pytestmark = pytest.mark.db

LAT, LNG = 55.6761, 12.5683


def _place(session, n, lat=None):
    """~n*100m north of LAT, LNG, unless `lat` puts it on another's point."""
    return session.execute(
        text(
            "INSERT INTO places (name, place_query, coordinates) "
            "VALUES (:n, :n, ST_MakePoint(:lng, :lat)::geography) RETURNING id"
        ),
        {"n": f"Stop {n}, Copenhagen", "lat": lat or LAT + n * 0.001, "lng": LNG},
    ).scalar()


def _memory(session, place, tags, hidden=False):
    content = session.execute(
        text(
            "INSERT INTO content (url, platform, platform_id) "
            "VALUES ('https://e.invalid/' || gen_random_uuid(), 'archive', "
            "gen_random_uuid()::text) RETURNING id"
        )
    ).scalar()
    session.execute(
        text(
            "INSERT INTO memories (place_id, content_id, timestamp_start, summary, tags, hidden) "
            "VALUES (:p, :c, 0, 's', CAST(:t AS varchar[]), :h)"
        ),
        {"p": place, "c": content, "t": tags, "h": hidden},
    )


def test_a_stop_is_a_place_a_walk_would_take(db_session):
    for n in range(5):
        _memory(db_session, _place(db_session, n), ["music"])
    _memory(db_session, _place(db_session, 5), ["music"], hidden=True)
    # Five food memories stacked on one place are one stop.
    stack = _place(db_session, 6)
    for _ in range(5):
        _memory(db_session, stack, ["food"])
    # Five art places on one point: no coordinate of their own, so no walk takes them.
    for n in range(7, 12):
        _memory(db_session, _place(db_session, n, lat=LAT + 0.02), ["art"])

    assert themes(db_session) == [("Copenhagen", 15, {"music": 5})]


def test_three_tags_of_five_stops(db_session):
    for n in range(5):
        _memory(db_session, _place(db_session, n), ["music", "food", "art"])
    [(_, _, tags)] = themes(db_session)
    assert tags == {"music": 5, "food": 5, "art": 5}
