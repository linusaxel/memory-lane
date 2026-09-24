"""How many days in a row this account unlocked a stop of that day's walk.

Computed from `unlocks.unlocked_at` joined to `daily_routes` on every read (api.accounts.current_streak),
not stored - there is nothing to keep in sync when a second device unlocks
something, and no counter that can drift from the rows it is supposed to
summarize.
"""

from datetime import date, timedelta

import pytest
from sqlalchemy import text

from api.accounts import current_streak

pytestmark = pytest.mark.db

TODAY = date(2026, 9, 23)
DEVICE = "11111111-2222-3333-4444-555555555555"


def test_no_days_is_no_streak():
    assert current_streak([], TODAY) == 0


def test_unlocking_only_today_is_a_streak_of_one():
    assert current_streak([TODAY], TODAY) == 1


def test_three_days_in_a_row_ending_today():
    days = [TODAY, TODAY - timedelta(days=1), TODAY - timedelta(days=2)]
    assert current_streak(days, TODAY) == 3


def test_yesterday_with_nothing_today_still_counts_so_far():
    """The day is not over - not having unlocked yet today does not break it."""
    days = [TODAY - timedelta(days=1), TODAY - timedelta(days=2)]
    assert current_streak(days, TODAY) == 2


def test_a_day_skipped_two_days_ago_breaks_the_streak():
    days = [TODAY - timedelta(days=2), TODAY - timedelta(days=3)]
    assert current_streak(days, TODAY) == 0


def test_a_gap_in_the_middle_stops_counting_there():
    days = [TODAY, TODAY - timedelta(days=1), TODAY - timedelta(days=3)]
    assert current_streak(days, TODAY) == 2


@pytest.fixture
def client(api_client):
    return api_client


def _place_and_memory(db_session, n):
    place = db_session.execute(
        text(
            "INSERT INTO places (name, place_query, coordinates, precision_meters) "
            "VALUES (:name, :name, ST_MakePoint(12.5655, 55.6759)::geography, 50) RETURNING id"
        ),
        {"name": f"Streak place {n}"},
    ).scalar()
    content = db_session.execute(
        text(
            "INSERT INTO content (url, platform, platform_id, source_type) "
            "VALUES (:url, 'text', :url, 'archive') RETURNING id"
        ),
        {"url": f"https://e.invalid/streak{n}"},
    ).scalar()
    return db_session.execute(
        text(
            "INSERT INTO memories (place_id, content_id, timestamp_start, summary, "
            "extraction_confidence) VALUES (:p, :c, 0, 'a streak test memory', 'high') "
            "RETURNING id"
        ),
        {"p": place, "c": content},
    ).scalar()


def test_the_profile_reports_the_streak_computed_from_unlocks(client, db_session):
    db_session.execute(
        text("INSERT INTO devices (id) VALUES (CAST(:device AS uuid))"), {"device": DEVICE}
    )
    for n, days_ago in enumerate([0, 1, 2]):
        memory_id = _place_and_memory(db_session, n)
        db_session.execute(
            text(
                "INSERT INTO unlocks (device_id, memory_id, unlocked_at) "
                "VALUES (CAST(:device AS uuid), :memory_id, CURRENT_TIMESTAMP - :days * INTERVAL '1 day')"
            ),
            {"device": DEVICE, "memory_id": memory_id, "days": days_ago},
        )
        _walk_that_day(db_session, memory_id, days_ago)
    db_session.commit()

    assert client.get(f"/v1/me?device={DEVICE}").json()["streak"] == 3


def _walk_that_day(db_session, memory_id, days_ago):
    db_session.execute(
        text(
            "INSERT INTO daily_routes (device_id, route_date, memory_ids) VALUES "
            "(CAST(:device AS uuid), (CURRENT_TIMESTAMP - :days * INTERVAL '1 day')::date, "
            "ARRAY[:memory_id])"
        ),
        {"device": DEVICE, "memory_id": memory_id, "days": days_ago},
    )


def test_a_day_with_only_a_filing_does_not_count(client, db_session):
    """Filing records its own unlock. If that counted, a streak would be kept
    by posting anything; the streak is for walking."""
    db_session.execute(
        text("INSERT INTO devices (id) VALUES (CAST(:device AS uuid))"), {"device": DEVICE}
    )
    walked, filed = _place_and_memory(db_session, 0), _place_and_memory(db_session, 1)
    for memory_id in (walked, filed):
        db_session.execute(
            text(
                "INSERT INTO unlocks (device_id, memory_id) "
                "VALUES (CAST(:device AS uuid), :memory_id)"
            ),
            {"device": DEVICE, "memory_id": memory_id},
        )
    db_session.commit()
    assert client.get(f"/v1/me?device={DEVICE}").json()["streak"] == 0

    _walk_that_day(db_session, walked, 0)
    db_session.commit()
    assert client.get(f"/v1/me?device={DEVICE}").json()["streak"] == 1


def test_a_device_that_has_never_unlocked_anything_has_no_streak(client):
    assert client.get(f"/v1/me?device={DEVICE}").json()["streak"] == 0
