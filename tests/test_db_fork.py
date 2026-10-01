"""A forked child gets its own connections. rq forks a work-horse per job, and
on the parent's pooled connection the second child to prepare a statement
failed with DuplicatePreparedStatement (2026-10-01)."""

import os

import pytest
from sqlalchemy import text

from pipeline import db


@pytest.mark.db
def test_each_forked_child_prepares_on_its_own_connection(db_engine, monkeypatch):
    monkeypatch.setattr(db, "engine", db_engine)  # the fork hook disposes db.engine
    with db_engine.connect() as conn:
        conn.execute(text("SELECT 1"))

    for _ in range(2):
        pid = os.fork()
        if pid == 0:
            try:
                with db_engine.begin() as conn:  # a commit keeps it prepared; a rollback drops it
                    for i in range(7):  # psycopg prepares a query on its fifth run
                        conn.execute(text("SELECT :i"), {"i": i})
                os._exit(0)
            except Exception:
                os._exit(1)
        assert os.waitpid(pid, 0)[1] == 0
