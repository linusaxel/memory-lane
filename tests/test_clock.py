"""The server has one opinion of what day it is, and two rules depend on it.

`today()` in api/gate.py decides which day's walk unlocks. `ANNIVERSARY` in
api/queries.py decides whether something happened "on this day". One was
Python's local date and the other was the database's, so on a CEST host
against a UTC container they disagreed for two hours every night -
which is how a test that had passed for weeks failed at 00:04 with nothing
changed but the clock.

Nothing about this is visible in a normal day's testing, which is why it is
worth a file of its own.
"""

import pytest
from sqlalchemy import text

from api.gate import today

pytestmark = pytest.mark.db


def test_the_database_and_the_gate_agree_about_today(db_session):
    """The one that actually bit. Both sides must name the same day, whatever
    timezone the host and the cluster are each set to."""
    from_db = db_session.execute(text("SELECT (now() AT TIME ZONE 'utc')::date")).scalar()
    assert from_db == today(), (
        f"the database thinks it is {from_db} and the gate thinks it is {today()}; "
        "today's walk and an anniversary now disagree about what day it is"
    )


def test_the_anniversary_query_does_not_depend_on_the_cluster_timezone(db_session):
    """CURRENT_DATE follows whatever the cluster is configured to, which is one
    deployment setting away from moving the anniversary by a day. Ask the
    database to pretend it is somewhere else and the answer must not move."""
    db_session.execute(text("SET TIME ZONE 'Pacific/Kiritimati'"))  # UTC+14
    ahead = db_session.execute(text("SELECT (now() AT TIME ZONE 'utc')::date")).scalar()
    db_session.execute(text("RESET TIME ZONE"))

    assert ahead == today(), "the pinned expression moved with the cluster timezone"


def test_the_shipped_query_uses_the_pinned_clock():
    """A regression guard with teeth: the string itself, because the query is
    built once at import and never parameterised."""
    from api.queries import ANNIVERSARY

    assert "AT TIME ZONE 'utc'" in ANNIVERSARY
    assert "CURRENT_DATE" not in ANNIVERSARY
