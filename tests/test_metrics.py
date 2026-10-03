"""Retention read from the tables (api.metrics): who came back, what a walk
opened, and how many stories are left around a walker."""

from datetime import date

import pytest
from sqlalchemy import text

from api.metrics import metrics

pytestmark = pytest.mark.db

BACK = "11111111-0000-0000-0000-000000000001"
GONE = "11111111-0000-0000-0000-000000000002"


def _memory(db_session, n):
    place = db_session.execute(
        text(
            "INSERT INTO places (name, place_query, coordinates, precision_meters) "
            "VALUES (:name, :name, ST_MakePoint(12.5655, 55.6759)::geography, 50) RETURNING id"
        ),
        {"name": f"Metrics place {n}"},
    ).scalar()
    return db_session.execute(
        text(
            "INSERT INTO memories (place_id, timestamp_start, summary, extraction_confidence) "
            "VALUES (:p, 0, 'a metrics test memory', 'high') RETURNING id"
        ),
        {"p": place},
    ).scalar()


def test_returns_walks_and_stories_left(db_session):
    for device in (BACK, GONE):
        db_session.execute(
            text(
                "INSERT INTO devices (id, first_seen) VALUES (CAST(:d AS uuid), '2026-09-01 09:00')"
            ),
            {"d": device},
        )
    first, second, other = (_memory(db_session, n) for n in range(3))

    def unlock(memory, at):
        db_session.execute(
            text(
                "INSERT INTO unlocks (device_id, memory_id, unlocked_at) VALUES (CAST(:d AS uuid), :m, :at)"
            ),
            {"d": BACK, "m": memory, "at": at},
        )

    unlock(other, "2026-09-02 12:00")  # back the next day
    db_session.execute(
        text("""
            INSERT INTO daily_routes (device_id, route_date, memory_ids, created_at)
            VALUES (CAST(:d AS uuid), '2026-09-08', CAST(:m AS integer[]), '2026-09-08 10:00')"""),
        {"d": BACK, "m": [first, second]},
    )
    unlock(first, "2026-09-08 11:00")  # and a week later, opening one stop of two

    got = metrics(db_session, date(2026, 9, 20))

    [cohort] = got["cohorts"]
    assert (cohort["devices"], cohort["d1"], cohort["eligible_d1"]) == (2, 1, 2)
    assert (cohort["d7"], cohort["eligible_d7"]) == (1, 2)
    assert got["walks"]["walks"] == 1
    assert got["walks"]["second_walks"] == 0
    assert got["walks"]["opened_per_walk"] == 1
    assert got["stories_left"] == [1]  # the second stop; the other two are opened
