"""The daily submission limit, against somebody who does not wait their turn.

The check was a read in one transaction and the insert a write in another.
Anybody can win that race by not waiting: fire twenty requests at once, all
twenty read the same count, all twenty are allowed. A limit that only holds
for people submitting politely one at a time is not a limit, because the only
person it exists to stop is the one doing it on purpose.

These drive the SQL the endpoint uses rather than the endpoint itself, because
the API's session is monkeypatched to a single shared one in tests and two
connections are the entire point.
"""

import threading
import time

import pytest
from sqlalchemy import create_engine, text

from api.write import FILED_TODAY, LOCK_USER

pytestmark = pytest.mark.db

LIMIT = 3
RUSH = 8


def _setup(db_session):
    # users.id has no default - the app mints it, so the test does too.
    user_id = db_session.execute(
        text(
            "INSERT INTO users (id, display_name) VALUES (gen_random_uuid(), 'Racer') RETURNING id"
        )
    ).scalar()
    place_id = db_session.execute(
        text(
            "INSERT INTO places (name, place_query, coordinates, precision_meters) "
            "VALUES ('Here', 'race:here', ST_MakePoint(12.5, 55.6)::geography, 25) "
            "RETURNING id"
        )
    ).scalar()
    db_session.commit()
    return user_id, place_id


def _rush(db_url, user_id, place_id, *, lock: bool, dawdle: float = 0.0):
    """Every thread does what the endpoint does: count, decide, insert."""
    engine = create_engine(db_url, pool_size=RUSH + 2, max_overflow=0)
    barrier = threading.Barrier(RUSH)

    def submit():
        barrier.wait()  # everybody arrives at once, which is the whole point
        with engine.begin() as conn:
            if lock:
                conn.execute(text(LOCK_USER), {"user_id": user_id})
            filed = conn.execute(text(FILED_TODAY), {"user_id": user_id}).scalar()
            if filed >= LIMIT:
                return
            time.sleep(dawdle)
            conn.execute(
                text(
                    "INSERT INTO memories (place_id, summary, user_id, layer) "
                    "VALUES (:p, 'filed in a hurry', :u, 'stranger')"
                ),
                {"p": place_id, "u": user_id},
            )

    threads = [threading.Thread(target=submit) for _ in range(RUSH)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    with engine.begin() as conn:
        total = conn.execute(
            text("SELECT COUNT(*) FROM memories WHERE user_id = :u"), {"u": user_id}
        ).scalar()
    engine.dispose()
    return total


def test_the_limit_holds_against_a_rush(db_session, db_url):
    user_id, place_id = _setup(db_session)
    total = _rush(db_url, user_id, place_id, lock=True)
    assert total == LIMIT, f"{RUSH} simultaneous submissions filed {total}, limit is {LIMIT}"


def test_without_the_lock_it_does_not(db_session, db_url):
    """The control. Without it the test above could be passing because the
    threads never actually overlapped, and would go on passing if somebody
    removed the lock."""
    user_id, place_id = _setup(db_session)
    total = _rush(db_url, user_id, place_id, lock=False, dawdle=0.05)
    assert total > LIMIT, (
        "the unlocked version stayed within the limit, so this pair proves "
        "nothing about the locked one - the threads are not overlapping"
    )
